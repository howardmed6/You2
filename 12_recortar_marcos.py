import os
import json
import sys
import io
from PIL import Image
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import requests

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                     json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_drive_service():
    creds = Credentials.from_service_account_info(
        json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS']),
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def download_file(service, filename):
    q = f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=false"
    results = service.files().list(q=q, fields="files(id)").execute()
    if not results.get('files'): return None
    
    file_id = results['files'][0]['id']
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done: _, done = downloader.next_chunk()
    
    with open(filename, 'wb') as f:
        f.write(fh.getvalue())
    return file_id

try:
    send_telegram("✂️ Script 12: Recortando marcos de 10 imágenes...")
    service = get_drive_service()
    
    download_file(service, 'reporte_marcos_logos.json')
    with open('reporte_marcos_logos.json', 'r') as f:
        reporte = json.load(f)
    
    recortadas = 0
    sin_marcos = 0
    
    for item in reporte:
        nombre = item['archivo']
        file_id = download_file(service, nombre)
        if not file_id: continue
        
        if item['tiene_marcos'] and item['detalles_marcos']:
            coords = next((d['coordenadas'] for d in item['detalles_marcos'] 
                          if d.get('objeto') == 'Area_Util_Video'), None)
            
            if coords:
                img = Image.open(nombre)
                w, h = img.size
                x1, y1 = int(coords[0]['x'] * w), int(coords[0]['y'] * h)
                x2, y2 = int(coords[2]['x'] * w), int(coords[2]['y'] * h)
                
                img.crop((x1, y1, x2, y2)).save(nombre, quality=95)
                
                media = MediaFileUpload(nombre, mimetype='image/jpeg')
                service.files().update(fileId=file_id, media_body=media).execute()
                recortadas += 1
            else:
                sin_marcos += 1
        else:
            sin_marcos += 1
    
    send_telegram(f"✅ Script 12: {recortadas} recortadas, {sin_marcos} sin marcos")

except Exception as e:
    send_telegram(f"❌ Script 12: {str(e)}")
    sys.exit(1)