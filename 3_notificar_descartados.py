import json
import requests
import os

def notificar_descartados():
    # Obtener configuración desde variables de entorno
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8599691958:AAHrOjGVJrvOgbU30rLY23HPmrrNNKYHDUs")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6166225652")  # Tu chat ID real
    
    print(f"Usando BOT_TOKEN: {BOT_TOKEN[:20]}...")
    print(f"Usando CHAT_ID: {CHAT_ID}")
    
    # Cargar videos
    try:
        with open("data.json", 'r', encoding='utf-8') as f:
            videos = json.load(f)
    except FileNotFoundError:
        print("❌ Error: data.json no encontrado")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error al leer data.json: {e}")
        return
    
    descartados = [v for v in videos if v.get('status') == 'descartado']
    
    if not descartados:
        print("✓ No hay videos descartados")
        return
    
    # Construir mensaje
    mensaje = f"🚫 *Videos descartados ({len(descartados)})*\n\n"
    for v in descartados:
        video_id = v.get('video_id', 'N/A')
        title = v.get('title', 'Sin título')[:100]  # Limitar título
        url = v.get('url', 'N/A')
        mensaje += f"ID: `{video_id}`\n📺 {title}\n🔗 {url}\n\n"
    
    # Enviar a Telegram (dividir si es muy largo)
    max_len = 4000
    partes = [mensaje[i:i+max_len] for i in range(0, len(mensaje), max_len)]
    
    for idx, parte in enumerate(partes):
        print(f"Enviando parte {idx + 1}/{len(partes)} a Telegram...")
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": parte, "parse_mode": "Markdown"},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✓ Parte {idx + 1} enviada correctamente")
            else:
                print(f"❌ Error al enviar parte {idx + 1}: {response.status_code}")
                print(f"Respuesta: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión al enviar parte {idx + 1}: {e}")
    
    print(f"✓ Notificados {len(descartados)} videos descartados")

if __name__ == "__main__":
    notificar_descartados()