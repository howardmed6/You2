import os
import json
import sys
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
    media = MediaFileUpload(filename, mimetype='application/json')
    if files:
        service.files().update(fileId=files[0]['id'], media_body=media).execute()
    else:
        file_metadata = {'name': filename, 'parents': [folder_id]}
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()

try:
    send_telegram("🚀 Script 9: Análisis Geográfico (Ignorando subtítulos abajo, permitiendo logos arriba)")
    service = get_drive_service()
    
    # Localizar archivos
    folder_results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='SnapTube Video'", fields="files(id)").execute()
    snaptube_id = folder_results['files'][0]['id']
    video_results = service.files().list(q=f"'{snaptube_id}' in parents and mimeType contains 'video/mp4'", fields="files(id, name)").execute()
    video_file = video_results['files'][0]
    
    download_file_from_drive(service, video_file['id'], 'video.mp4')
    with open('video.mp4', 'rb') as f:
        input_content = f.read()

    creds_dict = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    video_client = vi.VideoIntelligenceServiceClient(credentials=Credentials.from_service_account_info(creds_dict))
    
    # Análisis de etiquetas y texto con coordenadas
    features = [vi.Feature.LABEL_DETECTION, vi.Feature.TEXT_DETECTION]
    operation = video_client.annotate_video(request={"features": features, "input_content": input_content})
    
    send_telegram("⏳ Escaneando frames limpios...")
    result = operation.result(timeout=900)
    annotation = result.annotation_results[0]

    # 1. Identificar intervalos con texto en la zona de subtítulos (30% inferior)
    subtitle_intervals = []
    if annotation.text_annotations:
        for text in annotation.text_annotations:
            for segment in text.segments:
                # Revisar posición del texto (Eje Y: 0 es arriba, 1 es abajo)
                # Si algún vértice está muy abajo, lo tratamos como subtítulo
                y_coords = [v.y for v in segment.frames[0].rotated_bounding_box.vertices]
                max_y = max(y_coords) if y_coords else 0
                
                if max_y > 0.75: # Solo si el texto está en el último cuarto de pantalla
                    start = segment.segment.start_time_offset.total_seconds()
                    end = segment.segment.end_time_offset.total_seconds()
                    subtitle_intervals.append((start, end))

    # 2. Buscar personas que no coincidan con esos intervalos
    best_moment = None
    max_conf = -1.0
    
    if annotation.shot_label_annotations:
        for label in annotation.shot_label_annotations:
            desc = label.entity.description.lower()
            if any(k in desc for k in ["person", "face", "human", "actor", "girl", "boy"]):
                for seg in label.segments:
                    mid = (seg.segment.start_time_offset.total_seconds() + seg.segment.end_time_offset.total_seconds()) / 2
                    
                    # ¿Coincide este momento con un subtítulo detectado abajo?
                    is_subtitle_moment = any(s <= mid <= e for s, e in subtitle_intervals)
                    
                    if not is_subtitle_moment and seg.confidence > max_conf:
                        max_conf = seg.confidence
                        best_moment = mid

    # Si no hay nada ideal, elegir el medio como respaldo
    if best_moment is None:
        best_moment = 30.0 

    best_seconds = int(best_moment)
    mins, secs = divmod(best_seconds, 60)
    tiempo_formateado = f"{mins:02d}:{secs:02d}"

    registro = {
        "video": video_file['name'],
        "tiempo_exacto": best_moment,
        "tiempo_legible": tiempo_formateado,
        "filtro_geografico": "activo"
    }
    
    with open('registro.json', 'w') as f:
        json.dump(registro, f, indent=2)
    
    upload_file_to_folder(service, 'registro.json', FOLDER_ID)
    send_telegram(f"✅ Análisis terminado: {tiempo_formateado}\n(Se priorizaron rostros y se evitó el área de subtítulos)")

except Exception as e:
    send_telegram(f"❌ Error Script 9: {str(e)}")
    sys.exit(1)