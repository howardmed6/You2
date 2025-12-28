import os
import json
import sys
import io
from concurrent.futures import ThreadPoolExecutor
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Configuración
FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
IMAGENES = [f"imagen{i}.jpg" for i in range(1, 11)]

def get_services():
    creds_dict = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=creds), vision.ImageAnnotatorClient(credentials=creds)

def procesar_una_imagen(nombre, drive_service, vision_client):
    try:
        # 1. Buscar ID del archivo
        query = f"'{FOLDER_ID}' in parents and name='{nombre}' and trashed=false"
        res = drive_service.files().list(q=query, fields="files(id)").execute()
        if not res.get('files'): return {"archivo": nombre, "estado": "no encontrado"}

        # 2. Descargar a memoria
        file_id = res['files'][0]['id']
        request = drive_service.files().get_media(fileId=file_id)
        img_io = io.BytesIO()
        downloader = MediaIoBaseDownload(img_io, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        # 3. Analizar con Vision API
        content = img_io.getvalue()
        image = vision.Image(content=content)
        # Pedimos objetos y logos en UNA SOLA llamada para ahorrar
        response = vision_client.annotate_image({
            'image': image,
            'features': [{'type_': vision.Feature.Type.OBJECT_LOCALIZATION}, 
                         {'type_': vision.Feature.Type.LOGO_DETECTION}]
        })

        # 4. Estructurar el JSON como pediste (con ceros si no hay nada)
        marcos = []
        for obj in response.localized_object_annotations:
            if any(x in obj.name.lower() for x in ['frame', 'border', 'rectangle']):
                marcos.append({
                    "lado": obj.name,
                    "coords": [{"x": v.x, "y": v.y} for v in obj.bounding_poly.normalized_vertices]
                })
        
        if not marcos:
            marcos = [{"lado": "ninguno", "coords": [{"x": 0, "y": 0}]}]

        return {
            "archivo": nombre,
            "marcos": marcos,
            "logos": [logo.description for logo in response.logo_annotations]
        }
    except Exception as e:
        return {"archivo": nombre, "error": str(e)}

def ejecutar():
    drive, vision_api = get_services()
    
    # USAMOS SOLO 2 WORKERS PARA NO CORROMPER LA MEMORIA MALLOC
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(lambda n: procesar_una_imagen(n, drive, vision_api), IMAGENES))

    # Guardar reporte local
    with open('reporte_marcos_logos.json', 'w') as f:
        json.dump(resultados, f, indent=2)

    # Subir a Drive
    media = MediaFileUpload('reporte_marcos_logos.json', mimetype='application/json')
    drive.files().create(body={'name': 'reporte_marcos_logos.json', 'parents': [FOLDER_ID]}, media_body=media).execute()
    print("✅ Proceso completado exitosamente.")

if __name__ == "__main__":
    ejecutar()