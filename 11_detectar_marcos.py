import os
import json
import sys
import io
import numpy as np
import cv2
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Configuración
FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
ARCHIVO_JSON = "reporte_marcos_logos.json"
IMAGENES = [f"imagen{i}.jpg" for i in range(1, 11)]

def get_creds():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/cloud-vision']
    return Credentials.from_service_account_info(creds_json).with_scopes(scopes)

def detectar_marcos_opencv(img_bytes):
    """
    Usa OpenCV para detectar el área útil (no negra) de la imagen.
    Retorna coordenadas normalizadas (0 a 1) para mantener el formato.
    """
    try:
        # Convertir bytes a imagen OpenCV
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None: return None

        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Umbral: Todo lo que sea más oscuro que 15 (casi negro) se vuelve 0, lo demás 255
        _, thresh = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
        
        # Encontrar todos los píxeles que NO son negros
        coords = cv2.findNonZero(thresh)
        
        height, width = img.shape[:2]
        
        # Si toda la imagen es negra o no encuentra contenido
        if coords is None:
            return None

        # Obtener el rectángulo que encierra el contenido útil
        x, y, w, h = cv2.boundingRect(coords)
        
        # Calcular coordenadas normalizadas (0.0 a 1.0)
        # x1, y1 (arriba izquierda)
        nx1 = round(x / width, 3)
        ny1 = round(y / height, 3)
        # x2, y2 (abajo derecha)
        nx2 = round((x + w) / width, 3)
        ny2 = round((y + h) / height, 3)

        # Si el contenido ocupa casi toda la imagen (>95%), asumimos que NO hay marcos
        area_util = w * h
        area_total = width * height
        if area_util / area_total > 0.95:
            return None # No hay marcos significativos

        # Devolver formato de 4 vértices (rectángulo del contenido útil)
        return [
            {"x": nx1, "y": ny1}, # Top-Left
            {"x": nx2, "y": ny1}, # Top-Right
            {"x": nx2, "y": ny2}, # Bottom-Right
            {"x": nx1, "y": ny2}  # Bottom-Left
        ]

    except Exception as e:
        print(f"Error OpenCV: {e}")
        return None

def procesar_hibrido():
    print("🚀 Iniciando Detección Híbrida (OpenCV + Vision API)...")
    creds = get_creds()
    drive_service = build('drive', 'v3', credentials=creds)
    vision_client = vision.ImageAnnotatorClient(credentials=creds)
    
    reporte_final = []

    for nombre in IMAGENES:
        try:
            # 1. Buscar y Descargar
            q = f"'{FOLDER_ID}' in parents and name='{nombre}' and trashed=false"
            res = drive_service.files().list(q=q, fields="files(id)").execute()
            
            if not res.get('files'):
                print(f"⚠️ {nombre} no encontrada.")
                continue

            file_id = res['files'][0]['id']
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done: _, done = downloader.next_chunk()
            
            content = fh.getvalue()
            print(f"👁️ Procesando: {nombre}")

            # ---------------------------------------------------------
            # PASO 1: OpenCV (Detectar Marcos GRATIS y EXACTO)
            # ---------------------------------------------------------
            coords_marco = detectar_marcos_opencv(content)
            
            item = {
                "archivo": nombre,
                "tiene_marcos": False,
                "detalles_marcos": [],
                "logos_detectados": []
            }

            if coords_marco:
                item["tiene_marcos"] = True
                item["detalles_marcos"].append({
                    "objeto": "Area_Util_Video", # Nombre técnico
                    "confianza": 1.0, # OpenCV es matemático, la confianza es 100%
                    "coordenadas": coords_marco
                })
            else:
                # Si OpenCV dice que está limpia, ponemos ceros
                item["detalles_marcos"] = [{
                    "objeto": "ninguno",
                    "coordenadas": [{"x": 0, "y": 0}, {"x": 0, "y": 0}, {"x": 0, "y": 0}, {"x": 0, "y": 0}]
                }]

            # ---------------------------------------------------------
            # PASO 2: Vision API (Solo Logos)
            # ---------------------------------------------------------
            image = vision.Image(content=content)
            # Solo pedimos LOGO_DETECTION (Ahorramos la de objetos)
            response = vision_client.annotate_image({
                'image': image,
                'features': [{'type_': vision.Feature.Type.LOGO_DETECTION}]
            })

            for logo in response.logo_annotations:
                item["logos_detectados"].append({
                    "entidad": logo.description,
                    "score": round(logo.score, 2),
                    "vertices_px": [{"x": v.x, "y": v.y} for v in logo.bounding_poly.vertices]
                })

            reporte_final.append(item)
            
            # Limpieza
            fh.close()
            del image

        except Exception as e:
            print(f"❌ Error en {nombre}: {e}")

    # ---------------------------------------------------------
    # PASO 3: Guardar y Actualizar Drive
    # ---------------------------------------------------------
    print("💾 Guardando JSON...")
    with open(ARCHIVO_JSON, 'w') as f:
        json.dump(reporte_final, f, indent=2)

    print("☁️ Actualizando archivo en Drive...")
    res_json = drive_service.files().list(
        q=f"'{FOLDER_ID}' in parents and name='{ARCHIVO_JSON}' and trashed=false",
        fields="files(id)"
    ).execute()

    if res_json.get('files'):
        file_id_json = res_json['files'][0]['id']
        media = MediaFileUpload(ARCHIVO_JSON, mimetype='application/json')
        drive_service.files().update(fileId=file_id_json, media_body=media).execute()
        print("✅ ¡ÉXITO! Archivo actualizado correctamente.")
    else:
        print("❌ Error: No encontré el archivo JSON para actualizar.")

if __name__ == "__main__":
    procesar_hibrido()