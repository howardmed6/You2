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
    
    # Cargar videos subidos
    try:
        with open("subidos.json", 'r', encoding='utf-8') as f:
            subidos = json.load(f)
    except FileNotFoundError:
        subidos = []
    
    urls_subidos = set(subidos)
    
    # Cargar videos
    with open("data.json", 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    # Filtrar seleccionados que NO han sido subidos
    seleccionados = [v for v in videos if v.get('status') == 'seleccionado' and v['url'] not in urls_subidos]
    
    if not seleccionados:
        print("❌ No hay videos seleccionados disponibles (todos ya fueron subidos)")
        sys.exit(1)
    
    print(f"Analizando {len(seleccionados)} videos seleccionados con IA...")
    
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
            print(f"❌ Error OpenAI: {response.text}")
            sys.exit(1)
        
        data = response.json()
        respuesta = data['choices'][0]['message']['content'].strip()
        indice = int(respuesta) - 1
        
        if indice < 0 or indice >= len(seleccionados):
            print(f"❌ IA devolvió índice inválido: {respuesta}")
            sys.exit(1)
        
        # Elegir video
        elegido = seleccionados[indice]
        elegido['status'] = 'elegido'
        
        # Actualizar data.json (eliminar elegido)
        videos_filtrados = [v for v in videos if v['video_id'] != elegido['video_id']]
        with open("data.json", 'w', encoding='utf-8') as f:
            json.dump(videos_filtrados, f, indent=2, ensure_ascii=False)
        
        # Guardar en descargar.json
        with open("descargar.json", 'w', encoding='utf-8') as f:
            json.dump([elegido], f, indent=2, ensure_ascii=False)
        
        # Agregar a subidos.json
        subidos.append(elegido['url'])
        with open("subidos.json", 'w', encoding='utf-8') as f:
            json.dump(subidos, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Video elegido por IA: {elegido['title']}")
        print(f"📝 URL registrada en subidos.json")
        
        # Notificar en Telegram
        if BOT_TOKEN and CHAT_ID:
            mensaje = (
                f"🤖 *Video elegido por IA*\n\n"
                f"📺 *{elegido['title']}*\n"
                f"📡 Canal: {elegido['channel']}\n"
                f"🆔 ID: `{elegido['video_id']}`\n"
                f"🔗 {elegido['url']}"
            )
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"},
                timeout=10
            )
            print("✅ Notificación enviada a Telegram")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    elegir_con_ia()