import os
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread

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

# Function to extract the DropGalaxy direct download link with adblock and 10x speed
def extract_dropgalaxy_link(url):
    options = Options()
    options.add_argument("--headless")  # Run without UI
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    
    # Load Chrome with uBlock Origin (AdBlock)
    driver = uc.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get(url)
        print("🚀 DropGalaxy page loaded.")

        # Wait for the "Free Download" button and click it
        free_download_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "method_free"))
        )
        free_download_button.click()
        print("✅ Clicked 'Free Download' button.")

        # Skip countdown timer (Wait max 15s)
        print("⏳ Waiting for countdown to finish...")
        time.sleep(8)

        # Extract the final direct download link
        download_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Download')]"))
        )
        download_link = download_button.get_attribute("href")

        if download_link:
            print(f"🎯 Found direct download link: {download_link}")
            return download_link
        else:
            return "❌ Error: Direct download link not found."

    except Exception as e:
        return f"❌ Error: {str(e)}"

    finally:
        driver.quit()

# Function to download a file
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

# Function to send a file to Telegram
async def send_file_to_telegram(file_path, message):
    await bot.start()
    
    if os.path.getsize(file_path) > 2000000000:  # Telegram 2GB limit
        await message.reply_text("❌ File is too large to send on Telegram!")
        return
    
    if file_path.endswith((".mp4", ".mkv", ".avi", ".mov")):
        await bot.send_video(chat_id=CHAT_ID, video=file_path, caption="📽️ Here is your video file!")
    else:
        await bot.send_document(chat_id=CHAT_ID, document=file_path, caption="📂 Here is your file!")

    await bot.stop()

# Telegram bot command handler
@bot.on_message(filters.command("start"))
def start_command(client: Client, message: Message):
    message.reply_text("✅ Bot is running! Send me a DropGalaxy link to download directly.")

# Telegram bot handler for DropGalaxy links
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

    await message.reply_text(f"✅ Direct link found! Downloading file...")

    file_path = download_file(direct_link)
    await send_file_to_telegram(file_path, message)

    await message.reply_text("✅ All files have been sent!")

if __name__ == "__main__":
    def run_flask():
        app.run(host="0.0.0.0", port=5000)

    Thread(target=run_flask).start()
    bot.run()
