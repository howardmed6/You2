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
    send_telegram("🎬 Script 9: Iniciando análisis inteligente de miniatura...")
    service = get_drive_service()
    
    # Buscar video
    folder_query = f"'{FOLDER_ID}' in parents and name='SnapTube Video' and trashed=false"
    folder_results = service.files().list(q=folder_query, fields="files(id)").execute()
    snaptube_folder_id = folder_results.get('files', [])[0]['id']
    
    video_query = f"'{snaptube_folder_id}' in parents and mimeType contains 'video/mp4' and trashed=false"
    video_results = service.files().list(q=video_query, fields="files(id, name)").execute()
    video_file = video_results.get('files', [])[0]
    
    send_telegram(f"📹 Analizando contenido de: {video_file['name']}")
    download_file_from_drive(service, video_file['id'], 'video.mp4')
    
    with open('video.mp4', 'rb') as f:
        input_content = f.read()
    
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json)
    video_client = vi.VideoIntelligenceServiceClient(credentials=creds)
    
    # ACTIVAMOS LABEL_DETECTION para que la IA "vea" qué hay en el video
    features = [vi.Feature.LABEL_DETECTION, vi.Feature.SHOT_CHANGE_DETECTION]
    operation = video_client.annotate_video(
        request={"features": features, "input_content": input_content}
    )
    
    send_telegram("⏳ La IA está buscando la mejor escena con personas y sin texto...")
    result = operation.result(timeout=900)
    
    # Análisis de etiquetas para encontrar personas
    labels = result.annotation_results[0].shot_label_annotations
    best_moment = None
    highest_confidence = 0.0

    # Palabras clave que queremos (Personas) y las que no (Texto/Créditos)
    target_labels = ["person", "human", "face", "actor"]
    avoid_labels = ["text", "subtitle", "font", "brand", "logo"]

    for label in labels:
        description = label.entity.description.lower()
        
        # Si la etiqueta es sobre personas
        if any(target in description for target in target_labels):
            for segment in label.segments:
                confidence = segment.confidence
                # Priorizar segmentos con alta confianza
                if confidence > highest_confidence:
                    # Calculamos el punto medio de este segmento con personas
                    start = segment.segment.start_time_offset.total_seconds()
                    end = segment.segment.end_time_offset.total_seconds()
                    
                    highest_confidence = confidence
                    best_moment = (start + end) / 2

    # Si no encontró personas, usamos el método del shot central como respaldo
    if not best_moment:
        shots = result.annotation_results[0].shot_annotations
        middle_shot = shots[len(shots) // 2]
        best_moment = (middle_shot.start_time_offset.total_seconds() + middle_shot.end_time_offset.total_seconds()) / 2
        send_telegram("⚠️ No se detectaron personas claras, usando escena central.")

    best_seconds = int(best_moment)
    best_micros = int((best_moment - best_seconds) * 1_000_000)
    
    # Formato mm:ss para Telegram
    mins, secs = divmod(best_seconds, 60)
    tiempo_formateado = f"{mins:02d}:{secs:02d}"

    registro = {
        "video_archivo": video_file['name'],
        "video_drive_id": video_file['id'],
        "start_time_offset": {"seconds": best_seconds, "micros": best_micros},
        "tiempo_legible": tiempo_formateado,
        "metodo": "deteccion_de_personas" if highest_confidence > 0 else "shot_central"
    }
    
    with open('registro.json', 'w') as f:
        json.dump(registro, f, indent=2)
    
    upload_file_to_folder(service, 'registro.json', FOLDER_ID)
    send_telegram(f"✅ ¡Miniatura encontrada! Momento ideal: {tiempo_formateado} (Basado en presencia de personas)")
    
except Exception as e:
    send_telegram(f"❌ Error: {str(e)}")
    sys.exit(1)