import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

folder_id = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
credentials_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')

if credentials_json:
    credentials_info = json.loads(credentials_json)
    credentials = Credentials.from_service_account_info(
        credentials_info, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    
    service = build('drive', 'v3', credentials=credentials)
    
    # Buscar si existe data.json
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='data.json' and trashed=false",
        fields="files(id)"
    ).execute()
    
    files = results.get('files', [])
    
    media = MediaFileUpload('data.json', mimetype='application/json')
    
    if files:
        # Actualizar archivo existente
        file_id = files[0]['id']
        service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        print("✅ data.json actualizado en Google Drive")
    else:
        # Crear nuevo archivo
        file_metadata = {
            'name': 'data.json',
            'parents': [folder_id]
        }
        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print("✅ data.json creado en Google Drive")
else:
    print("❌ Credenciales no configuradas")