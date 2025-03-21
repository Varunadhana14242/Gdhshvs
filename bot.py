import os
import time
import requests
import re
import asyncio
import zipfile
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread

# Read environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # The chat ID where notifications will be sent

# Initialize Pyrogram bot client
bot = Client("telegram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask App for Health Check
app = Flask(__name__)

@app.route("/")
def health_check():
    """Health check endpoint for the server"""
    return "✅ Bot is running!", 200

# Function to bypass DropGalaxy and get the direct download link
def bypass_dropgalaxy(url):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        # Step 1: Get initial page
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            return "❌ Error: Unable to access DropGalaxy."

        # Extract form action URL
        match = re.search(r'action="([^"]+)"', response.text)
        if not match:
            return "❌ Error: No action URL found."

        action_url = match.group(1)

        # Extract key parameters
        match = re.search(r'name="op" value="([^"]+)"', response.text)
        if not match:
            return "❌ Error: No operation key found."

        op_value = match.group(1)

        file_id_match = re.search(r'name="id" value="([^"]+)"', response.text)
        if not file_id_match:
            return "❌ Error: No file ID found."

        file_id = file_id_match.group(1)

        payload = {
            'op': op_value,
            'usr_login': '',
            'id': file_id,
            'fname': '',
            'referer': '',
            'method_free': 'Free Download'
        }

        # Step 2: Submit form and wait
        time.sleep(5)  # Simulate the countdown timer
        post_response = session.post(action_url, data=payload, headers=headers)

        # Step 3: Extract direct download link
        final_match = re.search(r'href="(https://[^"]+)"', post_response.text)
        if final_match:
            return final_match.group(1)
        else:
            return "❌ Error: Direct download link not found."

    except requests.exceptions.RequestException as e:
        return f"❌ Error: {e}"

# Function to download a file from a URL
def download_file(url):
    local_filename = url.split("/")[-1]
    local_path = f"downloads/{local_filename}"

    os.makedirs("downloads", exist_ok=True)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    
    return local_path

# Function to extract ZIP files and return the list of extracted files
def extract_zip(file_path):
    extracted_files = []
    extract_folder = file_path.replace(".zip", "")

    os.makedirs(extract_folder, exist_ok=True)

    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)
        extracted_files = [os.path.join(extract_folder, f) for f in zip_ref.namelist()]

    return extracted_files

# Function to send a file to Telegram
async def send_file_to_telegram(file_path, message):
    with bot:
        file_size = os.path.getsize(file_path)

        if file_size > 2000000000:  # 2GB limit for Telegram bots
            await message.reply_text("❌ File is too large to send on Telegram!")
            return
        
        # Check file type and send accordingly
        if file_path.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
            await bot.send_video(CHAT_ID, video=file_path, caption="📽️ Here is your video file!")
        else:
            await bot.send_document(CHAT_ID, document=file_path, caption="📂 Here is your file!")

# Telegram bot command handler
@bot.on_message(filters.command("start"))
def start_command(client: Client, message: Message):
    message.reply_text("✅ Bot is running! Send me a DropGalaxy link to bypass.")

# Telegram bot handler for DropGalaxy links
@bot.on_message(filters.text & ~filters.command(["start"]))
async def handle_dropgalaxy(client: Client, message: Message):
    text = message.text.strip()

    if "dropgalaxy" in text:
        await message.reply_text("⏳ Processing your DropGalaxy link, please wait...")

        # Get direct download link
        direct_link = bypass_dropgalaxy(text)
        if "❌" in direct_link:
            await message.reply_text(direct_link)
            return

        await message.reply_text(f"✅ Direct download link found! Downloading file...")

        # Download the file
        file_path = download_file(direct_link)

        # If it's a ZIP file, extract and send files individually
        if file_path.endswith(".zip"):
            await message.reply_text("📂 Extracting ZIP file...")
            extracted_files = extract_zip(file_path)

            for extracted_file in extracted_files:
                await send_file_to_telegram(extracted_file, message)
        else:
            # Send the file to Telegram
            await send_file_to_telegram(file_path, message)

        await message.reply_text("✅ All files have been sent!")

    else:
        await message.reply_text("⚠️ Please send a valid DropGalaxy link.")

if __name__ == "__main__":
    # Start Flask app for health check in a separate thread
    def run_flask():
        app.run(host="0.0.0.0", port=5000)

    Thread(target=run_flask).start()

    # Start the Telegram bot
    bot.run()
