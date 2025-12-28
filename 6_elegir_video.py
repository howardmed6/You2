import json
import sys
import os
import requests

def elegir_video():
    identificador = sys.argv[1] if len(sys.argv) > 1 else input("ID o URL del video: ").strip()
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    
    print(f"🎯 Iniciando selección manual del video: {identificador}")
    
    # Extraer ID si es URL
    if "youtube.com" in identificador or "youtu.be" in identificador:
        if "v=" in identificador:
            video_id = identificador.split("v=")[1].split("&")[0]
        elif "youtu.be/" in identificador:
            video_id = identificador.split("youtu.be/")[1].split("?")[0]
        else:
            error_msg = "❌ URL inválida. Formato esperado: https://youtube.com/watch?v=ID o https://youtu.be/ID"
            print(error_msg)
            if BOT_TOKEN and CHAT_ID:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": CHAT_ID, "text": error_msg},
                    timeout=10
                )
            sys.exit(1)
        print(f"📝 ID extraído de URL: {video_id}")
    else:
        video_id = identificador
        print(f"📝 Usando ID directo: {video_id}")
    
    # Cargar videos subidos
    try:
        with open("subidos.json", 'r', encoding='utf-8') as f:
            subidos = json.load(f)
        print(f"📋 Cargados {len(subidos)} videos ya subidos")
    except FileNotFoundError:
        subidos = []
        print("📋 No hay videos subidos previamente (primera ejecución)")
    
    urls_subidos = set(subidos)
    
    # Cargar data.json
    with open("data.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Total de videos en data.json: {len(data)}")
    
    # Buscar video seleccionado
    elegido = None
    data_filtrada = []
    
    for video in data:
        if video['video_id'] == video_id and video['status'] == 'seleccionado':
            # Verificar si ya fue subido
            if video['url'] in urls_subidos:
                error_msg = (
                    f"⚠️ *Video ya subido anteriormente*\n\n"
                    f"📺 {video['title']}\n"
                    f"📡 Canal: {video['channel']}\n"
                    f"🔗 {video['url']}\n\n"
                    f"Este video está registrado en subidos.json"
                )
                print(f"\n{error_msg}")
                if BOT_TOKEN and CHAT_ID:
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={"chat_id": CHAT_ID, "text": error_msg, "parse_mode": "Markdown"},
                        timeout=10
                    )
                sys.exit(1)
            elegido = video
            elegido['status'] = 'elegido'
            print(f"✅ Video encontrado: {video['title']}")
        else:
            data_filtrada.append(video)
    
    if not elegido:
        error_msg = (
            f"❌ *Video no encontrado*\n\n"
            f"🆔 ID buscado: `{video_id}`\n\n"
            f"Posibles razones:\n"
            f"• No existe en data.json\n"
            f"• Su status no es 'seleccionado'\n"
            f"• Ya fue procesado anteriormente\n\n"
            f"💡 Verifica que el video tenga status='seleccionado' en data.json"
        )
        print(f"\n{error_msg}")
        if BOT_TOKEN and CHAT_ID:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": error_msg, "parse_mode": "Markdown"},
                timeout=10
            )
        sys.exit(1)
    
    # Guardar data.json sin el elegido
    with open("data.json", 'w', encoding='utf-8') as f:
        json.dump(data_filtrada, f, indent=2, ensure_ascii=False)
    
    print(f"📝 Removido de data.json")
    
    # Guardar descargar.json (sobrescribir)
    with open("descargar.json", 'w', encoding='utf-8') as f:
        json.dump([elegido], f, indent=2, ensure_ascii=False)
    
    print(f"📦 Guardado en descargar.json")
    
    # Agregar a subidos.json
    subidos.append(elegido['url'])
    with open("subidos.json", 'w', encoding='utf-8') as f:
        json.dump(subidos, f, indent=2, ensure_ascii=False)
    
    print(f"🔒 URL registrada en subidos.json")
    
    print(f"\n✅ Video elegido exitosamente:")
    print(f"   📺 {elegido['title']}")
    print(f"   📡 {elegido['channel']}")
    print(f"   🆔 {elegido['video_id']}")
    
    # Notificar en Telegram
    if BOT_TOKEN and CHAT_ID:
        mensaje = (
            f"👤 *Video elegido manualmente*\n\n"
            f"📺 *{elegido['title']}*\n"
            f"📡 Canal: {elegido['channel']}\n"
            f"🆔 ID: `{elegido['video_id']}`\n"
            f"🔗 {elegido['url']}\n\n"
            f"✅ Guardado en descargar.json\n"
            f"🔒 Registrado en subidos.json"
        )
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"},
                timeout=10
            )
            print("📱 Notificación enviada a Telegram")
        except Exception as e:
            print(f"⚠️ No se pudo enviar notificación a Telegram: {e}")
    
    print("\n🎉 Proceso completado exitosamente")

if __name__ == "__main__":
    elegir_video()