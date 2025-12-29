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
    send_telegram("🚀 Script 9: Generando Top 10 (Modo Robusto/Fallback)...")
    service = get_drive_service()
    
    folder_results = service.files().list(q=f"'{FOLDER_ID}' in parents and name='SnapTube Video'", fields="files(id)").execute()
    if not folder_results['files']:
        raise Exception("No se encontró la carpeta SnapTube Video")
        
    snaptube_id = folder_results['files'][0]['id']
    video_results = service.files().list(q=f"'{snaptube_id}' in parents and mimeType contains 'video/mp4'", fields="files(id, name)").execute()
    
    if not video_results['files']:
        raise Exception("No se encontró ningún video MP4")
        
    video_file = video_results['files'][0]
    
    download_file_from_drive(service, video_file['id'], 'video.mp4')
    with open('video.mp4', 'rb') as f:
        input_content = f.read()

    video_client = vi.VideoIntelligenceServiceClient(credentials=Credentials.from_service_account_info(json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])))
    
    # Solicitamos LABEL_DETECTION y TEXT_DETECTION
    features = [vi.Feature.LABEL_DETECTION, vi.Feature.TEXT_DETECTION]
    operation = video_client.annotate_video(request={"features": features, "input_content": input_content})
    
    send_telegram("⏳ Analizando video (Buscando personas y alternativas)...")
    result = operation.result(timeout=900)
    annotation = result.annotation_results[0]

    # 1. Mapear intervalos con subtítulos (zona inferior > 75%)
    subtitle_intervals = []
    if annotation.text_annotations:
        for text in annotation.text_annotations:
            for segment in text.segments:
                # Verificamos si el texto está en la parte inferior
                y_coords = [v.y for v in segment.frames[0].rotated_bounding_box.vertices]
                if y_coords and max(y_coords) > 0.75:
                    start = segment.segment.start_time_offset.total_seconds()
                    end = segment.segment.end_time_offset.total_seconds()
                    subtitle_intervals.append((start, end))

    # 2. Recolectar TODOS los candidatos y clasificarlos
    candidates = []
    
    # Palabras clave prioritarias
    human_keywords = ["person", "face", "human", "actor", "man", "woman", "girl", "boy"]
    
    if annotation.shot_label_annotations:
        for label in annotation.shot_label_annotations:
            desc = label.entity.description.lower()
            
            # Determinamos si es humano o no
            is_human = any(k in desc for k in human_keywords)
            
            for seg in label.segments:
                mid = (seg.segment.start_time_offset.total_seconds() + seg.segment.end_time_offset.total_seconds()) / 2
                
                # Chequeamos si choca con un subtítulo
                is_subtitle_collision = any(s <= mid <= e for s, e in subtitle_intervals)
                
                # SISTEMA DE PRIORIDADES (SCORING)
                # 1: Humano SIN subtítulo (El mejor)
                # 2: Humano CON subtítulo (Fallback 1)
                # 3: No humano SIN subtítulo (Fallback 2 - paisaje, objeto claro)
                # 4: No humano CON subtítulo (Último recurso)
                
                priority = 4
                if is_human and not is_subtitle_collision:
                    priority = 1
                elif is_human and is_subtitle_collision:
                    priority = 2
                elif not is_human and not is_subtitle_collision:
                    priority = 3
                
                candidates.append({
                    "tiempo_exacto": mid,
                    "confianza": seg.confidence,
                    "etiqueta": desc,
                    "prioridad": priority,
                    "tiene_subtitulo": is_subtitle_collision,
                    "es_humano": is_human
                })

    # 3. Ordenar inteligentemente
    # Ordenamos primero por Prioridad (menor es mejor), luego por Confianza (mayor es mejor)
    candidates = sorted(candidates, key=lambda x: (x['prioridad'], -x['confianza']))

    # 4. Seleccionar Top 10 evitando duplicados de segundos
    top_10 = []
    vistos = set()
    
    for c in candidates:
        seg_redondeado = int(c['tiempo_exacto'])
        
        # Evitamos fotogramas en el mismo segundo exacto
        if seg_redondeado not in vistos:
            mins, secs = divmod(seg_redondeado, 60)
            
            # Añadimos un indicador visual para el reporte
            tipo_icono = "🌟" if c['prioridad'] == 1 else ("⚠️" if c['prioridad'] == 2 else "📷")
            
            c['tiempo_legible'] = f"{mins:02d}:{secs:02d}"
            c['icono_debug'] = tipo_icono
            
            top_10.append(c)
            vistos.add(seg_redondeado)
        
        if len(top_10) == 10: break

    # Fallback de seguridad extrema: si la API no devolvió NADA de etiquetas (raro pero posible)
    if len(top_10) == 0:
        # Simplemente tomamos el punto medio del video si todo falla
        top_10.append({
             "tiempo_exacto": 10.0,
             "tiempo_legible": "00:10",
             "confianza": 0.0,
             "etiqueta": "fallback_manual",
             "prioridad": 5
        })

    registro_final = {
        "video": video_file['name'],
        "total_encontrados": len(top_10),
        "mejores_fotogramas": top_10
    }
    
    with open('registro.json', 'w') as f:
        json.dump(registro_final, f, indent=2)
    
    upload_file_to_folder(service, 'registro.json', FOLDER_ID)
    
    msg_telegram = "✅ Top Miniaturas (Lógica Mejorada):\n"
    for i, f in enumerate(top_10, 1):
        clean_info = "Subtítulo" if f.get('tiene_subtitulo') else "Limpio"
        msg_telegram += f"{i}. {f['tiempo_legible']} {f.get('icono_debug','')} ({f['etiqueta']} - {clean_info})\n"
    
    send_telegram(msg_telegram)

except Exception as e:
    send_telegram(f"❌ Error crítico: {str(e)}")
    sys.exit(1)