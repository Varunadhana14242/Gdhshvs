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

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager

# Read environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

# Initialize Pyrogram bot client
bot = Client("telegram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask App for Health Check
app = Flask(__name__)
@app.route("/")
def health_check():
    return "✅ Bot is running!", 200

def extract_dropgalaxy_link(url):
    # Set up Chrome options
    options = Options()
    # Set the binary location to the Chrome executable (adjust if needed)
    options.binary_location = "/usr/bin/google-chrome"
    # For debugging, you can comment out headless to see the browser window:
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    
    # Initialize the undetected-chromedriver
    driver = uc.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get(url)
        print("🚀 DropGalaxy page loaded.")
        
        # Wait for the "Free Download" button for up to 30 seconds
        free_download_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.NAME, "method_free"))
        )
        free_download_button.click()
        print("✅ Clicked 'Free Download' button.")
        
        # Wait for the countdown to finish (increase if needed)
        print("⏳ Waiting for countdown to finish...")
        time.sleep(15)
        
        # Log a snippet of the page source for debugging
        page_snippet = driver.page_source[:1000]
        print("Page snippet after countdown:", page_snippet)
        
        # Wait for the final download link to be clickable
        download_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Download')]"))
        )
        download_link = download_button.get_attribute("href")
        print("🎯 Download link extracted:", download_link)
        
        if download_link:
            return download_link
        else:
            return "❌ Error: Direct download link not found."
    except Exception as e:
        return f"❌ Error: {str(e)}"
    finally:
        driver.quit()

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

async def send_file_to_telegram(file_path, message):
    await bot.start()
    if os.path.getsize(file_path) > 2000000000:  # 2GB limit for Telegram bots
        await message.reply_text("❌ File is too large to send on Telegram!")
        return
    if file_path.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
        await bot.send_video(chat_id=CHAT_ID, video=file_path, caption="📽️ Here is your video file!", supports_streaming=True)
    else:
        await bot.send_document(chat_id=CHAT_ID, document=file_path, caption="📂 Here is your file!")
    await bot.stop()

@bot.on_message(filters.command("start"))
def start_command(client: Client, message: Message):
    message.reply_text("✅ Bot is running! Send me a DropGalaxy link to download directly.")

@bot.on_message(filters.text & ~filters.command(["start"]))
async def handle_dropgalaxy(client: Client, message: Message):
    text = message.text.strip()
    if "dropgalaxy" not in text:
        await message.reply_text("⚠️ Please send a valid DropGalaxy link.")
        return
    await message.reply_text("⏳ Extracting direct download link...")
    direct_link = extract_dropgalaxy_link(text)
    if "❌" in direct_link:
        await message.reply_text(direct_link)
        return
    await message.reply_text("✅ Direct link found! Downloading file...")
    file_path = download_file(direct_link)
    await send_file_to_telegram(file_path, message)
    await message.reply_text("✅ All files have been sent!")

if __name__ == "__main__":
    def run_flask():
        app.run(host="0.0.0.0", port=5000)
    Thread(target=run_flask).start()
    bot.run()
