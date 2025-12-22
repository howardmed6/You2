import json
import requests

def analizar_videos():
    # OPENAI API KEY - Obtener en https://platform.openai.com/api-keys
    API_KEY = "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"  # REEMPLAZAR CON TU API KEY
    
    # MODELO A USAR - Opciones: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
    MODEL = "gpt-4o-mini"  # Más barato y rápido
    
    # Cargar videos pendientes
    with open("data.json", 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    pendientes = [v for v in videos if v['status'] == 'pending']
    
    if not pendientes:
        print("No hay videos pendientes")
        return
    
    print(f"Analizando {len(pendientes)} videos...")
    
    # Preparar lista de títulos
    titulos = "\n".join([f"{i+1}. {v['title']}" for i, v in enumerate(pendientes)])
    
    # Llamada a OpenAI
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [{
                "role": "user",
                "content": f"Analiza estos títulos de videos y devuelve SOLO los números (separados por coma) de los que sean potencialmente virales, interesantes o con buen potencial de vistas:\n\n{titulos}\n\nRespuesta (solo números):"
            }],
            "temperature": 0.3,
            "max_tokens": 200
        }
    )
    
    # Procesar respuesta
    numeros = response.json()['choices'][0]['message']['content'].strip()
    seleccionados = [int(n.strip())-1 for n in numeros.replace('.','').split(',') if n.strip().isdigit()]
    
    # Actualizar status
    for i, video in enumerate(pendientes):
        video['status'] = 'seleccionado' if i in seleccionados else 'descartado'
    
    # Guardar cambios
    with open("data.json", 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
    
    print(f"✓ {len(seleccionados)} videos seleccionados, {len(pendientes)-len(seleccionados)} descartados")

if __name__ == "__main__":
    analizar_videos()