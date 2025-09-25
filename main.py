import os
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

# The stable URL is read from GitHub Secrets
RSS_FEED_URL = os.environ.get("RSS_URL")
LAST_VIDEO_FILE = "last_video_id.txt"

# --- FUNCTIONS ---

def get_last_processed_video_id():
    """Reads the ID of the last processed video from a file."""
    try:
        with open(LAST_VIDEO_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_last_processed_video_id(video_id):
    """Saves the ID of the newly processed video."""
    with open(LAST_VIDEO_FILE, "w") as f:
        f.write(video_id)

def get_video_transcript(video_id):
    """Gets the transcript for a given YouTube video ID."""
    try:
        # Correct call for the youtube-transcript-api library
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'es'])
        return " ".join([item['text'] for item in transcript_list])
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def summarize_text(text):
    """Generates a summary of the text using the Hugging Face API."""
    api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"} if HUGGINGFACE_API_KEY else {}

    max_chunk_size = 1024
    text_chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
    
    summary_chunks = []
    for chunk in text_chunks:
        max_length = len(chunk.split()) // 3
        min_length = max(20, max_length // 2)

        payload = {
            "inputs": chunk,
            "parameters": {
                "max_length": int(max_length),
                "min_length": int(min_length),
                "do_sample": False
            }
        }
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                summary_chunks.append(response.json()[0]['summary_text'])
            else:
                print(f"Error from Hugging Face API: {response.text}")
        except Exception as e:
            print(f"Error contacting Hugging Face: {e}")

    return " ".join(summary_chunks) if summary_chunks else "Could not generate summary."

def send_telegram_message(message):
    """Sends a message via the Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    requests.post(url, json=payload)

# --- MAIN LOGIC ---

def main():
    if not RSS_FEED_URL:
        print("Error: RSS_URL is not configured in GitHub Secrets.")
        return

    print("Checking for new videos...")
    print("Fetching feed from RSS.app URL...")

    response = requests.get(RSS_FEED_URL)
    feed = feedparser.parse(response.content)
    
    if not feed
