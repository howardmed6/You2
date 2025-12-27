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
    send_telegram("🎯 Script 13: Recortando logo inteligentemente...")
    service = get_drive_service()
    
    download_file(service, 'logo.json')
    download_file(service, 'fotograma_sin_marcos.jpg')
    
    with open('logo.json', 'r') as f:
        logo_data = json.load(f)
    
    img = Image.open('fotograma_sin_marcos.jpg')
    width, height = img.size
    
    if not logo_data or logo_data.get('logo') is None:
        img.save('fotograma_sin_logo.jpg', quality=95)
        send_telegram("⚠️ Script 13: Sin logo, continuando...")
        sys.exit(0)
    
    coords = logo_data.get('coordenadas', [])
    x_vals = [c[0] for c in coords]
    y_vals = [c[1] for c in coords]
    
    logo_left = min(x_vals)
    logo_right = max(x_vals)
    logo_top = min(y_vals)
    logo_bottom = max(y_vals)
    logo_width = logo_right - logo_left
    logo_height = logo_bottom - logo_top
    
    # Determinar esquina
    esquina = ""
    if logo_top < height * 0.25:
        esquina += "Superior "
    elif logo_bottom > height * 0.75:
        esquina += "Inferior "
    
    if logo_left < width * 0.25:
        esquina += "Izquierda"
    elif logo_right > width * 0.75:
        esquina += "Derecha"
    
    # Calcular pérdida de píxeles para cada opción
    perdida_y = logo_height * width  # Cortar en eje Y (arriba/abajo)
    perdida_x = logo_width * height   # Cortar en eje X (izquierda/derecha)
    
    # Elegir el corte que salva más área
    if perdida_y < perdida_x:
        # Cortar verticalmente (quitar franja superior o inferior)
        if "Superior" in esquina:
            img_cropped = img.crop((0, int(logo_bottom) + 5, width, height))
            decision = "superior"
        else:
            img_cropped = img.crop((0, 0, width, int(logo_top) - 5))
            decision = "inferior"
    else:
        # Cortar horizontalmente (quitar franja lateral)
        if "Izquierda" in esquina:
            img_cropped = img.crop((int(logo_right) + 5, 0, width, height))
            decision = "izquierda"
        else:
            img_cropped = img.crop((0, 0, int(logo_left) - 5, height))
            decision = "derecha"
    
    img_cropped.save('fotograma_sin_logo.jpg', quality=95)
    send_telegram(f"✅ Script 13: Logo cortado ({esquina}) - Decisión: {decision}")
    
except Exception as e:
    send_telegram(f"❌ Script 13 falló: {str(e)}")
    sys.exit(1)