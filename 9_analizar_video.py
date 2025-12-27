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
        except: pass

def get_drive_service():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json, scopes=['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=creds)

def upload_file_to_folder(service, filename, folder_id):
    media = MediaFileUpload(filename, mimetype='application/json')
    service.files().create(body={'name': filename, 'parents': [folder_id]}, media_body=media).execute()

try:
    send_telegram("🚀 Script 9: Algoritmo con Escaneo Geográfico de Subtítulos...")
    service = get_drive_service()
    
    # --- Localización de Video ---
    folder_results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='SnapTube Video'", fields="files(id)").execute()
    snaptube_id = folder_results['files'][0]['id']
    video_results = service.files().list(q=f"'{snaptube_id}' in parents and mimeType contains 'video/mp4'", fields="files(id, name)").execute()
    video_file = video_results['files'][0]
    
    download_file_from_drive(service, video_file['id'], 'video.mp4')
    with open('video.mp4', 'rb') as f:
        input_content = f.read()

    video_client = vi.VideoIntelligenceServiceClient(credentials=Credentials.from_service_account_info(json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])))
    
    # Pedimos etiquetas y texto con coordenadas (Bounding Boxes)
    features = [vi.Feature.LABEL_DETECTION, vi.Feature.TEXT_DETECTION]
    operation = video_client.annotate_video(request={"features": features, "input_content": input_content})
    
    send_telegram("⏳ Analizando posición de subtítulos vs logo...")
    result = operation.result(timeout=900)
    annotation = result.annotation_results[0]

    # 1. Mapear zonas con subtítulos (Parte inferior central)
    bad_intervals = []
    if annotation.text_annotations:
        for text in annotation.text_annotations:
            for segment in text.segments:
                # Miramos la posición del texto en el primer cuadro detectado
                conf = segment.confidence
                box = segment.frames[0].rotated_bounding_box.vertices
                # Y-coordinate de la base del texto (0 es arriba, 1 es abajo)
                y_pos = max(v.y for v in box)
                
                # SI EL TEXTO ESTÁ EN EL 30% INFERIOR, es un subtítulo
                if y_pos > 0.70:
                    start = segment.segment.start_time_offset.total_seconds()
                    end = segment.segment.end_time_offset.total_seconds()
                    bad_intervals.append((start, end))

    # 2. Buscar personas fuera de esas zonas
    best_moment = None
    max_conf = -1.0
    
    for label in annotation.shot_label_annotations:
        desc = label.entity.description.lower()
        if any(k in desc for k in ["person", "face", "human"]):
            for seg in label.segments:
                mid = (seg.segment.start_time_offset.total_seconds() + seg.segment.end_time_offset.total_seconds()) / 2
                
                # ¿Está este momento en un rango de subtítulos?
                is_subtitle = any(s <= mid <= e for s, e in bad_intervals)
                
                if not is_subtitle and seg.confidence > max_conf:
                    max_conf = seg.confidence
                    best_moment = mid

    if not best_moment:
        best_moment = 30.0 # Fallback

    best_seconds = int(best_moment)
    mins, secs = divmod(best_seconds, 60)
    tiempo_formateado = f"{mins:02d}:{secs:02d}"

    registro = {"video": video_file['name'], "miniatura_seg": best_moment, "tiempo": tiempo_formateado}
    with open('registro.json', 'w') as f: json.dump(registro, f)
    
    upload_file_to_folder(service, 'registro.json', FOLDER_ID)
    send_telegram(f"✅ Miniatura inteligente: {tiempo_formateado}\n(Se ignoró el texto en la parte inferior)")

except Exception as e:
    send_telegram(f"❌ Error: {str(e)}")