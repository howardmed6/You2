import os
import json
import sys

print("=== INICIANDO DOWNLOAD_DATA.PY ===")
print(f"Python version: {sys.version}")

# Verificar que la variable existe
credentials_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
print(f"GOOGLE_DRIVE_CREDENTIALS existe: {credentials_json is not None}")

if not credentials_json:
    print("❌ ERROR: Variable GOOGLE_DRIVE_CREDENTIALS no encontrada")
    print("Variables de entorno disponibles:")
    for key in os.environ.keys():
        if 'GOOGLE' in key or 'CREDENTIALS' in key:
            print(f"  - {key}")
    sys.exit(1)

print(f"Longitud de credenciales: {len(credentials_json)} caracteres")

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io
    
    print("✅ Imports exitosos")
    
    folder_id = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
    
    # Parsear credenciales
    credentials_info = json.loads(credentials_json)
    print("✅ JSON parseado correctamente")
    
    # Crear credenciales
    credentials = Credentials.from_service_account_info(
        credentials_info, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    print("✅ Credenciales creadas")
    
    # Construir servicio
    service = build('drive', 'v3', credentials=credentials)
    print("✅ Servicio de Drive construido")
    
    # Buscar archivo
    print(f"🔍 Buscando data.json en carpeta: {folder_id}")
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='data.json' and trashed=false",
        fields="files(id, name)"
    ).execute()
    
    files = results.get('files', [])
    print(f"Archivos encontrados: {len(files)}")
    
    if files:
        file_id = files[0]['id']
        print(f"✅ Archivo encontrado: {files[0]['name']} (ID: {file_id})")
        
        # Descargar
        request = service.files().get_media(fileId=file_id)
        with open('data.json', 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        size = os.path.getsize('data.json')
        print(f"✅ Descargado: {size} bytes")
        
        # Validar JSON
        with open('data.json', 'r') as f:
            data = json.load(f)
        print(f"✅ JSON válido con {len(data)} registros")
    else:
        print("⚠️ Archivo no encontrado, creando vacío")
        with open('data.json', 'w') as f:
            json.dump([], f)
        print("✅ Archivo vacío creado")
    
    print("=== DOWNLOAD COMPLETADO ===")

except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)