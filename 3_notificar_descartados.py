import json
import requests

def notificar_descartados():
    # BOT TOKEN - El que te dio BotFather
    BOT_TOKEN = "8599691958:AAHrOjGVJrvOgbU30rLY23HPmrrNNKYHDUs"
    
    # TU CHAT ID - Escribe a @userinfobot en Telegram para obtenerlo
    CHAT_ID = "8599691958"  # REEMPLAZAR (ej: "123456789")
    
    # Cargar videos
    with open("data.json", 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    descartados = [v for v in videos if v['status'] == 'descartado']
    
    if not descartados:
        print("No hay videos descartados")
        return
    
    # Construir mensaje
    mensaje = f"🚫 *Videos descartados ({len(descartados)})*\n\n"
    for v in descartados:
        mensaje += f"ID: `{v['video_id']}`\n📺 {v['title']}\n🔗 {v['url']}\n\n"
    
    # Enviar a Telegram (dividir si es muy largo)
    max_len = 4000
    partes = [mensaje[i:i+max_len] for i in range(0, len(mensaje), max_len)]
    
    for parte in partes:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": parte, "parse_mode": "Markdown"}
        )
    
    print(f"✓ Notificados {len(descartados)} videos descartados")

if __name__ == "__main__":
    notificar_descartados()