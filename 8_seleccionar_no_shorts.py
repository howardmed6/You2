import json
import sys

def seleccionar_trailers():
    try:
        with open("data.json", 'r', encoding='utf-8') as f:
            videos = json.load(f)
    except Exception as e:
        print(f"❌ Error al leer data.json: {e}")
        sys.exit(1)

    count_seleccionados = 0
    count_descartados = 0

    # Palabras clave que indican que el video es un trailer o contenido oficial
    palabras_trailer = ['tráiler', 'trailer', 'promo', 'avance', 'official', 'oficial', 'season', 'temporada', 'volume', 'volumen']

    for video in videos:
        title = video.get('title', '').lower()
        # Si el título contiene alguna palabra de trailer y no contiene shorts
        if any(p in title for p in palabras_trailer) and '#short' not in title and 'shorts' not in title:
            video['status'] = 'seleccionado'
            count_seleccionados += 1
        else:
            video['status'] = 'descartado'
            count_descartados += 1

    with open("data.json", 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)

    print(f"✅ {count_seleccionados} videos marcados como seleccionados")
    print(f"🚫 {count_descartados} videos descartados")

if __name__ == "__main__":
    seleccionar_trailers()
