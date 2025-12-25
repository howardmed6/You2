import json
import requests
import os
import sys

def analizar_videos():
    # --- CONFIGURACIÓN ---
    # Obtiene la llave directamente de la variable de entorno configurada en Cloud Build
    API_KEY = os.environ.get("OPENAI_API_KEY")
    MODEL = "gpt-4o-mini"
    
    if not API_KEY:
        print("❌ Error: No se encontró la variable de entorno OPENAI_API_KEY.")
        sys.exit(1)

    # 1. Cargar videos desde data.json
    try:
        with open("data.json", 'r', encoding='utf-8') as f:
            videos = json.load(f)
    except Exception as e:
        print(f"❌ Error al leer data.json: {e}")
        sys.exit(1)

    # Filtrar solo los videos pendientes
    pendientes = [v for v in videos if v.get('status') == 'pending']
    
    if not pendientes:
        print("No hay videos con status 'pending' para analizar.")
        return

    print(f"Analizando {len(pendientes)} videos con {MODEL}...")

    # 2. Preparar el prompt con los títulos
    titulos_lista = "\n".join([f"{i+1}. {v['title']}" for i, v in enumerate(pendientes)])
    
    prompt = (
        "Analiza los siguientes títulos de videos de YouTube. "
        "Devuelve ÚNICAMENTE los números de la lista de aquellos que tengan mayor potencial de ser virales o interesantes. "
        "Separa los números solo con comas, sin puntos ni texto adicional.\n\n"
        f"{titulos_lista}\n\n"
        "Respuesta (solo números separados por coma):"
    )

    # 3. Llamada a la API de OpenAI
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
                "max_tokens": 150
            },
            timeout=45
        )

        # Verificar si la respuesta fue exitosa
        if response.status_code != 200:
            print(f"❌ Error de OpenAI (Status {response.status_code}): {response.text}")
            sys.exit(1)

        data = response.json()
        respuesta_ia = data['choices'][0]['message']['content'].strip()
        print(f"IA seleccionó los índices: {respuesta_ia}")

        # 4. Procesar los números seleccionados
        # Limpiamos posibles caracteres extra que la IA a veces incluye
        indices_seleccionados = []
        for n in respuesta_ia.replace('.', '').replace(' ', '').split(','):
            if n.isdigit():
                indices_seleccionados.append(int(n) - 1)

        # 5. Actualizar el status en la lista original
        count_si = 0
        count_no = 0
        for i, video in enumerate(pendientes):
            if i in indices_seleccionados:
                video['status'] = 'seleccionado'
                count_si += 1
            else:
                video['status'] = 'descartado'
                count_no += 1

        # 6. Guardar los cambios de vuelta en data.json
        with open("data.json", 'w', encoding='utf-8') as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)

        print(f"✅ Proceso terminado: {count_si} seleccionados, {count_no} descartados.")

    except Exception as e:
        print(f"❌ Error durante el análisis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analizar_videos()