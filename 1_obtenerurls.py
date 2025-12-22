import json
import requests
from datetime import datetime

def monitor_channels():
    # TU API KEY DE YOUTUBE (obtener en Google Cloud Console)
    API_KEY = "AIzaSyBZUaGb5RXQOSGpVH25MS3vw1wSggAPZnc"  # REEMPLAZAR CON TU API KEY
    
    # Lista de canales a monitorear
    channels = [
        "UCcVNDl7ZJMf9lC9a34CY4RA",  # Canal original
        "UC5ZiUaIJ2b5dYBYGf5iEUrA",  # Segundo canal
        "UCjq5m8s71qA9ZMfJw0q7Fgw",  # Tercer canal
        "UCP7i-E6AYr-UChpNcO0EEag"   # Cuarto canal
    ]
    
    data_file = "data.json"
    
    # Cargar datos existentes
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
            
            # YouTube API para obtener 35 videos
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'key': API_KEY,
                'channelId': channel_id,
                'part': 'snippet',
                'order': 'date',
                'maxResults': 35,
                'type': 'video'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'items' not in data:
                print(f"  Error: {data}")
                continue
            
            channel_new_videos = 0
            
            for item in data['items']:
                video_id = item['id']['videoId']
                
                if video_id not in existing_ids:
                    video_data = {
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "title": item['snippet']['title'],
                        "channel": item['snippet']['channelTitle'],
                        "channel_id": channel_id,
                        "published": item['snippet']['publishedAt'],
                        "found_at": datetime.now().isoformat(),
                        "status": "pending"
                    }
                    existing_data.append(video_data)
                    existing_ids.add(video_id)
                    channel_new_videos += 1
                    new_videos_count += 1
                    print(f"  Nuevo video: {item['snippet']['title']}")
            
            print(f"  Procesados {len(data['items'])} videos, {channel_new_videos} nuevos")
            
        except Exception as e:
            print(f"Error procesando canal {channel_id}: {e}")
    
    # Guardar datos
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        print(f"\nResumen: Se encontraron {new_videos_count} videos nuevos en total")
        print(f"Total de videos en la base de datos: {len(existing_data)}")
    except Exception as e:
        print(f"Error guardando datos: {e}")

if __name__ == "__main__":
    monitor_channels()