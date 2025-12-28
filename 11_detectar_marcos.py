import os
import json
import sys
import io
import time
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Configuración
FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
ARCHIVO_JSON = "reporte_marcos_logos.json"
IMAGENES = [f"imagen{i}.jpg" for i in range(1, 11)]

def get_creds():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    # Permisos completos para asegurar que pueda ver y editar el archivo
    scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/cloud-vision']
    return Credentials.from_service_account_info(creds_json).with_scopes(scopes)

def procesar_y_actualizar():
    try:
        print("🚀 Iniciando script...")
        creds = get_creds()
        drive_service = build('drive', 'v3', credentials=creds)
        vision_client = vision.ImageAnnotatorClient(credentials=creds)
        
        reporte_final = []

        # 1. Procesamiento de Imágenes
        for nombre in IMAGENES:
            try:
                # Buscar imagen
                q = f"'{FOLDER_ID}' in parents and name='{nombre}' and trashed=false"
                res = drive_service.files().list(q=q, fields="files(id)").execute()
                
                if not res.get('files'):
                    print(f"⚠️ {nombre} no encontrada.")
                    continue

                file_id = res['files'][0]['id']
                
                # Descargar
                request = drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done: _, done = downloader.next_chunk()
                
                print(f"👁️ Analizando: {nombre}")
                content = fh.getvalue()
                image = vision.Image(content=content)
                
                # Llamada a Vision API
                response = vision_client.annotate_image({
                    'image': image,
                    'features': [
                        {'type_': vision.Feature.Type.OBJECT_LOCALIZATION},
                        {'type_': vision.Feature.Type.LOGO_DETECTION}
                    ]
                })

                # Estructura JSON solicitada
                item = {
                    "archivo": nombre,
                    "tiene_marcos": False,
                    "detalles_marcos": [],
                    "logos_detectados": []
                }

                # Filtro de Marcos
                for obj in response.localized_object_annotations:
                    es_marco = any(t in obj.name.lower() for t in ['frame', 'border', 'rectangle', 'display', 'screen'])
                    if es_marco:
                        item["tiene_marcos"] = True
                        item["detalles_marcos"].append({
                            "objeto": obj.name,
                            "confianza": round(obj.score, 2),
                            "coordenadas": [{"x": round(v.x, 3), "y": round(v.y, 3)} for v in obj.bounding_poly.normalized_vertices]
                        })

                # Relleno con ceros si está vacío
                if not item["detalles_marcos"]:
                    item["detalles_marcos"] = [{
                        "objeto": "ninguno",
                        "coordenadas": [{"x": 0, "y": 0}, {"x": 0, "y": 0}, {"x": 0, "y": 0}, {"x": 0, "y": 0}]
                    }]

                # Logos
                for logo in response.logo_annotations:
                    item["logos_detectados"].append({
                        "entidad": logo.description,
                        "vertices_px": [{"x": v.x, "y": v.y} for v in logo.bounding_poly.vertices]
                    })

                reporte_final.append(item)
                
                # Limpiar memoria
                fh.close()
                del image
                
            except Exception as e:
                print(f"❌ Error en {nombre}: {e}")

        # 2. Guardado y Actualización (SOLO ACTUALIZAR)
        print("💾 Guardando JSON local...")
        with open(ARCHIVO_JSON, 'w') as f:
            json.dump(reporte_final, f, indent=2)

        print("☁️ Buscando archivo en Drive para actualizar...")
        # Buscar el archivo JSON existente
        res_json = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and name='{ARCHIVO_JSON}' and trashed=false",
            fields="files(id)"
        ).execute()

        if not res_json.get('files'):
            print(f"❌ ERROR CRÍTICO: No encontré el archivo '{ARCHIVO_JSON}' en la carpeta.")
            print("Por favor verifica que el archivo exista y tenga ese nombre exacto.")
            # Imprimimos el JSON en consola por seguridad
            print(json.dumps(reporte_final, indent=2))
            sys.exit(1)
        else:
            file_id_json = res_json['files'][0]['id']
            print(f"✅ Archivo encontrado ({file_id_json}). Subiendo cambios...")
            
            media = MediaFileUpload(ARCHIVO_JSON, mimetype='application/json')
            drive_service.files().update(
                fileId=file_id_json, 
                media_body=media
            ).execute()
            print("✅ Actualización completada con éxito.")

    except Exception as e:
        print(f"💀 Fallo fatal: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    procesar_y_actualizar()