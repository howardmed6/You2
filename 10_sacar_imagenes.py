import os
import json
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import cv2
import requests

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                         json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
        except: pass

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

try:
    send_telegram("🚀 Script 10: Extrayendo fotogramas del video...")
    service = get_drive_service()
    
    # 1. Descargar registro.json
    query = f"'{FOLDER_ID}' in parents and name='registro.json' and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    if not results.get('files'):
        send_telegram("❌ No se encontró registro.json")
        sys.exit(1)
    
    download_file_from_drive(service, results['files'][0]['id'], 'registro.json')
    
    with open('registro.json', 'r') as f:
        registro = json.load(f)
    
    # 2. Descargar el video
    folder_results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='SnapTube Video'", fields="files(id)").execute()
    snaptube_id = folder_results['files'][0]['id']
    video_results = service.files().list(q=f"'{snaptube_id}' in parents and mimeType contains 'video/mp4'", fields="files(id, name)").execute()
    video_file = video_results['files'][0]
    
    send_telegram(f"📥 Descargando video: {video_file['name']}")
    download_file_from_drive(service, video_file['id'], 'video.mp4')
    
    # 3. Extraer fotogramas
    mejores_fotogramas = registro.get('mejores_fotogramas', [])
    total = len(mejores_fotogramas)
    
    send_telegram(f"🎬 Extrayendo {total} fotogramas...")
    
    cap = cv2.VideoCapture('video.mp4')
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    for i, fotograma in enumerate(mejores_fotogramas, 1):
        tiempo_exacto = fotograma['tiempo_exacto']
        frame_number = int(tiempo_exacto * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if ret:
            imagen_nombre = f'imagen{i}.jpg'
            cv2.imwrite(imagen_nombre, frame)
            send_telegram(f"✅ Extraída: {imagen_nombre} (tiempo: {fotograma.get('tiempo_legible', tiempo_exacto)}s)")
        else:
            send_telegram(f"⚠️ No se pudo extraer imagen{i} en tiempo {tiempo_exacto}s")
    
    cap.release()
    
    send_telegram(f"🎉 Proceso completado: {total} imágenes extraídas (se subirán al finalizar todos los scripts)")

except Exception as e:
    send_telegram(f"❌ Error en Script 10: {str(e)}")
    sys.exit(1)