import json
import requests
from datetime import datetime
import re

def monitor_channels():
    API_KEY = "AIzaSyBZUaGb5RXQOSGpVH25MS3vw1wSggAPZnc"
    
    channels = [
        "UCcVNDl7ZJMf9lC9a34CY4RA",
        "UC5ZiUaIJ2b5dYBYGf5iEUrA",
        "UCjq5m8s71qA9ZMfJw0q7Fgw",
        "UCP7i-E6AYr-UChpNcO0EEag"
    ]
    
    data_file = "data.json"
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        existing_ids = {item['video_id'] for item in existing_data}
    except:
        existing_data = []
        existing_ids = set()
    
    new_videos_count = 0
    
    for channel_id in channels:
        try:
            print(f"Monitoreando canal: {channel_id}")
            
            # Obtener videos recientes del canal
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'key': API_KEY,
                'channelId': channel_id,
                'part': 'snippet',
                'order': 'date',  # IMPORTANTE: orden por fecha
                'maxResults': 50,
                'type': 'video',
                'publishedAfter': get_recent_date()  # Solo videos recientes
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'items' not in data:
                print(f"  Error: {data}")
                continue
            
            video_ids = [item['id']['videoId'] for item in data['items']]
            
            if not video_ids:
                print(f"  No hay videos nuevos")
                continue
            
            # Obtener detalles de los videos (incluyendo duración)
            details_url = "https://www.googleapis.com/youtube/v3/videos"
            details_params = {
                'key': API_KEY,
                'id': ','.join(video_ids),
                'part': 'contentDetails,snippet'
            }
            
            details_response = requests.get(details_url, params=details_params)
            details_data = details_response.json()
            
            if 'items' not in details_data:
                print(f"  Error obteniendo detalles: {details_data}")
                continue
            
            channel_new_videos = 0
            filtered_count = 0
            
            for video in details_data['items']:
                video_id = video['id']
                duration = video['contentDetails']['duration']
                
                # Convertir duración a segundos
                total_seconds = parse_duration(duration)
                
                # FILTRO: Excluir videos menores a 50 segundos
                if total_seconds < 50:
                    filtered_count += 1
                    print(f"  ⏭️  Filtrado ({total_seconds}s): {video['snippet']['title']}")
                    continue
                
                if video_id not in existing_ids:
                    video_data = {
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "title": video['snippet']['title'],
                        "channel": video['snippet']['channelTitle'],
                        "channel_id": channel_id,
                        "published": video['snippet']['publishedAt'],
                        "duration": duration,
                        "duration_seconds": total_seconds,
                        "found_at": datetime.now().isoformat(),
                        "status": "pending"
                    }
                    existing_data.append(video_data)
                    existing_ids.add(video_id)
                    channel_new_videos += 1
                    new_videos_count += 1
                    print(f"  ✓ Nuevo video ({total_seconds}s): {video['snippet']['title']}")
            
            print(f"  📊 Procesados: {len(details_data['items'])} videos")
            print(f"  ⏭️  Filtrados (<50s): {filtered_count}")
            print(f"  ✨ Nuevos guardados: {channel_new_videos}")
            
        except Exception as e:
            print(f"Error procesando canal {channel_id}: {e}")
    
    # Ordenar por fecha de publicación (más recientes primero)
    existing_data.sort(key=lambda x: x['published'], reverse=True)
    
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        print(f"\n{'='*50}")
        print(f"✅ Videos nuevos encontrados: {new_videos_count}")
        print(f"📦 Total en base de datos: {len(existing_data)}")
        print(f"{'='*50}")
    except Exception as e:
        print(f"Error guardando datos: {e}")

def parse_duration(duration):
    """
    Convierte duración ISO 8601 a segundos
    Ejemplo: PT1M30S = 90 segundos, PT45S = 45 segundos
    """
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

def get_recent_date():
    """
    Devuelve fecha de hace 60 días en formato ISO 8601
    Esto asegura que solo tome videos recientes
    """
    from datetime import timedelta
    recent = datetime.now() - timedelta(days=60)
    return recent.strftime('%Y-%m-%dT%H:%M:%SZ')

if __name__ == "__main__":
    monitor_channels()