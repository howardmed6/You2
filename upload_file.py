import os
import json
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"

def upload_file(filename):
    credentials_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
    if not credentials_json:
        print(f"❌ Credenciales no disponibles")
        return
    
    try:
        credentials_info = json.loads(credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_info, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        
        # Buscar si existe
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        
        # Determinar mimetype
        if filename.endswith('.json'):
            mimetype = 'application/json'
        elif filename.endswith(('.jpg', '.jpeg')):
            mimetype = 'image/jpeg'
        elif filename.endswith('.png'):
            mimetype = 'image/png'
        else:
            mimetype = 'application/octet-stream'
        
        media = MediaFileUpload(filename, mimetype=mimetype)
        
        if files:
            # Actualizar
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
            print(f"✅ {filename} actualizado")
        else:
            # Crear
            service.files().create(
                body={'name': filename, 'parents': [FOLDER_ID]},
                media_body=media
            ).execute()
            print(f"✅ {filename} creado")
            
    except Exception as e:
        print(f"❌ Error subiendo {filename}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        upload_file(sys.argv[1])
    else:
        print("Uso: python upload_file.py <nombre_archivo>")