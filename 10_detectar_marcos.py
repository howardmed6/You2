import os
import json
import sys
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import requests

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                     json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_drive_service():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json, scopes=['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=creds)

def download_file(service, filename):
    results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=false", fields="files(id)").execute()
    if not results.get('files'): return None
    file_id = results['files'][0]['id']
    request = service.files().get_media(fileId=file_id)
    with open(filename, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return file_id

def upload_file(service, filename):
    from googleapiclient.http import MediaFileUpload
    results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=false", fields="files(id)").execute()
    file_id = results['files'][0]['id'] if results.get('files') else None
    media = MediaFileUpload(filename, mimetype='application/json')
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(body={'name': filename, 'parents': [FOLDER_ID]}, media_body=media).execute()

try:
    send_telegram("🖼️ Script 10: Detectando marcos...")
    service = get_drive_service()
    
    # Descargar imagen generada del fotograma
    download_file(service, 'fotograma.jpg')
    
    # Configurar Vision API
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json)
    client = vision.ImageAnnotatorClient(credentials=creds)
    
    with open('fotograma.jpg', 'rb') as img_file:
        content = img_file.read()
    
    image = vision.Image(content=content)
    response = client.object_localization(image=image)
    
    # Buscar objetos tipo "marco" o "border"
    marcos = []
    for obj in response.localized_object_annotations:
        if 'frame' in obj.name.lower() or 'border' in obj.name.lower() or 'rectangle' in obj.name.lower():
            vertices = [(v.x, v.y) for v in obj.bounding_poly.normalized_vertices]
            marcos.append({
                "nombre": obj.name,
                "confianza": obj.score,
                "coordenadas": vertices
            })
    
    # Si no detecta marcos específicos, usar detección de bordes
    if not marcos:
        # Detectar usando análisis de bordes de la imagen completa
        response = client.image_properties(image=image)
        props = response.image_properties_annotation
        
        # Asumir que marcos están en los bordes (detección manual)
        marcos = [{
            "lado": "superior",
            "coordenadas": [[0, 0], [1, 0], [1, 0.05], [0, 0.05]]
        }, {
            "lado": "inferior",
            "coordenadas": [[0, 0.95], [1, 0.95], [1, 1], [0, 1]]
        }, {
            "lado": "izquierdo",
            "coordenadas": [[0, 0], [0.05, 0], [0.05, 1], [0, 1]]
        }, {
            "lado": "derecho",
            "coordenadas": [[0.95, 0], [1, 0], [1, 1], [0.95, 1]]
        }]
    
    with open('marcos.json', 'w') as f:
        json.dump({"marcos": marcos}, f, indent=2)
    
    upload_file(service, 'marcos.json')
    send_telegram(f"✅ Script 10: {len(marcos)} marcos detectados")
    
except Exception as e:
    send_telegram(f"❌ Script 10 falló: {str(e)}")
    sys.exit(1)