import json
import sys
import os
import requests

def elegir_video():
    identificador = sys.argv[1] if len(sys.argv) > 1 else input("ID o URL del video: ").strip()
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Extraer ID si es URL
    if "youtube.com" in identificador or "youtu.be" in identificador:
        if "v=" in identificador:
            video_id = identificador.split("v=")[1].split("&")[0]
        elif "youtu.be/" in identificador:
            video_id = identificador.split("youtu.be/")[1].split("?")[0]
        else:
            print("❌ URL inválida")
            sys.exit(1)
    else:
        video_id = identificador
    
    # Cargar videos subidos
    try:
        with open("subidos.json", 'r', encoding='utf-8') as f:
            subidos = json.load(f)
    except FileNotFoundError:
        subidos = []
    
    urls_subidos = set(subidos)
    
    # Cargar data.json
    with open("data.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Buscar video seleccionado
    elegido = None
    data_filtrada = []
    
    for video in data:
        if video['video_id'] == video_id and video['status'] == 'seleccionado':
            # Verificar si ya fue subido
            if video['url'] in urls_subidos:
                print(f"⚠️ Este video ya fue subido anteriormente")
                print(f"📺 {video['title']}")
                print(f"🔗 {video['url']}")
                sys.exit(1)
            elegido = video
            elegido['status'] = 'elegido'
        else:
            data_filtrada.append(video)
    
    if not elegido:
        print(f"❌ No se encontró video con ID {video_id} en estado 'seleccionado'")
        sys.exit(1)
    
    # Guardar data.json sin el elegido
    with open("data.json", 'w', encoding='utf-8') as f:
        json.dump(data_filtrada, f, indent=2, ensure_ascii=False)
    
    # Guardar descargar.json (sobrescribir)
    with open("descargar.json", 'w', encoding='utf-8') as f:
        json.dump([elegido], f, indent=2, ensure_ascii=False)
    
    # Agregar a subidos.json
    subidos.append(elegido['url'])
    with open("subidos.json", 'w', encoding='utf-8') as f:
        json.dump(subidos, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Video elegido: {elegido['title']}")
    print(f"📦 Movido a descargar.json")
    print(f"📝 URL registrada en subidos.json")
    
    # Notificar en Telegram
    if BOT_TOKEN and CHAT_ID:
        mensaje = (
            f"👤 *Video elegido manualmente*\n\n"
            f"📺 *{elegido['title']}*\n"
            f"📡 Canal: {elegido['channel']}\n"
            f"🆔 ID: `{elegido['video_id']}`\n"
            f"🔗 {elegido['url']}"
        )
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"},
                timeout=10
            )
            print("✅ Notificación enviada a Telegram")
        except:
            pass

if __name__ == "__main__":
    elegir_video()