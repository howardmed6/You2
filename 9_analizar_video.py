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
    send_telegram("🚀 Script 9: Generando Top 10 de mejores fotogramas (Sin subtítulos)...")
    service = get_drive_service()
    
    folder_results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='SnapTube Video'", fields="files(id)").execute()
    snaptube_id = folder_results['files'][0]['id']
    video_results = service.files().list(q=f"'{snaptube_id}' in parents and mimeType contains 'video/mp4'", fields="files(id, name)").execute()
    video_file = video_results['files'][0]
    
    download_file_from_drive(service, video_file['id'], 'video.mp4')
    with open('video.mp4', 'rb') as f:
        input_content = f.read()

    video_client = vi.VideoIntelligenceServiceClient(credentials=Credentials.from_service_account_info(json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])))
    
    features = [vi.Feature.LABEL_DETECTION, vi.Feature.TEXT_DETECTION]
    operation = video_client.annotate_video(request={"features": features, "input_content": input_content})
    
    send_telegram("⏳ Buscando las 10 mejores escenas...")
    result = operation.result(timeout=900)
    annotation = result.annotation_results[0]

    # 1. Mapear intervalos con subtítulos (zona inferior)
    subtitle_intervals = []
    if annotation.text_annotations:
        for text in annotation.text_annotations:
            for segment in text.segments:
                y_coords = [v.y for v in segment.frames[0].rotated_bounding_box.vertices]
                if y_coords and max(y_coords) > 0.75:
                    start = segment.segment.start_time_offset.total_seconds()
                    end = segment.segment.end_time_offset.total_seconds()
                    subtitle_intervals.append((start, end))

    # 2. Recolectar candidatos con personas
    candidates = []
    if annotation.shot_label_annotations:
        for label in annotation.shot_label_annotations:
            desc = label.entity.description.lower()
            if any(k in desc for k in ["person", "face", "human", "actor"]):
                for seg in label.segments:
                    mid = (seg.segment.start_time_offset.total_seconds() + seg.segment.end_time_offset.total_seconds()) / 2
                    is_subtitle = any(s <= mid <= e for s, e in subtitle_intervals)
                    
                    if not is_subtitle:
                        candidates.append({
                            "tiempo_exacto": mid,
                            "confianza": seg.confidence,
                            "etiqueta": desc
                        })

    # 3. Ordenar por confianza y tomar los mejores 10
    # Usamos un set para evitar tiempos duplicados muy cercanos
    candidates = sorted(candidates, key=lambda x: x['confianza'], reverse=True)
    top_10 = []
    vistos = set()
    
    for c in candidates:
        seg_redondeado = int(c['tiempo_exacto'])
        if seg_redondeado not in vistos:
            mins, secs = divmod(seg_redondeado, 60)
            c['tiempo_legible'] = f"{mins:02d}:{secs:02d}"
            top_10.append(c)
            vistos.add(seg_redondeado)
        if len(top_10) == 10: break

    registro_final = {
        "video": video_file['name'],
        "total_candidatos": len(top_10),
        "mejores_fotogramas": top_10
    }
    
    with open('registro.json', 'w') as f:
        json.dump(registro_final, f, indent=2)
    
    upload_file_to_folder(service, 'registro.json', FOLDER_ID)
    
    msg_telegram = "✅ Top 10 de miniaturas listo:\n"
    for i, f in enumerate(top_10, 1):
        msg_telegram += f"{i}. {f['tiempo_legible']} (Confianza: {f['confianza']:.2f})\n"
    
    send_telegram(msg_telegram)

except Exception as e:
    send_telegram(f"❌ Error: {str(e)}")
    sys.exit(1)