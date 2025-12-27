import os
import json
import sys
import subprocess
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
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

def upload_file(service, filename):
    results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=false", fields="files(id)").execute()
    files = results.get('files', [])
    file_id = files[0]['id'] if files else None
    
    mimetype = 'application/json' if filename.endswith('.json') else 'image/jpeg'
    media = MediaFileUpload(filename, mimetype=mimetype)
    
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(body={'name': filename, 'parents': [FOLDER_ID]}, media_body=media).execute()

try:
    send_telegram("🎬 Script 9: Iniciando análisis de video...")
    service = get_drive_service()
    
    # Buscar video .mp4 en la carpeta 'SnapTube Video'
    VIDEO_FOLDER = 'SnapTube Video'
    
    if not os.path.exists(VIDEO_FOLDER):
        send_telegram(f"❌ Carpeta '{VIDEO_FOLDER}' no encontrada")
        sys.exit(1)
    
    # Buscar archivo .mp4 en la carpeta (siempre hay uno)
    video_files = [f for f in os.listdir(VIDEO_FOLDER) if f.endswith('.mp4')]
    
    if not video_files:
        send_telegram(f"❌ Video .mp4 no encontrado en '{VIDEO_FOLDER}'")
        sys.exit(1)
    
    video_filename = video_files[0]
    video_path = os.path.join(VIDEO_FOLDER, video_filename)
    
    send_telegram(f"📹 Video encontrado: {video_filename}")
    
    # Calcular duración del video
    duration_cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
    duration = float(result.stdout.strip()) if result.stdout.strip() else 0
    
    # Extraer fotograma del medio del video (o 30% si es muy largo)
    if duration > 0:
        best_time = min(duration * 0.3, duration / 2)
    else:
        best_time = 5  # Por defecto 5 segundos
    
    send_telegram(f"⏱️ Extrayendo fotograma en {int(best_time)}s...")
    
    # Extraer fotograma usando ffmpeg
    cmd = [
        'ffmpeg', '-ss', str(best_time), '-i', video_path,
        '-vframes', '1', '-q:v', '2', '-y', 'fotograma.jpg'
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)
    
    # Verificar que se creó el fotograma
    if not os.path.exists('fotograma.jpg'):
        send_telegram("❌ No se pudo extraer fotograma")
        sys.exit(1)
    
    # Subir fotograma a Drive
    upload_file(service, 'fotograma.jpg')
    
    # Convertir a nanosegundos
    nanos = int(best_time * 1e9)
    
    # Guardar en registro.json
    registro = {
        "video_archivo": video_filename,
        "video_ruta": video_path,
        "fotograma_segundos": int(best_time),
        "fotograma_nanos": nanos,
        "timestamp": int(best_time)
    }
    
    with open('registro.json', 'w') as f:
        json.dump(registro, f, indent=2)
    
    upload_file(service, 'registro.json')
    send_telegram(f"✅ Script 9: Fotograma extraído en {int(best_time)}s y subido a Drive")
    
except Exception as e:
    send_telegram(f"❌ Script 9 falló: {str(e)}")
    import traceback
    send_telegram(f"📋 Traceback: {traceback.format_exc()[:500]}")
    sys.exit(1)