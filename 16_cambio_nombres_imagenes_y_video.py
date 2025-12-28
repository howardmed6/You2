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
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                     json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_drive_service():
    creds = Credentials.from_service_account_info(
        json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS']),
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

try:
    send_telegram("📝 Script 16: Moviendo video y renombrando imágenes...")
    service = get_drive_service()
    
    # 1. Buscar carpeta SnapTube Video
    folder_results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and name='SnapTube Video' and mimeType='application/vnd.google-apps.folder'",
        fields="files(id)"
    ).execute()
    
    if not folder_results.get('files'):
        send_telegram("❌ Script 16: Carpeta 'SnapTube Video' no encontrada")
        sys.exit(1)
    
    snaptube_id = folder_results['files'][0]['id']
    
    # 2. Buscar el video MP4
    video_results = service.files().list(
        q=f"'{snaptube_id}' in parents and mimeType contains 'video/mp4' and trashed=false",
        fields="files(id, name)"
    ).execute()
    
    if not video_results.get('files'):
        send_telegram("❌ Script 16: No se encontró video MP4 en SnapTube Video")
        sys.exit(1)
    
    video_file = video_results['files'][0]
    video_id = video_file['id']
    video_name = video_file['name']
    
    # Extraer nombre sin extensión
    base_name = os.path.splitext(video_name)[0]
    
    # 3. Mover video a carpeta principal
    service.files().update(
        fileId=video_id,
        addParents=FOLDER_ID,
        removeParents=snaptube_id,
        fields='id, parents'
    ).execute()
    
    print(f"✅ Video movido: {video_name}")
    
    # 4. Renombrar las 10 imágenes
    renombradas = 0
    for i in range(1, 11):
        old_name = f"imagen{i}.jpg"
        new_name = f"{base_name}_{i}.jpg"
        
        # Buscar imagen actual
        img_results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and name='{old_name}' and trashed=false",
            fields="files(id)"
        ).execute()
        
        if img_results.get('files'):
            img_id = img_results['files'][0]['id']
            
            # Renombrar
            service.files().update(
                fileId=img_id,
                body={'name': new_name}
            ).execute()
            
            renombradas += 1
            print(f"✅ {old_name} → {new_name}")
    
    send_telegram(f"✅ Script 16: Video movido y {renombradas} imágenes renombradas\n📹 {video_name}")

except Exception as e:
    send_telegram(f"❌ Script 16: {str(e)}")
    sys.exit(1)