import os
import json
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import requests
import cv2

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

def download_file_from_drive(service, file_id, destination):
    request = service.files().get_media(fileId=file_id)
    with open(destination, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

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
    
    # Buscar carpeta SnapTube Video
    folder_query = f"'{FOLDER_ID}' in parents and name='SnapTube Video' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    folder_results = service.files().list(q=folder_query, fields="files(id, name)").execute()
    folders = folder_results.get('files', [])
    
    if not folders:
        send_telegram("❌ Carpeta 'SnapTube Video' no encontrada")
        sys.exit(1)
    
    snaptube_folder_id = folders[0]['id']
    
    # Buscar video .mp4
    video_query = f"'{snaptube_folder_id}' in parents and mimeType contains 'video/mp4' and trashed=false"
    video_results = service.files().list(q=video_query, fields="files(id, name)").execute()
    videos = video_results.get('files', [])
    
    if not videos:
        send_telegram("❌ Video .mp4 no encontrado")
        sys.exit(1)
    
    video_file = videos[0]
    video_filename = video_file['name']
    
    send_telegram(f"📹 Descargando: {video_filename}")
    download_file_from_drive(service, video_file['id'], video_filename)
    
    # Extraer fotograma con OpenCV
    video = cv2.VideoCapture(video_filename)
    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    best_time = min(duration * 0.3, duration / 2) if duration > 0 else 5
    target_frame = int(best_time * fps)
    
    video.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ret, frame = video.read()
    
    if ret:
        cv2.imwrite('fotograma.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        video.release()
        
        upload_file(service, 'fotograma.jpg')
        
        registro = {
            "video_archivo": video_filename,
            "video_drive_id": video_file['id'],
            "fotograma_segundos": int(best_time),
            "fotograma_nanos": int(best_time * 1e9),
            "timestamp": int(best_time),
            "duracion_total": int(duration)
        }
        
        with open('registro.json', 'w') as f:
            json.dump(registro, f, indent=2)
        
        upload_file(service, 'registro.json')
        send_telegram(f"✅ Script 9: Fotograma en {int(best_time)}s de {int(duration)}s")
    else:
        send_telegram("❌ Error extrayendo fotograma")
        sys.exit(1)
    
except Exception as e:
    send_telegram(f"❌ Script 9: {str(e)}")
    sys.exit(1)