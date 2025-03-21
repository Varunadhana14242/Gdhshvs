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
CHAT_ID = int(os.getenv("CHAT_ID"))  # Ensure it's an integer

# Initialize Pyrogram bot client
bot = Client("telegram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask App for Health Check
app = Flask(__name__)

@app.route("/")
def health_check():
    """Health check endpoint for the server"""
    return "✅ Bot is running!", 200

# Function to extract the real download link from DropGalaxy
def extract_dropgalaxy_link(url):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        # Step 1: Get the initial page
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            return "❌ Error: Unable to access DropGalaxy."

        soup = BeautifulSoup(response.text, "html.parser")

        # Step 2: Extract the file ID
        file_id_match = re.search(r'name="id" value="([^"]+)"', response.text)
        if not file_id_match:
            return "❌ Error: No file ID found."

        file_id = file_id_match.group(1)

        # Step 3: Submit form to get the direct download link
        payload = {
            'op': 'download2',
            'id': file_id,
            'method_free': 'Free Download'
        }

        time.sleep(5)  # Simulate the DropGalaxy wait timer
        post_response = session.post(url, data=payload, headers=headers)
        post_soup = BeautifulSoup(post_response.text, "html.parser")

        # Step 4: Extract the final download link
        download_link = post_soup.find("a", href=True, string=re.compile("https://", re.IGNORECASE))
        if download_link:
            return download_link["href"]
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
    await bot.start()  # Fix: Properly start Pyrogram
    
    file_size = os.path.getsize(file_path)

    if file_size > 2000000000:  # 2GB limit for Telegram bots
        await message.reply_text("❌ File is too large to send on Telegram!")
        return
    
    # Ensure Telegram detects it as a video
    if file_path.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
        await bot.send_video(
            chat_id=CHAT_ID,
            video=file_path,
            caption="📽️ Here is your video file!",
            supports_streaming=True
        )
    else:
        await bot.send_document(
            chat_id=CHAT_ID,
            document=file_path,
            caption="📂 Here is your file!"
        )

    await bot.stop()  # Fix: Properly stop Pyrogram

# Telegram bot command handler
@bot.on_message(filters.command("start"))
def start_command(client: Client, message: Message):
    message.reply_text("✅ Bot is running! Send me a DropGalaxy link to download directly.")

# Telegram bot handler for DropGalaxy links
@bot.on_message(filters.text & ~filters.command(["start"]))
async def handle_dropgalaxy(client: Client, message: Message):
    text = message.text.strip()

    # ✅ Ensure only ONE error message is sent for invalid links
    if not re.search(r"dropgalaxy\.com", text):
        if not hasattr(client, "sent_invalid_link_msg"):  # Check if the bot already sent a message
            client.sent_invalid_link_msg = True  # Mark that the message was sent
            await message.reply_text("⚠️ Please send a valid DropGalaxy link.")
        return

    # ✅ Extract the download link
    await message.reply_text("⏳ Extracting direct download link...")

    direct_link = extract_dropgalaxy_link(text)
    if "❌" in direct_link:
        await message.reply_text(direct_link)
        return

    await message.reply_text(f"✅ Direct link found! Downloading file...")

    # ✅ Download the file
    file_path = download_file(direct_link)

    # ✅ If it's a ZIP file, extract and send files individually
    if file_path.endswith(".zip"):
        await message.reply_text("📂 Extracting ZIP file...")
        extracted_files = extract_zip(file_path)

        for extracted_file in extracted_files:
            await send_file_to_telegram(extracted_file, message)
    else:
        # ✅ Send the file to Telegram
        await send_file_to_telegram(file_path, message)

    await message.reply_text("✅ All files have been sent!")

if __name__ == "__main__":
    # Start Flask app for health check in a separate thread
    def run_flask():
        app.run(host="0.0.0.0", port=5000)

    Thread(target=run_flask).start()

    # Start the Telegram bot
    bot.run()
