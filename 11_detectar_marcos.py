import os
import json
import sys
import io
import time
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
IMAGENES = [f"imagen{i}.jpg" for i in range(1, 11)]

def get_creds():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    # Agregamos los SCOPES necesarios para ambas APIs aquí mismo
    scopes = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/cloud-platform'
    ]
    return Credentials.from_service_account_info(creds_json).with_scopes(scopes)

def procesar_lote_secuencial():
    creds = get_creds()
    # Construimos los servicios con las credenciales que ya tienen los scopes
    drive_service = build('drive', 'v3', credentials=creds)
    # Importante: Pasar las credenciales directamente al cliente de Vision
    vision_client = vision.ImageAnnotatorClient(credentials=creds)
    
    reporte_final = []

    print(f"--- Iniciando proceso de {len(IMAGENES)} imágenes ---")

    for nombre in IMAGENES:
        try:
            print(f"📥 Descargando: {nombre}")
            q = f"'{FOLDER_ID}' in parents and name='{nombre}' and trashed=false"
            res = drive_service.files().list(q=q, fields="files(id)").execute()
            
            if not res.get('files'):
                print(f"⚠️ {nombre} no encontrado.")
                continue

            file_id = res['files'][0]['id']
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            print(f"🔍 Analizando IA: {nombre}")
            content = fh.getvalue()
            image = vision.Image(content=content)
            
            response = vision_client.annotate_image({
                'image': image,
                'features': [
                    {'type_': vision.Feature.Type.OBJECT_LOCALIZATION},
                    {'type_': vision.Feature.Type.LOGO_DETECTION}
                ]
            })

            registro = {
                "archivo": nombre,
                "marcos": [],
                "logos": [logo.description for logo in response.logo_annotations]
            }

            for obj in response.localized_object_annotations:
                if any(x in obj.name.lower() for x in ['frame', 'border', 'rectangle']):
                    registro["marcos"].append({
                        "nombre": obj.name,
                        "coordenadas": [{"x": round(v.x, 3), "y": round(v.y, 3)} for v in obj.bounding_poly.normalized_vertices]
                    })

            if not registro["marcos"]:
                registro["marcos"] = [{"nombre": "ninguno", "coordenadas": [{"x": 0, "y": 0}]}]

            reporte_final.append(registro)
            fh.close()

        except Exception as e:
            print(f"❌ Error en {nombre}: {str(e)}")
            reporte_final.append({"archivo": nombre, "error": str(e)})

    # SOLUCIÓN AL ERROR DE CUOTA (403):
    # En lugar de crear un archivo nuevo que consume cuota de la cuenta de servicio,
    # lo creamos dentro de la carpeta compartida para que use tu cuota.
    print("📤 Subiendo reporte final...")
    with open('reporte_marcos_logos.json', 'w') as f:
        json.dump(reporte_final, f, indent=2)

    file_metadata = {
        'name': 'reporte_marcos_logos.json',
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload('reporte_marcos_logos.json', mimetype='application/json')
    
    # Intentamos primero ver si ya existe para actualizarlo, si no, lo creamos
    existing = drive_service.files().list(q=f"name='reporte_marcos_logos.json' and '{FOLDER_ID}' in parents").execute()
    if existing.get('files'):
        drive_service.files().update(fileId=existing['files'][0]['id'], media_body=media).execute()
    else:
        # La clave es que al estar en una carpeta compartida, hereda el permiso
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    
    print("✅ TODO LISTO.")

if __name__ == "__main__":
    procesar_lote_secuencial()