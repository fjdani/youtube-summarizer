import os
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

# Leemos la URL estable desde los secrets de GitHub
RSS_FEED_URL = os.environ.get("RSS_URL")
LAST_VIDEO_FILE = "last_video_id.txt"

# --- FUNCIONES ---

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

    return " ".join(summary_chunks) if summary_chunks else "No se pudo generar el resumen."

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = { 'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown' }
    requests.post(url, json=payload)

# --- LÓGICA PRINCIPAL ---

def main():
    if not RSS_FEED_URL:
        print("Error: La variable RSS_URL no está configurada en los Secrets de GitHub.")
        return

    print("Iniciando la revisión de nuevos videos...")
    print(f"Obteniendo feed desde la URL de RSS.app...")

    response = requests.get(RSS_FEED_URL)
    feed = feedparser.parse(response.content)
    
    if not feed.entries:
        print("El feed no contiene videos. Saliendo.")
        return

    latest_video = feed.entries[0]
    # Extraemos el ID del video del link
    latest_video_id = latest_video.link.split('v=')[-1]
    
    last_processed_id = get_last_processed_video_id()
    
    print(f"Último video en el feed: {latest_video.title} ({latest_video_id})")
    print(f"Último video procesado: {last_processed_id}")

    if latest_video_id != last_processed_id:
        print(f"¡Nuevo video detectado!")
        
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
