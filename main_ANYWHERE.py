import os
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi

# --- CONFIGURACIÓN ---
# Pega tus datos directamente aquí. Asegúrate de que estén entre las comillas.
TELEGRAM_TOKEN = "8492260970:AAH9LDcnru8MqFCcB-7Kl7IlG9WaHO2tfIs"
TELEGRAM_CHAT_ID = "481040187"
RSS_FEED_URL = "https://rss.app/feeds/0Q2g5a7J2b8o7P3h.xml"

# Opcional: Si quieres mejor calidad en los resúmenes, pega tu clave de Hugging Face.
# Si no, déjalo como está.
HUGGINGFACE_API_KEY = "" 

# Ruta donde se guardará el ID del último video. 
# Asegúrate de cambiar "fjdani" por tu nombre de usuario en PythonAnywhere.
LAST_VIDEO_FILE = "/home/fjdani/youtube-summarizer/last_video_id.txt" 

# --- FUNCIONES ---

def get_last_processed_video_id():
    try:
        with open(LAST_VIDEO_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_last_processed_video_id(video_id):
    # Asegúrate de que el directorio existe
    os.makedirs(os.path.dirname(LAST_VIDEO_FILE), exist_ok=True)
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
    max_input_length = 30000
    if len(text) > max_input_length:
        text = text[:max_input_length]
    max_length = len(text.split()) // 3
    min_length = max(50, max_length // 2)
    payload = {"inputs": text, "parameters": {"max_length": int(max_length), "min_length": int(min_length), "do_sample": False}}
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=180)
        if response.status_code == 200:
            return response.json()[0]['summary_text']
        else:
            return "(No se pudo generar el resumen por un error de la API.)"
    except Exception:
        return "(No se pudo generar el resumen por un error de conexión.)"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    requests.post(url, json=payload)

# --- LÓGICA PRINCIPAL ---

def main():
    print("Iniciando revisión de nuevos vídeos...")
    response = requests.get(RSS_FEED_URL)
    feed = feedparser.parse(response.content)
    
    if not feed.entries:
        print("El feed no contiene vídeos. Saliendo.")
        return

    latest_video = feed.entries[0]
    latest_video_id = latest_video.link.split('v=')[-1]
    last_processed_id = get_last_processed_video_id()
    
    print(f"Último vídeo: {latest_video.title} ({latest_video_id})")

    if latest_video_id != last_processed_id:
        print("¡Nuevo vídeo detectado!")
        transcript = get_video_transcript(video_id=latest_video_id)
        
        if transcript and len(transcript.strip()) > 50:
            print("Generando resumen...")
            summary = summarize_text(transcript)
            message = (
                f"🚀 *Nuevo Vídeo en Into The Cryptoverse!*\n\n"
                f"*{latest_video.title}*\n\n"
                f"📝 *Resumen IA:*\n{summary}\n\n"
                f"🔗 [Ver Vídeo]({latest_video.link})"
            )
            send_telegram_message(message)
            save_last_processed_video_id(latest_video_id)
            print("¡Proceso completado con éxito!")
        else:
            print("No se pudo obtener una transcripción válida. Enviando notificación sin resumen.")
            message_no_summary = (
                f"🚀 *Nuevo Vídeo en Into The Cryptoverse!*\n\n"
                f"*{latest_video.title}*\n\n"
                f"📝 (El resumen IA no pudo ser generado al no haber transcripción disponible.)\n\n"
                f"🔗 [Ver Vídeo]({latest_video.link})"
            )
            send_telegram_message(message_no_summary)
            save_last_processed_video_id(latest_video_id)
    else:
        print("No hay vídeos nuevos.")

if __name__ == "__main__":
    main()
