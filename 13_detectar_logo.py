import os
import json
import sys
import io
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import requests

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
ARCHIVO_JSON = "reporte_marcos_logos.json"
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                     json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_creds():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/cloud-vision']
    return Credentials.from_service_account_info(creds_json).with_scopes(scopes)

try:
    send_telegram("🔍 Script 13: Detectando logos con Vision API...")
    creds = get_creds()
    drive_service = build('drive', 'v3', credentials=creds)
    vision_client = vision.ImageAnnotatorClient(credentials=creds)
    
    # Descargar JSON existente con info de marcos
    q = f"'{FOLDER_ID}' in parents and name='{ARCHIVO_JSON}' and trashed=false"
    res_json = drive_service.files().list(q=q, fields="files(id)").execute()
    
    reporte_final = []
    if res_json.get('files'):
        file_id_json = res_json['files'][0]['id']
        request = drive_service.files().get_media(fileId=file_id_json)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        reporte_final = json.loads(fh.getvalue().decode('utf-8'))
        fh.close()
    
    detectados = 0

    for item in reporte_final:
        nombre = item['archivo']
        q = f"'{FOLDER_ID}' in parents and name='{nombre}' and trashed=false"
        res = drive_service.files().list(q=q, fields="files(id)").execute()
        
        if not res.get('files'):
            print(f"⚠️ {nombre} no encontrada")
            continue

        file_id = res['files'][0]['id']
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        
        content = fh.getvalue()
        image = vision.Image(content=content)
        response = vision_client.annotate_image({
            'image': image,
            'features': [{'type_': vision.Feature.Type.LOGO_DETECTION}]
        })

        logos = []
        for logo in response.logo_annotations:
            logos.append({
                "entidad": logo.description,
                "score": round(logo.score, 2),
                "vertices_px": [{"x": v.x, "y": v.y} for v in logo.bounding_poly.vertices]
            })
            detectados += 1

        item['logos_detectados'] = logos
        fh.close()
        del image

    with open(ARCHIVO_JSON, 'w') as f:
        json.dump(reporte_final, f, indent=2)

    if res_json.get('files'):
        media = MediaFileUpload(ARCHIVO_JSON, mimetype='application/json')
        drive_service.files().update(fileId=file_id_json, media_body=media).execute()
        send_telegram(f"✅ Script 13: {detectados} logos detectados en 10 imágenes")
    else:
        send_telegram("❌ Script 13: Error al actualizar JSON")
        sys.exit(1)

except Exception as e:
    send_telegram(f"❌ Script 13: {str(e)}")
    sys.exit(1)