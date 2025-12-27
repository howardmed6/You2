import os
import json
import sys
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.cloud import videointelligence_v1 as vi
import requests

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                         json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
        except:
            pass

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

def upload_file_to_folder(service, filename, folder_id):
    query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get('files', [])
    
    mimetype = 'application/json'
    media = MediaFileUpload(filename, mimetype=mimetype)
    
    if files:
        service.files().update(fileId=files[0]['id'], media_body=media).execute()
    else:
        file_metadata = {'name': filename, 'parents': [folder_id]}
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()

try:
    send_telegram("🎬 Script 9: Iniciando análisis con Video Intelligence API...")
    service = get_drive_service()
    
    # Buscar carpeta SnapTube Video
    folder_query = f"'{FOLDER_ID}' in parents and name='SnapTube Video' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    folder_results = service.files().list(q=folder_query, fields="files(id)").execute()
    folders = folder_results.get('files', [])
    
    if not folders:
        send_telegram("❌ Carpeta SnapTube Video no encontrada")
        sys.exit(1)
    
    snaptube_folder_id = folders[0]['id']
    
    # Buscar video
    video_query = f"'{snaptube_folder_id}' in parents and mimeType contains 'video/mp4' and trashed=false"
    video_results = service.files().list(q=video_query, fields="files(id, name)").execute()
    videos = video_results.get('files', [])
    
    if not videos:
        send_telegram("❌ Video no encontrado")
        sys.exit(1)
    
    video_file = videos[0]
    send_telegram(f"📹 Analizando: {video_file['name']}")
    
    # Descargar video
    download_file_from_drive(service, video_file['id'], 'video.mp4')
    
    # Leer video como bytes
    with open('video.mp4', 'rb') as f:
        input_content = f.read()
    
    # Crear cliente Video Intelligence
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json)
    video_client = vi.VideoIntelligenceServiceClient(credentials=creds)
    
    # Analizar video con Shot Change Detection
    features = [vi.Feature.SHOT_CHANGE_DETECTION]
    operation = video_client.annotate_video(
        request={"features": features, "input_content": input_content}
    )
    
    send_telegram("⏳ Procesando video con IA...")
    # Timeout de 15 minutos para videos pesados
    result = operation.result(timeout=900)
    
    # Obtener shots
    shots = result.annotation_results[0].shot_annotations
    
    if not shots:
        send_telegram("❌ No se detectaron shots")
        sys.exit(1)
    
    # Seleccionar shot del medio (mejor representativo)
    index_medio = len(shots) // 2
    middle_shot = shots[index_medio]
    
    # --- CORRECCIÓN DE DATETIME.TIMEDELTA ---
    # Usamos total_seconds() para evitar el error de '.nanos'
    start_ts = middle_shot.start_time_offset.total_seconds()
    end_ts = middle_shot.end_time_offset.total_seconds()
    
    # Promedio para obtener punto medio del shot
    punto_medio_segundos = (start_ts + end_ts) / 2
    
    best_seconds = int(punto_medio_segundos)
    best_micros = int((punto_medio_segundos - best_seconds) * 1_000_000)
    
    # Guardar resultado
    registro = {
        "video_archivo": video_file['name'],
        "video_drive_id": video_file['id'],
        "start_time_offset": {
            "seconds": best_seconds,
            "micros": best_micros
        },
        "total_shots": len(shots),
        "shot_seleccionado": index_medio
    }
    
    with open('registro.json', 'w') as f:
        json.dump(registro, f, indent=2)
    
    upload_file_to_folder(service, 'registro.json', FOLDER_ID)
    send_telegram(f"✅ Script 9: Análisis completado. Shot {index_medio} de {len(shots)} en {best_seconds}s")
    
except Exception as e:
    send_telegram(f"❌ Script 9 Error: {str(e)}")
    import traceback
    # Enviamos el traceback para debuggear mejor si algo más falla
    print(traceback.format_exc())
    send_telegram(f"📋 Detalle: {traceback.format_exc()[-200:]}")
    sys.exit(1)