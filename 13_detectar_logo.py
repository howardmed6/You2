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
    send_telegram("🔍 Script 12: Detectando logo...")
    service = get_drive_service()
    
    download_file(service, 'fotograma_sin_marcos.jpg')
    
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json)
    client = vision.ImageAnnotatorClient(credentials=creds)
    
    with open('fotograma_sin_marcos.jpg', 'rb') as img_file:
        content = img_file.read()
    
    image = vision.Image(content=content)
    response = client.logo_detection(image=image)
    
    logo_info = None
    if response.logo_annotations:
        logo = response.logo_annotations[0]
        vertices = [(v.x, v.y) for v in logo.bounding_poly.vertices]
        logo_info = {
            "nombre": logo.description,
            "confianza": logo.score,
            "coordenadas": vertices,
            "ancho": max(v[0] for v in vertices) - min(v[0] for v in vertices),
            "alto": max(v[1] for v in vertices) - min(v[1] for v in vertices)
        }
    
    with open('logo.json', 'w') as f:
        json.dump(logo_info or {"logo": None}, f, indent=2)
    
    upload_file(service, 'logo.json')
    send_telegram(f"✅ Script 12: Logo {'detectado' if logo_info else 'no encontrado'}")
    
except Exception as e:
    send_telegram(f"❌ Script 12 falló: {str(e)}")
    sys.exit(1)