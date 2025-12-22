import os
import json
import sys
from datetime import datetime

# ESCRIBIR TODO A UN ARCHIVO DE LOG
log_file = open('build_log.txt', 'w')

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}\n"
    log_file.write(line)
    log_file.flush()
    print(line, end='')

log("=== INICIANDO DOWNLOAD_DATA.PY ===")
log(f"Python version: {sys.version}")

# Verificar que la variable existe
credentials_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
log(f"GOOGLE_DRIVE_CREDENTIALS existe: {credentials_json is not None}")

if not credentials_json:
    log("❌ ERROR: Variable GOOGLE_DRIVE_CREDENTIALS no encontrada")
    log("Variables de entorno disponibles:")
    for key in os.environ.keys():
        if 'GOOGLE' in key or 'CREDENTIALS' in key or 'SECRET' in key:
            log(f"  - {key}")
    log_file.close()
    sys.exit(1)

log(f"Longitud de credenciales: {len(credentials_json)} caracteres")

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
    import io
    
    log("✅ Imports exitosos")
    
    folder_id = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
    
    # Parsear credenciales
    credentials_info = json.loads(credentials_json)
    log("✅ JSON parseado correctamente")
    
    # Crear credenciales
    credentials = Credentials.from_service_account_info(
        credentials_info, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    log("✅ Credenciales creadas")
    
    # Construir servicio
    service = build('drive', 'v3', credentials=credentials)
    log("✅ Servicio de Drive construido")
    
    # Buscar archivo
    log(f"🔍 Buscando data.json en carpeta: {folder_id}")
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='data.json' and trashed=false",
        fields="files(id, name)"
    ).execute()
    
    files = results.get('files', [])
    log(f"Archivos encontrados: {len(files)}")
    
    if files:
        file_id = files[0]['id']
        log(f"✅ Archivo encontrado: {files[0]['name']} (ID: {file_id})")
        
        # Descargar
        request = service.files().get_media(fileId=file_id)
        with open('data.json', 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        size = os.path.getsize('data.json')
        log(f"✅ Descargado: {size} bytes")
        
        # Validar JSON
        with open('data.json', 'r') as f:
            data = json.load(f)
        log(f"✅ JSON válido con {len(data)} registros")
    else:
        log("⚠️ Archivo no encontrado, creando vacío")
        with open('data.json', 'w') as f:
            json.dump([], f)
        log("✅ Archivo vacío creado")
    
    log("=== DOWNLOAD COMPLETADO ===")
    
    # SUBIR EL LOG A GOOGLE DRIVE
    log("📤 Subiendo log a Google Drive...")
    log_file.close()
    
    file_metadata = {
        'name': f'build_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
        'parents': [folder_id]
    }
    media = MediaFileUpload('build_log.txt', mimetype='text/plain')
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print("✅ Log subido a Google Drive")

except Exception as e:
    log(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    log(traceback.format_exc())
    log_file.close()
    
    # Intentar subir el log incluso si falló
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from datetime import datetime
        
        credentials_info = json.loads(os.environ.get('GOOGLE_DRIVE_CREDENTIALS'))
        credentials = Credentials.from_service_account_info(
            credentials_info, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        
        file_metadata = {
            'name': f'build_log_ERROR_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
            'parents': ['1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML']
        }
        media = MediaFileUpload('build_log.txt', mimetype='text/plain')
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print("✅ Log de error subido a Google Drive")
    except:
        pass
    
    sys.exit(1)