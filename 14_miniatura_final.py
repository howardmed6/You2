import os
import json
import sys
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io
import requests

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TARGET_WIDTH = 1588
TARGET_HEIGHT = 937

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

def upload_file(service, filename, drive_name=None):
    results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='{drive_name or filename}' and trashed=false", fields="files(id)").execute()
    file_id = results['files'][0]['id'] if results.get('files') else None
    media = MediaFileUpload(filename, mimetype='image/jpeg')
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(body={'name': drive_name or filename, 'parents': [FOLDER_ID]}, media_body=media).execute()

try:
    send_telegram("🎨 Script 14: Recorte final y texto...")
    service = get_drive_service()
    
    download_file(service, 'fotograma_sin_logo.jpg')
    
    img = Image.open('fotograma_sin_logo.jpg')
    width, height = img.size
    
    # Calcular ratio objetivo
    target_ratio = TARGET_WIDTH / TARGET_HEIGHT
    current_ratio = width / height
    
    # Determinar si necesita zoom o recorte
    if current_ratio > target_ratio:
        # Imagen muy ancha - recortar/zoom en ancho
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        img = img.crop((left, 0, left + new_width, height))
    else:
        # Imagen muy alta - recortar/zoom en alto
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        img = img.crop((0, top, width, top + new_height))
    
    # Redimensionar a tamaño objetivo
    img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    
    # Agregar texto "Trailer Oficial"
    draw = ImageDraw.Draw(img)
    
    # Intentar cargar fuente, usar default si falla
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except:
        font = ImageFont.load_default()
    
    # Posición: esquina inferior derecha
    text_lines = ["TRAILER", "OFICIAL"]
    padding = 30
    
    # Calcular dimensiones del texto
    line_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in text_lines]
    total_height = sum(line_heights) + 10  # 10px entre líneas
    
    y_position = TARGET_HEIGHT - total_height - padding
    
    for i, line in enumerate(text_lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x_position = TARGET_WIDTH - text_width - padding
        
        # Sombra negra
        draw.text((x_position + 2, y_position + 2), line, font=font, fill=(0, 0, 0, 180))
        # Texto blanco
        draw.text((x_position, y_position), line, font=font, fill=(255, 255, 255, 255))
        
        y_position += line_heights[i] + 10
    
    # Guardar miniatura final
    img.save('miniatura_final.jpg', quality=95)
    
    # Subir a Drive
    upload_file(service, 'miniatura_final.jpg')
    
    send_telegram(f"✅ Script 14: Miniatura lista {TARGET_WIDTH}x{TARGET_HEIGHT}px")
    
except Exception as e:
    send_telegram(f"❌ Script 14 falló: {str(e)}")
    sys.exit(1)