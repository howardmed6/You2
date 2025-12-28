import json
import sys
import os
import requests

def cambiar_a_seleccionado(ids_str):
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    
    print("📝 Cambiando videos a status 'seleccionado'...")
    
    # Cargar videos
    try:
        with open("data.json", 'r', encoding='utf-8') as f:
            videos = json.load(f)
        print(f"📊 Total de videos en data.json: {len(videos)}")
    except FileNotFoundError:
        error_msg = "❌ Error: No se encontró data.json"
        print(error_msg)
        sys.exit(1)
    
    # Procesar IDs
    ids = [id.strip() for id in ids_str.split(',')]
    print(f"🔍 Buscando {len(ids)} video(s)...")
    
    # Cambiar status
    cambiados = 0
    no_encontrados = []
    detalles = []
    
    for video in videos:
        if video['video_id'] in ids:
            status_anterior = video.get('status', 'sin status')
            video['status'] = 'seleccionado'
            cambiados += 1
            detalles.append({
                'titulo': video['title'],
                'canal': video['channel'],
                'id': video['video_id'],
                'status_anterior': status_anterior
            })
            print(f"✅ {video['title']}")
            print(f"   Status: {status_anterior} → seleccionado")
    
    # Verificar IDs no encontrados
    ids_encontrados = [d['id'] for d in detalles]
    no_encontrados = [id for id in ids if id not in ids_encontrados]
    
    if no_encontrados:
        print(f"\n⚠️ {len(no_encontrados)} ID(s) no encontrado(s):")
        for id_ne in no_encontrados:
            print(f"   • {id_ne}")
    
    # Guardar
    with open("data.json", 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ {cambiados} video(s) cambiado(s) a 'seleccionado'")
    print(f"💾 Cambios guardados en data.json")
    
    # Notificar en Telegram
    if BOT_TOKEN and CHAT_ID and cambiados > 0:
        mensaje = f"✅ *{cambiados} video(s) seleccionado(s)*\n\n"
        
        for detalle in detalles:
            mensaje += f"📺 {detalle['titulo']}\n"
            mensaje += f"📡 {detalle['canal']}\n"
            mensaje += f"🆔 `{detalle['id']}`\n"
            mensaje += f"🔄 {detalle['status_anterior']} → seleccionado\n\n"
        
        if no_encontrados:
            mensaje += f"⚠️ {len(no_encontrados)} ID(s) no encontrado(s)"
        
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"},
                timeout=10
            )
            print("📱 Notificación enviada a Telegram")
        except Exception as e:
            print(f"⚠️ No se pudo enviar notificación: {e}")

def mostrar_ayuda():
    ayuda = """
╔═══════════════════════════════════════════════════════════╗
║  📝 CAMBIAR VIDEOS A STATUS 'SELECCIONADO'                ║
╚═══════════════════════════════════════════════════════════╝

📖 USO:
   python script.py ID1,ID2,ID3
   python script.py
   
📌 EJEMPLOS:

   1. Con argumentos:
      python script.py abc123,def456,ghi789
      
   2. Interactivo:
      python script.py
      > IDs separados por coma: abc123,def456,ghi789

   3. Un solo video:
      python script.py abc123

🔍 DESCRIPCIÓN:
   Cambia el status de uno o varios videos en data.json
   a 'seleccionado' para que puedan ser elegidos después.

✅ QUÉ HACE:
   • Lee data.json
   • Busca los videos por ID
   • Cambia su status a 'seleccionado'
   • Guarda los cambios
   • Notifica por Telegram

💡 NOTAS:
   • Los IDs deben estar separados por comas
   • No uses espacios entre IDs (o serán ignorados)
   • Los IDs que no existan serán reportados
   • Se notificará el status anterior de cada video
"""
    print(ayuda)

if __name__ == "__main__":
    ids_str = sys.argv[1] if len(sys.argv) > 1 else input("IDs separados por coma: ").strip()
    
    if ids_str:
        cambiar_a_seleccionado(ids_str)
    else:
        print("❌ No se ingresaron IDs")
        sys.exit(1)