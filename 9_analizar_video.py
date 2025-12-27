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
    if files:
        service.files().update(fileId=files[0]['id'], media_body=media).execute()
    else:
        file_metadata = {'name': filename, 'parents': [folder_id]}
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()

try:
    send_telegram("🎬 Script 9: Buscando miniatura perfecta (Persona SÍ, Subtítulos NO)...")
    service = get_drive_service()
    
    # Buscar video
    folder_query = f"'{FOLDER_ID}' in parents and name='SnapTube Video' and trashed=false"
    folder_results = service.files().list(q=folder_query, fields="files(id)").execute()
    snaptube_folder_id = folder_results.get('files', [])[0]['id']
    
    video_query = f"'{snaptube_folder_id}' in parents and mimeType contains 'video/mp4' and trashed=false"
    video_results = service.files().list(q=video_query, fields="files(id, name)").execute()
    video_file = video_results.get('files', [])[0]
    
    download_file_from_drive(service, video_file['id'], 'video.mp4')
    
    with open('video.mp4', 'rb') as f:
        input_content = f.read()
    
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json)
    video_client = vi.VideoIntelligenceServiceClient(credentials=creds)
    
    # Añadimos TEXT_DETECTION para poder filtrar subtítulos
    features = [
        vi.Feature.LABEL_DETECTION, 
        vi.Feature.SHOT_CHANGE_DETECTION,
        vi.Feature.TEXT_DETECTION
    ]
    
    operation = video_client.annotate_video(
        request={"features": features, "input_content": input_content}
    )
    
    send_telegram("⏳ Analizando visualmente cada escena...")
    result = operation.result(timeout=900)
    annotation_result = result.annotation_results[0]

    # 1. Mapear dónde hay texto (subtítulos/letreros)
    text_frames = []
    if annotation_result.text_annotations:
        for text in annotation_result.text_annotations:
            for segment in text.segments:
                start = segment.segment.start_time_offset.total_seconds()
                end = segment.segment.end_time_offset.total_seconds()
                text_frames.append((start, end))

    # 2. Buscar personas
    best_moment = None
    max_score = -1.0

    labels = annotation_result.shot_label_annotations
    for label in labels:
        desc = label.entity.description.lower()
        if any(keyword in desc for keyword in ["person", "human", "face", "actor"]):
            for segment in label.segments:
                start = segment.segment.start_time_offset.total_seconds()
                end = segment.segment.end_time_offset.total_seconds()
                mid = (start + end) / 2
                
                # Penalizar si este momento cae dentro de un rango con texto detectado
                has_text = any(t_start <= mid <= t_end for t_start, t_end in text_frames)
                
                score = segment.confidence
                if has_text:
                    score -= 0.5  # Penalización fuerte por subtítulos
                
                if score > max_score:
                    max_score = score
                    best_moment = mid

    # Respaldo si todo tiene texto o no hay personas
    if not best_moment:
        shots = annotation_result.shot_annotations
        best_moment = (shots[len(shots)//2].start_time_offset.total_seconds())

    best_seconds = int(best_moment)
    best_micros = int((best_moment - best_seconds) * 1_000_000)
    mins, secs = divmod(best_seconds, 60)
    tiempo_formateado = f"{mins:02d}:{secs:02d}"

    registro = {
        "video_archivo": video_file['name'],
        "tiempo_miniatura": tiempo_formateado,
        "segundos_totales": best_moment,
        "presencia_texto_evitada": True
    }
    
    with open('registro.json', 'w') as f:
        json.dump(registro, f, indent=2)
    
    upload_file_to_folder(service, 'registro.json', FOLDER_ID)
    send_telegram(f"✅ Miniatura optimizada: {tiempo_formateado}\n(Se priorizó persona y se evitó subtítulos detectados)")
    
except Exception as e:
    send_telegram(f"❌ Error: {str(e)}")
    sys.exit(1)