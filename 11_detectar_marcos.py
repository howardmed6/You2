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
IMAGENES = [f"imagen{i}.jpg" for i in range(1, 11)]

def get_creds():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    return Credentials.from_service_account_info(creds_json, scopes=['https://www.googleapis.com/auth/drive'])

def procesar_lote_secuencial():
    creds = get_creds()
    drive_service = build('drive', 'v3', credentials=creds)
    reporte_final = []

    print(f"--- Iniciando proceso de {len(IMAGENES)} imágenes ---")

    for nombre in IMAGENES:
        try:
            print(f"📥 Descargando: {nombre}")
            # 1. Buscar archivo
            q = f"'{FOLDER_ID}' in parents and name='{nombre}' and trashed=false"
            res = drive_service.files().list(q=q, fields="files(id)").execute()
            
            if not res.get('files'):
                print(f"⚠️ {nombre} no encontrado.")
                continue

            file_id = res['files'][0]['id']
            
            # 2. Descargar a buffer
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            # 3. Analizar (Creamos y destruimos el cliente en el loop para limpiar RAM)
            print(f"🔍 Analizando IA: {nombre}")
            vision_client = vision.ImageAnnotatorClient(credentials=creds)
            content = fh.getvalue()
            image = vision.Image(content=content)
            
            response = vision_client.annotate_image({
                'image': image,
                'features': [
                    {'type_': vision.Feature.Type.OBJECT_LOCALIZATION},
                    {'type_': vision.Feature.Type.LOGO_DETECTION}
                ]
            })

            # Estructura del registro
            registro = {
                "archivo": nombre,
                "marcos": [],
                "logos": [logo.description for logo in response.logo_annotations]
            }

            for obj in response.localized_object_annotations:
                if any(x in obj.name.lower() for x in ['frame', 'border', 'rectangle']):
                    registro["marcos"].append({
                        "nombre": obj.name,
                        "coordenadas": [{"x": v.x, "y": v.y} for v in obj.bounding_poly.normalized_vertices]
                    })

            if not registro["marcos"]:
                registro["marcos"] = [{"nombre": "ninguno", "coordenadas": [{"x": 0, "y": 0}]}]

            reporte_final.append(registro)
            
            # Limpieza manual de memoria para evitar malloc corruption
            del vision_client
            fh.close()
            time.sleep(1) # Pequeño respiro para el recolector de basura

        except Exception as e:
            print(f"❌ Error en {nombre}: {str(e)}")
            reporte_final.append({"archivo": nombre, "error": str(e)})

    # 4. Guardar y Subir Reporte
    print("📤 Subiendo reporte final...")
    with open('reporte_marcos_logos.json', 'w') as f:
        json.dump(reporte_final, f, indent=2)

    media = MediaFileUpload('reporte_marcos_logos.json', mimetype='application/json')
    drive_service.files().create(
        body={'name': 'reporte_marcos_logos.json', 'parents': [FOLDER_ID]},
        media_body=media
    ).execute()
    
    print("✅ TODO LISTO.")

if __name__ == "__main__":
    procesar_lote_secuencial()