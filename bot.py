import os
import time
import requests
import re
import asyncio
import zipfile
from pyrogram import Client, filters
from pyrogram.types import Message
from bs4 import BeautifulSoup
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

# Function to get direct download link from HotDebrid
def get_premium_link(dropgalaxy_url):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        # Step 1: Send DropGalaxy link to HotDebrid
        debrid_url = "https://www.hotdebrid.com/premium-link-generator/dropgalaxy"
        data = {"link": dropgalaxy_url}

        response = session.post(debrid_url, data=data, headers=headers)
        if response.status_code != 200:
            return "❌ Error: Unable to access HotDebrid."

        # Step 2: Extract the generated premium link
        soup = BeautifulSoup(response.text, "html.parser")
        link_tag = soup.find("a", href=True, text=re.compile("Download", re.IGNORECASE))

        if link_tag:
            return link_tag["href"]
        else:
            return "❌ Error: Failed to get a premium link from HotDebrid."

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

# Function to extract ZIP files and return extracted files
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
    message.reply_text("✅ Bot is running! Send me a DropGalaxy link to bypass using HotDebrid.")

# Telegram bot handler for DropGalaxy links
@bot.on_message(filters.text & ~filters.command(["start"]))
async def handle_dropgalaxy(client: Client, message: Message):
    text = message.text.strip()

    if "dropgalaxy" in text:
        await message.reply_text("⏳ Checking HotDebrid for a premium link...")

        # Get direct download link from HotDebrid
        direct_link = get_premium_link(text)
        if "❌" in direct_link:
            await message.reply_text(direct_link)
            return

        await message.reply_text(f"✅ Premium link found! Downloading file...")

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
