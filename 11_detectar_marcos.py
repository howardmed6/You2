import os
import json
import sys
import io
import numpy as np
import cv2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import requests

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
ARCHIVO_JSON = "reporte_marcos.json"
IMAGENES = [f"imagen{i}.jpg" for i in range(1, 11)]
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                     json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_drive_service():
    creds = Credentials.from_service_account_info(
        json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS']),
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def detectar_marcos_opencv(img_bytes):
    try:
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: return None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
        coords = cv2.findNonZero(thresh)
        
        height, width = img.shape[:2]
        if coords is None: return None

        x, y, w, h = cv2.boundingRect(coords)
        
        nx1 = round(x / width, 3)
        ny1 = round(y / height, 3)
        nx2 = round((x + w) / width, 3)
        ny2 = round((y + h) / height, 3)

        area_util = w * h
        area_total = width * height
        if area_util / area_total > 0.95:
            return None

        return [
            {"x": nx1, "y": ny1},
            {"x": nx2, "y": ny1},
            {"x": nx2, "y": ny2},
            {"x": nx1, "y": ny2}
        ]
    except Exception as e:
        print(f"Error OpenCV: {e}")
        return None

try:
    send_telegram("🔍 Script 11: Detectando marcos con OpenCV...")
    service = get_drive_service()
    reporte_final = []
    detectados = 0

    for nombre in IMAGENES:
        q = f"'{FOLDER_ID}' in parents and name='{nombre}' and trashed=false"
        res = service.files().list(q=q, fields="files(id)").execute()
        
        if not res.get('files'):
            print(f"⚠️ {nombre} no encontrada")
            continue

        file_id = res['files'][0]['id']
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        
        content = fh.getvalue()
        coords_marco = detectar_marcos_opencv(content)
        
        item = {
            "archivo": nombre,
            "tiene_marcos": False,
            "detalles_marcos": []
        }

        if coords_marco:
            item["tiene_marcos"] = True
            item["detalles_marcos"].append({
                "objeto": "Area_Util_Video",
                "confianza": 1.0,
                "coordenadas": coords_marco
            })
            detectados += 1
        else:
            item["detalles_marcos"] = [{
                "objeto": "ninguno",
                "coordenadas": [{"x": 0, "y": 0}, {"x": 0, "y": 0}, {"x": 0, "y": 0}, {"x": 0, "y": 0}]
            }]

        reporte_final.append(item)
        fh.close()

    with open(ARCHIVO_JSON, 'w') as f:
        json.dump(reporte_final, f, indent=2)

    res_json = service.files().list(
        q=f"'{FOLDER_ID}' in parents and name='{ARCHIVO_JSON}' and trashed=false",
        fields="files(id)"
    ).execute()

    if res_json.get('files'):
        file_id_json = res_json['files'][0]['id']
        media = MediaFileUpload(ARCHIVO_JSON, mimetype='application/json')
        service.files().update(fileId=file_id_json, media_body=media).execute()
        send_telegram(f"✅ Script 11: {detectados}/10 imágenes con marcos detectados")
    else:
        send_telegram("❌ Script 11: Error al actualizar JSON")
        sys.exit(1)

except Exception as e:
    send_telegram(f"❌ Script 11: {str(e)}")
    sys.exit(1)