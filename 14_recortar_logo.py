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
    send_telegram("🎯 Script 14: Ejecutando recortes inteligentes...")
    service = get_drive_service()
    
    download_file(service, 'reporte_marcos_logos.json')
    with open('reporte_marcos_logos.json', 'r') as f:
        reporte = json.load(f)
    
    recortadas = 0
    sin_logos = 0
    
    for item in reporte:
        nombre = item['archivo']
        lado = item.get('lado_a_cortar')
        logos = item.get('logos_detectados', [])
        
        if not lado or not logos:
            sin_logos += 1
            continue
        
        file_id = download_file(service, nombre)
        if not file_id: continue
        
        img = Image.open(nombre)
        w, h = img.size
        
        # Obtener coordenadas del logo
        logo = logos[0]
        vertices = logo['vertices_px']
        x_vals = [v['x'] for v in vertices]
        y_vals = [v['y'] for v in vertices]
        
        logo_left = min(x_vals)
        logo_right = max(x_vals)
        logo_top = min(y_vals)
        logo_bottom = max(y_vals)
        
        try:
            # Ejecutar el corte según la decisión de Script 13
            if lado == 'arriba':
                img = img.crop((0, int(logo_bottom) + 5, w, h))
            elif lado == 'abajo':
                img = img.crop((0, 0, w, int(logo_top) - 5))
            elif lado == 'izquierda':
                img = img.crop((int(logo_right) + 5, 0, w, h))
            elif lado == 'derecha':
                img = img.crop((0, 0, int(logo_left) - 5, h))
            
            img.save(nombre, quality=95)
            media = MediaFileUpload(nombre, mimetype='image/jpeg')
            service.files().update(fileId=file_id, media_body=media).execute()
            recortadas += 1
        except Exception:
            # Si falla el crop (coordenadas inválidas por logo en borde), saltamos
            sin_logos += 1
            continue
    
    send_telegram(f"✅ Script 14: {recortadas} logos recortados, {sin_logos} sin logos")
except Exception as e:
    send_telegram(f"❌ Script 14: {str(e)}")
    sys.exit(1)