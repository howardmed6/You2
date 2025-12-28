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

def procesar_miniatura(input_filename, recorte_coords):
    """Usa coordenadas de recorte inteligentes calculadas por Script 13"""
    img = Image.open(input_filename)
    
    # Aplicar recorte inteligente
    if recorte_coords:
        x = recorte_coords['x']
        y = recorte_coords['y']
        w = recorte_coords['width']
        h = recorte_coords['height']
        img = img.crop((x, y, x + w, y + h))
    
    # Redimensionar al tamaño objetivo
    img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    
    # Agregar texto "TRAILER OFICIAL"
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    text_lines = ["TRAILER", "OFICIAL"]
    padding = 40
    line_spacing = 10
    
    line_heights = []
    for line in text_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
    
    total_height = sum(line_heights) + line_spacing
    y_position = TARGET_HEIGHT - total_height - padding
    
    for i, line in enumerate(text_lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x_position = TARGET_WIDTH - text_width - padding
        
        draw.text((x_position + 3, y_position + 3), line, font=font, fill=(0, 0, 0, 200))
        draw.text((x_position, y_position), line, font=font, fill=(255, 255, 255))
        
        y_position += line_heights[i] + line_spacing
    
    return img

try:
    send_telegram(f"🎨 Script 15: Procesando 10 miniaturas {TARGET_WIDTH}x{TARGET_HEIGHT}...")
    service = get_drive_service()
    
    # Leer JSON con coordenadas de recorte
    download_file(service, 'reporte_marcos_logos.json')
    with open('reporte_marcos_logos.json', 'r') as f:
        reporte = json.load(f)
    
    procesadas = 0
    errores = 0
    
    for item in reporte:
        nombre = item['archivo']
        recorte = item.get('recorte_final')
        
        try:
            file_id = download_file(service, nombre)
            if not file_id:
                print(f"⚠️ {nombre} no encontrada")
                errores += 1
                continue
            
            # Procesar con coordenadas inteligentes
            img_final = procesar_miniatura(nombre, recorte)
            img_final.save(nombre, quality=95)
            
            # Actualizar en Drive
            media = MediaFileUpload(nombre, mimetype='image/jpeg')
            service.files().update(fileId=file_id, media_body=media).execute()
            procesadas += 1
            print(f"✅ {nombre} → miniatura")
            
        except Exception as e:
            print(f"❌ Error en {nombre}: {e}")
            errores += 1
    
    send_telegram(f"✅ Script 15: {procesadas} miniaturas listas, {errores} errores")

except Exception as e:
    send_telegram(f"❌ Script 15: {str(e)}")
    sys.exit(1)