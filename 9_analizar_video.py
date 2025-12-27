import os
import json
import sys
from google.cloud import videointelligence_v1 as vi
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
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

def upload_file(service, filename):
    from googleapiclient.http import MediaFileUpload
    results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=false", fields="files(id)").execute()
    file_id = results['files'][0]['id'] if results.get('files') else None
    media = MediaFileUpload(filename, mimetype='application/json')
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(body={'name': filename, 'parents': [FOLDER_ID]}, media_body=media).execute()

try:
    send_telegram("🎬 Script 9: Iniciando análisis de video...")
    service = get_drive_service()
    
    # Descargar descargar.json
    download_file(service, 'descargar.json')
    with open('descargar.json', 'r') as f:
        video_data = json.load(f)
    
    video_title = video_data.get('titulo', 'video')
    
    # Buscar video .mp4 en Drive (solo hay uno)
    results = service.files().list(q=f"'{FOLDER_ID}' in parents and name contains '.mp4' and trashed=false", fields="files(id, name)").execute()
    
    if not results.get('files'):
        send_telegram("❌ Video .mp4 no encontrado en Drive")
        sys.exit(1)
    
    video_file = results['files'][0]
    video_uri = f"gs://project-7a7cfe54-b055-48bc-808/{video_file['id']}"  # Ajustar según tu bucket
    
    # Configurar Video Intelligence
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json)
    client = vi.VideoIntelligenceServiceClient(credentials=creds)
    
    # Analizar video con prompt optimizado
    features = [vi.Feature.LABEL_DETECTION, vi.Feature.SHOT_CHANGE_DETECTION]
    config = vi.LabelDetectionConfig(model="builtin/latest")
    
    operation = client.annotate_video(
        request={
            "features": features,
            "input_uri": video_uri,
            "label_detection_config": config
        }
    )
    
    result = operation.result(timeout=600)
    
    # Buscar mejor fotograma (centro, personajes principales)
    best_time = 0
    max_confidence = 0
    
    for annotation in result.annotation_results[0].shot_label_annotations:
        for segment in annotation.segments:
            if segment.confidence > max_confidence:
                max_confidence = segment.confidence
                best_time = (segment.segment.start_time_offset.seconds + segment.segment.end_time_offset.seconds) / 2
    
    # Si no hay resultados, usar mitad del video
    if best_time == 0 and result.annotation_results[0].shot_annotations:
        first_shot = result.annotation_results[0].shot_annotations[0]
        best_time = (first_shot.start_time_offset.seconds + first_shot.end_time_offset.seconds) / 2
    
    # Convertir a nanosegundos
    nanos = int(best_time * 1e9)
    
    # Descargar video y extraer fotograma
    download_file(service, video_file['name'])
    
    # Extraer fotograma usando ffmpeg
    import subprocess
    cmd = [
        'ffmpeg', '-ss', str(best_time), '-i', video_file['name'],
        '-vframes', '1', '-q:v', '2', '-y', 'fotograma.jpg'
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)
    
    # Subir fotograma a Drive
    if os.path.exists('fotograma.jpg'):
        upload_file(service, 'fotograma.jpg')
    
    # Guardar en registro.json
    registro = {
        "titulo": video_title,
        "video_archivo": video_file['name'],
        "fotograma_segundos": int(best_time),
        "fotograma_nanos": nanos,
        "timestamp": int(best_time)
    }
    
    with open('registro.json', 'w') as f:
        json.dump(registro, f, indent=2)
    
    upload_file(service, 'registro.json')
    send_telegram(f"✅ Script 9: Fotograma óptimo en {int(best_time)}s")
    
except Exception as e:
    send_telegram(f"❌ Script 9 falló: {str(e)}")
    sys.exit(1)