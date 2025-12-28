import os
import json
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import glob
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

def update_file_in_drive(service, filename, folder_id):
    """Actualiza un archivo existente en Google Drive"""
    try:
        # Buscar el archivo en Drive
        query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        if not files:
            send_telegram(f"⚠️ {filename} no existe en Drive, se omite")
            return False
        
        # Actualizar el archivo
        file_id = files[0]['id']
        media = MediaFileUpload(filename, mimetype='image/jpeg')
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception as e:
        send_telegram(f"❌ Error actualizando {filename}: {str(e)}")
        return False

try:
    send_telegram("🚀 Script 17: Renombrando imágenes JPG a imagen1.jpg, imagen2.jpg...")
    service = get_drive_service()
    
    # Buscar todos los archivos JPG en el directorio actual
    jpg_files = glob.glob('*.jpg') + glob.glob('*.jpeg')
    
    # Filtrar solo los que NO sean imagen1.jpg, imagen2.jpg, etc. (para evitar conflictos)
    jpg_files = [f for f in jpg_files if not f.startswith('imagen') or not f[6:-4].isdigit()]
    
    if not jpg_files:
        send_telegram("⚠️ No se encontraron archivos JPG para renombrar")
        sys.exit(0)
    
    # Ordenar alfabéticamente para consistencia
    jpg_files.sort()
    
    # Limitar a máximo 10 imágenes
    jpg_files = jpg_files[:10]
    
    send_telegram(f"📸 Se encontraron {len(jpg_files)} imágenes para renombrar")
    
    # Renombrar y subir cada archivo
    for i, original_file in enumerate(jpg_files, 1):
        nuevo_nombre = f'imagen{i}.jpg'
        
        # Renombrar localmente
        if os.path.exists(nuevo_nombre):
            os.remove(nuevo_nombre)  # Eliminar si ya existe
        
        os.rename(original_file, nuevo_nombre)
        
        # Actualizar en Drive
        if update_file_in_drive(service, nuevo_nombre, FOLDER_ID):
            send_telegram(f"✅ {original_file} → {nuevo_nombre} (actualizado en Drive)")
        else:
            send_telegram(f"⚠️ {original_file} → {nuevo_nombre} (local, pero no en Drive)")
    
    send_telegram(f"🎉 Proceso completado: {len(jpg_files)} imágenes renombradas")

except Exception as e:
    send_telegram(f"❌ Error en Script 17: {str(e)}")
    sys.exit(1)