import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

folder_id = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
credentials_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')

if credentials_json:
    credentials_info = json.loads(credentials_json)
    credentials = Credentials.from_service_account_info(
        credentials_info, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    
    service = build('drive', 'v3', credentials=credentials)
    
    # Buscar data.json
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='data.json' and trashed=false",
        fields="files(id,name)"
    ).execute()
    
    files = results.get('files', [])
    
    if files:
        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        
        with open('data.json', 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        print("✅ data.json descargado")
    else:
        print("⚠️ data.json no encontrado, creando nuevo")
        with open('data.json', 'w') as f:
            json.dump([], f)
else:
    print("❌ Credenciales no configuradas")