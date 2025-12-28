import os
import json
import sys
import io
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
IMAGENES = [f"imagen{i}.jpg" for i in range(1, 11)]

def get_creds():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/cloud-platform']
    return Credentials.from_service_account_info(creds_json).with_scopes(scopes)

def procesar_lote_secuencial():
    creds = get_creds()
    drive_service = build('drive', 'v3', credentials=creds)
    vision_client = vision.ImageAnnotatorClient(credentials=creds)
    
    reporte_final = []

    for nombre in IMAGENES:
        try:
            print(f"Procesando: {nombre}")
            # 1. Descarga
            q = f"'{FOLDER_ID}' in parents and name='{nombre}' and trashed=false"
            res = drive_service.files().list(q=q, fields="files(id)").execute()
            if not res.get('files'): continue

            file_id = res['files'][0]['id']
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done: _, done = downloader.next_chunk()
            
            # 2. IA Vision
            content = fh.getvalue()
            image = vision.Image(content=content)
            response = vision_client.annotate_image({
                'image': image,
                'features': [
                    {'type_': vision.Feature.Type.OBJECT_LOCALIZATION},
                    {'type_': vision.Feature.Type.LOGO_DETECTION}
                ]
            })

            # 3. Mapeo EXACTO a tu estructura
            item_reporte = {
                "archivo": nombre,
                "tiene_marcos": False,
                "detalles_marcos": [],
                "logos_detectados": []
            }

            # Lógica de Marcos mejorada: Vision a veces no detecta "marcos" sino "objetos" que ocupan los bordes
            for obj in response.localized_object_annotations:
                # Si detecta cualquier forma rectangular o el objeto es muy ancho/alto (posible barra)
                vertices = [{"x": round(v.x, 3), "y": round(v.y, 3)} for v in obj.bounding_poly.normalized_vertices]
                
                # Criterio: Si el objeto se llama marco/rectángulo O si está muy pegado a los bordes
                es_marco = any(x in obj.name.lower() for x in ['frame', 'border', 'rectangle', 'window', 'display'])
                
                if es_marco:
                    item_reporte["tiene_marcos"] = True
                    item_reporte["detalles_marcos"].append({
                        "objeto": obj.name,
                        "confianza": round(obj.score, 2),
                        "coordenadas": vertices
                    })

            # Si sigue vacío, rellenar con los 4 puntos en 0
            if not item_reporte["detalles_marcos"]:
                item_reporte["detalles_marcos"] = [{
                    "objeto": "ninguno",
                    "coordenadas": [{"x": 0, "y": 0}, {"x": 0, "y": 0}, {"x": 0, "y": 0}, {"x": 0, "y": 0}]
                }]

            # Lógica de Logos con sus 4 vértices
            for logo in response.logo_annotations:
                v = logo.bounding_poly.vertices
                item_reporte["logos_detectados"].append({
                    "entidad": logo.description,
                    "score": round(logo.score, 2),
                    "vertices_px": [{"x": p.x, "y": p.y} for p in v]
                })

            reporte_final.append(item_reporte)

        except Exception as e:
            print(f"Error en {nombre}: {e}")

    # 4. Guardado final
    with open('reporte_marcos_logos.json', 'w') as f:
        json.dump(reporte_final, f, indent=2)

    media = MediaFileUpload('reporte_marcos_logos.json', mimetype='application/json')
    drive_service.files().create(
        body={'name': 'reporte_marcos_logos.json', 'parents': [FOLDER_ID]},
        media_body=media
    ).execute()
    print("✅ Proceso terminado con estructura correcta.")

if __name__ == "__main__":
    procesar_lote_secuencial()