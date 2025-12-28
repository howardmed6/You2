import os
import json
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
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

try:
    send_telegram("🚀 Script 17: Renombrando 10 imágenes JPG...")
    service = get_drive_service()
    
    # Buscar todas las imágenes JPG en Drive (excluyendo las que ya son imagen1.jpg, etc)
    query = f"'{FOLDER_ID}' in parents and (mimeType='image/jpeg' or name contains '.jpg') and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)", orderBy="name").execute()
    files = results.get('files', [])
    
    # Filtrar las que NO son imagen1.jpg, imagen2.jpg, etc.
    files = [f for f in files if not (f['name'].startswith('imagen') and f['name'][6:-4].isdigit())]
    
    if not files:
        send_telegram("⚠️ No se encontraron imágenes JPG para renombrar")
        sys.exit(0)
    
    # Limitar a 10 imágenes
    files = files[:10]
    
    send_telegram(f"📸 Renombrando {len(files)} imágenes...")
    
    for i, file_info in enumerate(files, 1):
        file_id = file_info['id']
        nombre_original = file_info['name']
        nuevo_nombre = f'imagen{i}.jpg'
        
        # Renombrar directamente en Drive
        service.files().update(
            fileId=file_id,
            body={'name': nuevo_nombre}
        ).execute()
        
        print(f"✅ {nombre_original} → {nuevo_nombre}")
    
    send_telegram(f"✅ Script 17: {len(files)} imágenes renombradas correctamente")

except Exception as e:
    send_telegram(f"❌ Script 17: {str(e)}")
    sys.exit(1)