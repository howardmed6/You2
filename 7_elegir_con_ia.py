import json
import requests
import os
import sys

def elegir_con_ia():
    API_KEY = os.environ.get("OPENAI_API_KEY")
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    MODEL = "gpt-4o-mini"
    
    if not API_KEY:
        print("❌ Error: OPENAI_API_KEY no configurada")
        sys.exit(1)
    
    print("🤖 Iniciando selección automática con IA...")
    
    # Cargar videos subidos
    try:
        with open("subidos.json", 'r', encoding='utf-8') as f:
            subidos = json.load(f)
        print(f"📋 Cargados {len(subidos)} videos ya subidos")
    except FileNotFoundError:
        subidos = []
        print("📋 No hay videos subidos previamente (primera ejecución)")
    
    urls_subidos = set(subidos)
    
    # Cargar videos
    with open("data.json", 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    print(f"📊 Total de videos en data.json: {len(videos)}")
    
    # Filtrar seleccionados que NO han sido subidos
    seleccionados = [v for v in videos if v.get('status') == 'seleccionado' and v['url'] not in urls_subidos]
    
    print(f"✅ Videos con status 'seleccionado': {len(seleccionados)}")
    print(f"🔍 Videos disponibles (no subidos): {len(seleccionados)}")
    
    if not seleccionados:
        msg = "❌ No hay videos seleccionados disponibles\n\nTodos los videos ya fueron subidos o no hay videos con status 'seleccionado'"
        print(msg)
        if BOT_TOKEN and CHAT_ID:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": msg},
                timeout=10
            )
        sys.exit(1)
    
    print(f"\n🧠 Analizando {len(seleccionados)} videos con IA...")
    
    # Preparar prompt
    videos_info = "\n".join([
        f"{i+1}. ID: {v['video_id']}\n   Título: {v['title']}\n   Canal: {v['channel']}"
        for i, v in enumerate(seleccionados)
    ])
    
    prompt = (
        "Analiza estos videos de YouTube y elige el que tenga MAYOR potencial viral o valor.\n"
        "Responde ÚNICAMENTE con el número del video elegido (sin texto adicional).\n\n"
        f"{videos_info}\n\n"
        "Respuesta (solo el número):"
    )
    
    # Llamar a OpenAI
    try:
        print("⏳ Consultando a OpenAI...")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 10
            },
            timeout=30
        )
        
        if response.status_code != 200:
            error_msg = f"❌ Error OpenAI (código {response.status_code}): {response.text}"
            print(error_msg)
            if BOT_TOKEN and CHAT_ID:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": CHAT_ID, "text": error_msg},
                    timeout=10
                )
            sys.exit(1)
        
        data = response.json()
        respuesta = data['choices'][0]['message']['content'].strip()
        print(f"🤖 IA respondió: {respuesta}")
        
        indice = int(respuesta) - 1
        
        if indice < 0 or indice >= len(seleccionados):
            error_msg = f"❌ IA devolvió índice inválido: {respuesta}"
            print(error_msg)
            if BOT_TOKEN and CHAT_ID:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": CHAT_ID, "text": error_msg},
                    timeout=10
                )
            sys.exit(1)
        
        # Elegir video
        elegido = seleccionados[indice]
        elegido['status'] = 'elegido'
        
        print(f"\n✅ Video elegido: {elegido['title']}")
        print(f"📡 Canal: {elegido['channel']}")
        print(f"🆔 ID: {elegido['video_id']}")
        
        # Actualizar data.json (eliminar elegido)
        videos_filtrados = [v for v in videos if v['video_id'] != elegido['video_id']]
        with open("data.json", 'w', encoding='utf-8') as f:
            json.dump(videos_filtrados, f, indent=2, ensure_ascii=False)
        
        print(f"📝 Removido de data.json")
        
        # Guardar en descargar.json
        with open("descargar.json", 'w', encoding='utf-8') as f:
            json.dump([elegido], f, indent=2, ensure_ascii=False)
        
        print(f"📦 Guardado en descargar.json")
        
        # Agregar a subidos.json
        subidos.append(elegido['url'])
        with open("subidos.json", 'w', encoding='utf-8') as f:
            json.dump(subidos, f, indent=2, ensure_ascii=False)
        
        print(f"🔒 URL registrada en subidos.json")
        
        # Notificar en Telegram
        if BOT_TOKEN and CHAT_ID:
            mensaje = (
                f"🤖 *Video elegido por IA*\n\n"
                f"📺 *{elegido['title']}*\n"
                f"📡 Canal: {elegido['channel']}\n"
                f"🆔 ID: `{elegido['video_id']}`\n"
                f"🔗 {elegido['url']}\n\n"
                f"✅ Guardado en descargar.json\n"
                f"🔒 Registrado en subidos.json"
            )
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"},
                timeout=10
            )
            print("📱 Notificación enviada a Telegram")
        
        print("\n🎉 Proceso completado exitosamente")
    
    except Exception as e:
        error_msg = f"❌ Error durante el proceso: {str(e)}"
        print(error_msg)
        if BOT_TOKEN and CHAT_ID:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": error_msg},
                timeout=10
            )
        sys.exit(1)

if __name__ == "__main__":
    elegir_con_ia()