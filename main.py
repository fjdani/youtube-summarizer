import os
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCRvqjQP_of_v2ubqXN-e2wQ"
LAST_VIDEO_FILE = "last_video_id.txt"

# --- FUNCIONES (sin cambios) ---

def get_last_processed_video_id():
    try:
        with open(LAST_VIDEO_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_last_processed_video_id(video_id):
    with open(LAST_VIDEO_FILE, "w") as f:
        f.write(video_id)

def get_video_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'es'])
        return " ".join([item['text'] for item in transcript_list])
    except Exception as e:
        print(f"Error al obtener la transcripción: {e}")
        return None

def summarize_text(text):
    api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"} if HUGGINGFACE_API_KEY else {}

    max_chunk_size = 1024
    text_chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
    
    summary_chunks = []
    for chunk in text_chunks:
        max_length = len(chunk.split()) // 3
        min_length = max(20, max_length // 2)

        payload = { "inputs": chunk, "parameters": { "max_length": int(max_length), "min_length": int(min_length), "do_sample": False } }
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                summary_chunks.append(response.json()[0]['summary_text'])
            else:
                print(f"Error en la API de Hugging Face: {response.text}")
        except Exception as e:
            print(f"Error al contactar Hugging Face: {e}")

    if summary_chunks:
        return " ".join(summary_chunks)
    else:
        return "No se pudo generar el resumen."

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = { 'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown' }
    requests.post(url, json=payload)

# --- LÓGICA PRINCIPAL (MODIFICADA) ---

def main():
    print("Iniciando la revisión de nuevos videos...")
    
    # --- NUEVA SECCIÓN DE DIAGNÓSTICO ---
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    
    try:
        print(f"Obteniendo feed desde: {YOUTUBE_RSS_URL}")
        response = requests.get(YOUTUBE_RSS_URL, headers=headers, timeout=15)
        
        # Imprimimos diagnósticos clave
        print(f"Status Code: {response.status_code}")
        print(f"Response Content (primeros 500 caracteres): {response.text[:500]}")

        if response.status_code != 200:
            print("Error: La solicitud no fue exitosa.")
            return

        # Pasamos el contenido a feedparser
        feed = feedparser.parse(response.content)

    except requests.exceptions.RequestException as e:
        print(f"Error al hacer la solicitud HTTP: {e}")
        return
    # --- FIN DE LA NUEVA SECCIÓN ---
    
    if not feed.entries:
        print("El feed no contiene videos. Saliendo.")
        return

    latest_video = feed.entries[0]
    latest_video_id = latest_video.yt_videoid
    
    last_processed_id = get_last_processed_video_id()
    
    print(f"Último video en el feed: {latest_video_id}")
    print(f"Último video procesado: {last_processed_id}")

    if latest_video_id != last_processed_id:
        print(f"¡Nuevo video detectado! Título: {latest_video.title}")
        
        transcript = get_video_transcript(latest_video_id)
        
        if transcript:
            print("Generando resumen...")
            summary = summarize_text(transcript)
            
            message = (
                f"🚀 *Nuevo Video en Into The Cryptoverse!*\n\n"
                f"*{latest_video.title}*\n\n"
                f"📝 *Resumen IA:*\n{summary}\n\n"
                f"🔗 [Ver video]({latest_video.link})"
            )
            
            print("Enviando mensaje a Telegram...")
            send_telegram_message(message)
            
            save_last_processed_video_id(latest_video_id)
            print("¡Proceso completado con éxito!")
        else:
            print("No se pudo obtener la transcripción. No se enviará resumen.")
    else:
        print("No hay videos nuevos.")

if __name__ == "__main__":
    main()
