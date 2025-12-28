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
    send_telegram("🎯 Script 14: Recortando logos inteligentemente...")
    service = get_drive_service()
    
    download_file(service, 'reporte_logos.json')
    with open('reporte_logos.json', 'r') as f:
        reporte = json.load(f)
    
    recortadas = 0
    sin_logos = 0
    
    for item in reporte:
        nombre = item['archivo']
        logos = item.get('logos_detectados', [])
        
        file_id = download_file(service, nombre)
        if not file_id: continue
        
        if not logos:
            sin_logos += 1
            continue
        
        img = Image.open(nombre)
        w, h = img.size
        
        # Procesar cada logo (normalmente hay 1, pero puede haber más)
        for logo in logos:
            vertices = logo['vertices_px']
            x_vals = [v['x'] for v in vertices]
            y_vals = [v['y'] for v in vertices]
            
            logo_left = min(x_vals)
            logo_right = max(x_vals)
            logo_top = min(y_vals)
            logo_bottom = max(y_vals)
            logo_width = logo_right - logo_left
            logo_height = logo_bottom - logo_top
            
            # Determinar esquina
            esquina = ""
            if logo_top < h * 0.25:
                esquina += "Sup."
            elif logo_bottom > h * 0.75:
                esquina += "Inf."
            
            if logo_left < w * 0.25:
                esquina += "Izq"
            elif logo_right > w * 0.75:
                esquina += "Der"
            
            # Calcular pérdida de píxeles
            perdida_y = logo_height * w
            perdida_x = logo_width * h
            
            # Decidir el corte óptimo
            if perdida_y < perdida_x:
                if "Sup" in esquina:
                    img = img.crop((0, int(logo_bottom) + 5, w, h))
                    decision = "↓arriba"
                else:
                    img = img.crop((0, 0, w, int(logo_top) - 5))
                    decision = "↑abajo"
            else:
                if "Izq" in esquina:
                    img = img.crop((int(logo_right) + 5, 0, w, h))
                    decision = "→izq"
                else:
                    img = img.crop((0, 0, int(logo_left) - 5, h))
                    decision = "←der"
            
            w, h = img.size  # Actualizar dimensiones para próximo logo
        
        img.save(nombre, quality=95)
        media = MediaFileUpload(nombre, mimetype='image/jpeg')
        service.files().update(fileId=file_id, media_body=media).execute()
        recortadas += 1
    
    send_telegram(f"✅ Script 14: {recortadas} logos recortados, {sin_logos} sin logos")

except Exception as e:
    send_telegram(f"❌ Script 14: {str(e)}")
    sys.exit(1)