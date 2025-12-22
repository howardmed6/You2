import json
import sys

def cambiar_a_seleccionado(ids_str):
    # Cargar videos
    with open("data.json", 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    # Procesar IDs
    ids = [id.strip() for id in ids_str.split(',')]
    
    # Cambiar status
    cambiados = 0
    for video in videos:
        if video['video_id'] in ids:
            video['status'] = 'seleccionado'
            cambiados += 1
    
    # Guardar
    with open("data.json", 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
    
    print(f"✓ {cambiados} videos cambiados a seleccionado")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cambiar_a_seleccionado(sys.argv[1])
    else:
        ids = input("IDs separados por coma: ")
        cambiar_a_seleccionado(ids)