import os
import re
import requests
import feedparser
import yt_dlp

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

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
    """Gets the transcript using the robust yt-dlp library."""
    print("Fetching transcript with yt-dlp...")
    # Use a unique filename for the transcript
    output_template = f"{video_id}.vtt"
    
    ydl_opts = {
        'writeautomaticsub': True,
        'subtitleslangs': ['en', 'es'],
        'subtitlesformat': 'vtt',
        'skip_download': True,
        'outtmpl': output_template.replace('.vtt', ''), # yt-dlp adds the lang and extension
        'quiet': True,
    }
    
    transcript_file = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
        
        # Find the downloaded file (e.g., video_id.en.vtt)
        for lang in ['en', 'es']:
            expected_file = f"{video_id}.{lang}.vtt"
            if os.path.exists(expected_file):
                transcript_file = expected_file
                break
        
        if not transcript_file:
            print("Transcript file was not downloaded by yt-dlp.")
            return None
        
        # Read and parse the VTT file
        with open(transcript_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Basic VTT parsing to extract just the text
        text_lines = []
        for line in lines:
            # Skip metadata and timestamp lines
            if '-->' not in line and not line.strip().isdigit() and line.strip() and not line.strip().startswith('WEBVTT') and not line.strip().startswith('Kind:'):
                cleaned_line = re.sub(r'<[^>]+>', '', line).strip() # Remove VTT tags
                text_lines.append(cleaned_line)
        
        print("Transcript fetched and parsed successfully.")
        return " ".join(text_lines)
            
    except Exception as e:
        print(f"An error occurred with yt-dlp: {e}")
        return None
    finally:
        # Clean up any downloaded transcript files
        if transcript_file and os.path.exists(transcript_file):
            os.remove(transcript_file)
        # Also try to remove other possible filenames
        for lang in ['en', 'es']:
            potential_file = f"{video_id}.{lang}.vtt"
            if os.path.exists(potential_file):
                os.remove(potential_file)


def summarize_text(text):
    """Generates a summary of the text using the Hugging Face API."""
    api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"} if HUGGINGFACE_API_KEY else {}

    # Truncate text to avoid overly long inputs for the summarizer
    max_input_length = 30000  # Generous character limit
    if len(text) > max_input_length:
        text = text[:max_input_length]

    max_length = len(text.split()) // 3
    min_length = max(50, max_length // 2)

    payload = {
        "inputs": text,
        "parameters": { "max_length": int(max_length), "min_length": int(min_length), "do_sample": False }
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=180) # Increased timeout
        if response.status_code == 200:
            return response.json()[0]['summary_text']
        else:
            print(f"Error from Hugging Face API: {response.text}")
            # Check for model loading error
            if isinstance(response.json(), dict) and 'error' in response.json():
                return f"(Could not generate summary: {response.json()['error']})"
            return "(Could not generate summary due to API error.)"
    except Exception as e:
        print(f"Error contacting Hugging Face: {e}")
        return "(Could not generate summary due to connection error.)"


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
    
    if not feed.entries:
        print("Feed does not contain any videos. Exiting.")
        return

    latest_video = feed.entries[0]
    latest_video_id = latest_video.link.split('v=')[-1]
    
    last_processed_id = get_last_processed_video_id()
    
    print(f"Latest video in feed: {latest_video.title} ({latest_video_id})")
    print(f"Last processed video: {last_processed_id}")

    if latest_video_id != last_processed_id:
        print("New video detected!")
        
        transcript = get_video_transcript(video_id=latest_video_id)
        
        if transcript and len(transcript.strip()) > 50: # Check for a meaningful transcript
            print("Generating summary...")
            summary = summarize_text(transcript)
            
            message = (
                f"🚀 *New Video on Into The Cryptoverse!*\n\n"
                f"*{latest_video.title}*\n\n"
                f"📝 *AI Summary:*\n{summary}\n\n"
                f"🔗 [Watch Video]({latest_video.link})"
            )
            
            print("Sending message to Telegram...")
            send_telegram_message(message)
            
            save_last_processed_video_id(latest_video_id)
            print("Process completed successfully!")
        else:
            print("Could not get a valid transcript. No summary will be sent.")
            # Optionally, send a notification without a summary
            message_no_summary = (
                f"🚀 *New Video on Into The Cryptoverse!*\n\n"
                f"*{latest_video.title}*\n\n"
                f"📝 (AI summary could not be generated as no transcript was available.)\n\n"
                f"🔗 [Watch Video]({latest_video.link})"
            )
            send_telegram_message(message_no_summary)
            save_last_processed_video_id(latest_video_id)
            print("Sent notification without summary.")

    else:
        print("No new videos found.")

if __name__ == "__main__":
    main()
