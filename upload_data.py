import os
import json
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("=== INICIANDO UPLOAD_DATA.PY ===")

folder_id = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
credentials_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')

if not credentials_json:
    print("❌ ERROR: Credenciales no configuradas")
    sys.exit(1)

try:
    # Verificar que data.json existe localmente
    if not os.path.exists('data.json'):
        print("❌ ERROR: data.json no existe localmente")
        sys.exit(1)
    
    size = os.path.getsize('data.json')
    print(f"📄 Archivo local data.json: {size} bytes")
    
    # Crear credenciales
    credentials_info = json.loads(credentials_json)
    credentials = Credentials.from_service_account_info(
        credentials_info, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    print("✅ Credenciales creadas")
    
    service = build('drive', 'v3', credentials=credentials)
    print("✅ Servicio de Drive construido")
    
    # Buscar data.json existente
    print(f"🔍 Buscando data.json en carpeta: {folder_id}")
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='data.json' and trashed=false",
        fields="files(id, name)"
    ).execute()
    
    files = results.get('files', [])
    print(f"Archivos encontrados: {len(files)}")
    
    if not files:
        print("❌ ERROR: data.json no existe en Google Drive")
        print("SOLUCIÓN: Crea manualmente un archivo data.json en la carpeta de Drive primero")
        print("Contenido inicial sugerido: []")
        sys.exit(1)
    
    # SIEMPRE actualizar (nunca crear)
    file_id = files[0]['id']
    print(f"📤 Actualizando archivo: {files[0]['name']} (ID: {file_id})")
    
    media = MediaFileUpload('data.json', mimetype='application/json')
    
    service.files().update(
        fileId=file_id,
        media_body=media
    ).execute()
    
    print("✅ data.json actualizado exitosamente en Google Drive")
    print("=== UPLOAD COMPLETADO ===")

except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)