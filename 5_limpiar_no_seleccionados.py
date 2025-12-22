import json

def limpiar_no_seleccionados():
    # Cargar videos
    with open("data.json", 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    # Filtrar solo seleccionados
    antes = len(videos)
    videos = [v for v in videos if v['status'] == 'seleccionado']
    eliminados = antes - len(videos)
    
    # Guardar
    with open("data.json", 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
    
    print(f"✓ {eliminados} videos eliminados, {len(videos)} seleccionados conservados")

if __name__ == "__main__":
    limpiar_no_seleccionados()