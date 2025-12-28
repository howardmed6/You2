import os
import json
import sys
from PIL import Image
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
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

try:
    send_telegram("✂️ Script 11: Recortando marcos...")
    service = get_drive_service()
    
    download_file(service, 'marcos.json')
    download_file(service, 'fotograma.jpg')
    
    with open('marcos.json', 'r') as f:
        marcos_data = json.load(f)
    
    img = Image.open('fotograma.jpg')
    width, height = img.size
    
    # Calcular área a recortar basándose en marcos detectados
    crop_left = crop_top = 0
    crop_right = width
    crop_bottom = height
    
    for marco in marcos_data.get('marcos', []):
        coords = marco.get('coordenadas', [])
        if coords:
            # Convertir coordenadas normalizadas a píxeles
            if isinstance(coords[0], list):
                x_vals = [c[0] * width for c in coords]
                y_vals = [c[1] * height for c in coords]
            else:
                x_vals = [coords[0] * width, coords[2] * width]
                y_vals = [coords[1] * height, coords[3] * height]
            
            lado = marco.get('lado', '')
            if 'superior' in lado or min(y_vals) < height * 0.1:
                crop_top = max(crop_top, int(max(y_vals)))
            elif 'inferior' in lado or max(y_vals) > height * 0.9:
                crop_bottom = min(crop_bottom, int(min(y_vals)))
            elif 'izquierdo' in lado or min(x_vals) < width * 0.1:
                crop_left = max(crop_left, int(max(x_vals)))
            elif 'derecho' in lado or max(x_vals) > width * 0.9:
                crop_right = min(crop_right, int(min(x_vals)))
    
    # Aplicar recorte
    img_cropped = img.crop((crop_left, crop_top, crop_right, crop_bottom))
    img_cropped.save('fotograma_sin_marcos.jpg', quality=95)
    
    send_telegram(f"✅ Script 11: Marcos recortados ({crop_left},{crop_top},{crop_right},{crop_bottom})")
    
except Exception as e:
    send_telegram(f"❌ Script 11 falló: {str(e)}")
    sys.exit(1)