import os
import json
import sys
import io
from google.cloud import vision
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import requests
from PIL import Image as PILImage

FOLDER_ID = "1-NXHDM29JFrNpzVxMFmfFLMMaNgy44ML"
ARCHIVO_JSON = "reporte_marcos_logos.json"
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TARGET_WIDTH = 1588
TARGET_HEIGHT = 937

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                     json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_creds():
    creds_json = json.loads(os.environ['GOOGLE_DRIVE_CREDENTIALS'])
    scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/cloud-vision']
    return Credentials.from_service_account_info(creds_json).with_scopes(scopes)

def decidir_corte_logo(logo, rostros, w, h):
    """Decide qué lado cortar para eliminar el logo"""
    x_vals = [v['x'] for v in logo['vertices_px']]
    y_vals = [v['y'] for v in logo['vertices_px']]
    
    logo_left = min(x_vals)
    logo_right = max(x_vals)
    logo_top = min(y_vals)
    logo_bottom = max(y_vals)
    logo_width = logo_right - logo_left
    logo_height = logo_bottom - logo_top
    
    en_superior = logo_top < h * 0.25
    en_inferior = logo_bottom > h * 0.75
    en_izquierda = logo_left < w * 0.25
    en_derecha = logo_right > w * 0.75
    
    opciones = []
    if en_superior and en_izquierda:
        opciones = ['arriba', 'izquierda']
    elif en_superior and en_derecha:
        opciones = ['arriba', 'derecha']
    elif en_inferior and en_izquierda:
        opciones = ['abajo', 'izquierda']
    elif en_inferior and en_derecha:
        opciones = ['abajo', 'derecha']
    elif en_superior:
        opciones = ['arriba']
    elif en_inferior:
        opciones = ['abajo']
    elif en_izquierda:
        opciones = ['izquierda']
    elif en_derecha:
        opciones = ['derecha']
    else:
        return None
    
    mejor_opcion = None
    menor_impacto = float('inf')
    
    for opcion in opciones:
        rostros_afectados = 0
        perdida_pixeles = 0
        
        if opcion == 'arriba':
            perdida_pixeles = logo_height * w
            for rostro in rostros:
                if rostro['top'] < logo_bottom:
                    rostros_afectados += 1
        elif opcion == 'abajo':
            perdida_pixeles = logo_height * w
            for rostro in rostros:
                if rostro['bottom'] > logo_top:
                    rostros_afectados += 1
        elif opcion == 'izquierda':
            perdida_pixeles = logo_width * h
            for rostro in rostros:
                if rostro['left'] < logo_right:
                    rostros_afectados += 1
        elif opcion == 'derecha':
            perdida_pixeles = logo_width * h
            for rostro in rostros:
                if rostro['right'] > logo_left:
                    rostros_afectados += 1
        
        impacto = rostros_afectados * 1000000 + perdida_pixeles
        
        if impacto < menor_impacto:
            menor_impacto = impacto
            mejor_opcion = opcion
    
    return mejor_opcion

def calcular_recorte_final(rostros, w, h):
    """Calcula coordenadas de recorte final 1588x937 evitando rostros"""
    target_ratio = TARGET_WIDTH / TARGET_HEIGHT
    current_ratio = w / h
    
    if current_ratio > target_ratio:
        # Imagen ancha - recortar lados
        new_width = int(h * target_ratio)
        
        if not rostros:
            left = (w - new_width) // 2
            return {"x": left, "y": 0, "width": new_width, "height": h}
        
        mejor_left = (w - new_width) // 2
        menor_rostros_perdidos = len(rostros) + 1
        
        paso = max(1, (w - new_width) // 20)
        for left in range(0, w - new_width + 1, paso):
            right = left + new_width
            rostros_perdidos = 0
            
            for rostro in rostros:
                centro_rostro = (rostro['left'] + rostro['right']) / 2
                if centro_rostro < left or centro_rostro > right:
                    rostros_perdidos += 1
                elif rostro['left'] < left or rostro['right'] > right:
                    rostros_perdidos += 0.3
            
            if rostros_perdidos < menor_rostros_perdidos:
                menor_rostros_perdidos = rostros_perdidos
                mejor_left = left
        
        return {"x": int(mejor_left), "y": 0, "width": new_width, "height": h}
    
    else:
        # Imagen alta - recortar arriba/abajo
        new_height = int(w / target_ratio)
        
        if not rostros:
            top = (h - new_height) // 2
            return {"x": 0, "y": top, "width": w, "height": new_height}
        
        mejor_top = (h - new_height) // 2
        menor_rostros_perdidos = len(rostros) + 1
        
        paso = max(1, (h - new_height) // 20)
        for top in range(0, h - new_height + 1, paso):
            bottom = top + new_height
            rostros_perdidos = 0
            
            for rostro in rostros:
                centro_rostro = (rostro['top'] + rostro['bottom']) / 2
                if centro_rostro < top or centro_rostro > bottom:
                    rostros_perdidos += 1
                elif rostro['top'] < top or rostro['bottom'] > bottom:
                    rostros_perdidos += 0.3
            
            if rostros_perdidos < menor_rostros_perdidos:
                menor_rostros_perdidos = rostros_perdidos
                mejor_top = top
        
        return {"x": 0, "y": int(mejor_top), "width": w, "height": new_height}

try:
    send_telegram("🔍 Script 13: Detectando logos + rostros + recorte final...")
    creds = get_creds()
    drive_service = build('drive', 'v3', credentials=creds)
    vision_client = vision.ImageAnnotatorClient(credentials=creds)
    
    q = f"'{FOLDER_ID}' in parents and name='{ARCHIVO_JSON}' and trashed=false"
    res_json = drive_service.files().list(q=q, fields="files(id)").execute()
    
    reporte_final = []
    if res_json.get('files'):
        file_id_json = res_json['files'][0]['id']
        request = drive_service.files().get_media(fileId=file_id_json)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        reporte_final = json.loads(fh.getvalue().decode('utf-8'))
        fh.close()
    
    detectados = 0
    decisiones = 0

    for item in reporte_final:
        nombre = item['archivo']
        q = f"'{FOLDER_ID}' in parents and name='{nombre}' and trashed=false"
        res = drive_service.files().list(q=q, fields="files(id)").execute()
        
        if not res.get('files'):
            print(f"⚠️ {nombre} no encontrada")
            continue

        file_id = res['files'][0]['id']
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        
        content = fh.getvalue()
        image = vision.Image(content=content)
        
        response = vision_client.annotate_image({
            'image': image,
            'features': [
                {'type_': vision.Feature.Type.LOGO_DETECTION},
                {'type_': vision.Feature.Type.FACE_DETECTION}
            ]
        })

        logos = []
        for logo in response.logo_annotations:
            logos.append({
                "entidad": logo.description,
                "score": round(logo.score, 2),
                "vertices_px": [{"x": v.x, "y": v.y} for v in logo.bounding_poly.vertices]
            })
            detectados += 1

        item['logos_detectados'] = logos
        
        rostros = []
        for face in response.face_annotations:
            vertices = face.bounding_poly.vertices
            rostros.append({
                'left': min(v.x for v in vertices),
                'right': max(v.x for v in vertices),
                'top': min(v.y for v in vertices),
                'bottom': max(v.y for v in vertices)
            })
        
        img = PILImage.open(io.BytesIO(content))
        w, h = img.size
        
        # Decidir corte de logo
        if logos:
            lado = decidir_corte_logo(logos[0], rostros, w, h)
            item['lado_a_cortar'] = lado
            if lado:
                decisiones += 1
        else:
            item['lado_a_cortar'] = None
        
        # Calcular recorte final inteligente
        recorte = calcular_recorte_final(rostros, w, h)
        item['recorte_final'] = recorte
        
        fh.close()
        del image

    with open(ARCHIVO_JSON, 'w') as f:
        json.dump(reporte_final, f, indent=2)

    if res_json.get('files'):
        media = MediaFileUpload(ARCHIVO_JSON, mimetype='application/json')
        drive_service.files().update(fileId=file_id_json, media_body=media).execute()
        send_telegram(f"✅ Script 13: {detectados} logos, {decisiones} decisiones, 10 recortes calculados")
    else:
        send_telegram("❌ Script 13: Error al actualizar JSON")
        sys.exit(1)

except Exception as e:
    send_telegram(f"❌ Script 13: {str(e)}")
    sys.exit(1)