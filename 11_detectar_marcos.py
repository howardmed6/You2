import os
import json
import sys
import io
import requests
from concurrent.futures import ThreadPoolExecutor
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Configuración basada en tu captura de pantalla
FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
# Nombres exactos de los archivos en tu carpeta TEM
IMAGENES_A_PROCESAR = [f"imagen{i}.jpg" for i in range(1, 11)]

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                         json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
        except: pass

def get_services():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json, scopes=['https://www.googleapis.com/auth/drive'])
    drive_service = build('drive', 'v3', credentials=creds)
    vision_client = vision.ImageAnnotatorClient(credentials=creds)
    return drive_service, vision_client

def download_image(service, filename):
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=false", 
        fields="files(id)"
    ).execute()
    
    if not results.get('files'):
        return None
    
    file_id = results['files'][0]['id']
    request = service.files().get_media(fileId=file_id)
    
    img_data = io.BytesIO()
    downloader = MediaIoBaseDownload(img_data, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return img_data.getvalue()

def analizar_marcos_y_logos(vision_client, content, filename):
    image = vision.Image(content=content)
    
    # Pedimos Localización de Objetos (Marcos) y Logos en una sola llamada (Ahorro)
    features = [
        {"type_": vision.Feature.Type.OBJECT_LOCALIZATION},
        {"type_": vision.Feature.Type.LOGO_DETECTION}
    ]
    request = vision.AnnotateImageRequest(image=image, features=features)
    response = vision_client.annotate_image(request)
    
    registro = {
        "archivo": filename,
        "tiene_marcos": False,
        "detalles_marcos": [],
        "logos_detectados": []
    }

    # 1. Procesar Marcos (Bordes/Rectángulos)
    for obj in response.localized_object_annotations:
        name = obj.name.lower()
        if any(x in name for x in ['frame', 'border', 'rectangle', 'window']):
            registro["tiene_marcos"] = True
            vertices = [{"x": v.x, "y": v.y} for v in obj.bounding_poly.normalized_vertices]
            registro["detalles_marcos"].append({
                "objeto": obj.name,
                "confianza": round(obj.score, 2),
                "coordenadas": vertices
            })

    # 2. Procesar Logos (Si los hay)
    for logo in response.logo_annotations:
        v = logo.bounding_poly.vertices
        registro["logos_detectados"].append({
            "entidad": logo.description,
            "score": round(logo.score, 2),
            "vertices_px": [{"x": p.x, "y": p.y} for p in v]
        })

    # Si no se detectó nada, asegurar que existan los campos en 0 o vacíos como pediste
    if not registro["detalles_marcos"]:
        registro["detalles_marcos"] = [{"objeto": "ninguno", "coordenadas": [{"x": 0, "y": 0}]}]

    return registro

def main():
    try:
        send_telegram("🚀 Iniciando detección en lote de 10 imágenes...")
        drive_service, vision_client = get_services()
        reporte_final = []

        # Función para procesar cada imagen individualmente en el hilo
        def procesar_imagen(nombre):
            content = download_image(drive_service, nombre)
            if content:
                return analizar_marcos_y_logos(vision_client, content, nombre)
            return {"archivo": nombre, "error": "No encontrado en Drive"}

        # Procesamiento paralelo de las 10 imágenes
        with ThreadPoolExecutor(max_workers=10) as executor:
            reporte_final = list(executor.map(procesar_imagen, IMAGENES_A_PROCESAR))

        # Guardar y subir el JSON
        output_file = 'reporte_marcos_logos.json'
        with open(output_file, 'w') as f:
            json.dump(reporte_final, f, indent=2)

        # Subir (o actualizar) el archivo en Drive
        media = MediaFileUpload(output_file, mimetype='application/json')
        existing = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and name='{output_file}'", 
            fields="files(id)"
        ).execute()

        if existing.get('files'):
            drive_service.files().update(fileId=existing['files'][0]['id'], media_body=media).execute()
        else:
            drive_service.files().create(
                body={'name': output_file, 'parents': [FOLDER_ID]}, 
                media_body=media
            ).execute()

        send_telegram(f"✅ Reporte generado con {len(reporte_final)} registros.")

    except Exception as e:
        send_telegram(f"❌ Error crítico en el Script: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()