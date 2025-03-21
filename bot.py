import os
import time
import requests
import re
import asyncio
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
    
    response = session.get(url)
    if response.status_code != 200:
        return "❌ Error: Unable to access DropGalaxy."

    # Extract form action URL
    match = re.search(r'action="([^"]+)"', response.text)
    if not match:
        return "❌ Error: No action URL found."

    action_url = match.group(1)

    # Extract key parameter
    match = re.search(r'name="op" value="([^"]+)"', response.text)
    if not match:
        return "❌ Error: No operation key found."

    op_value = match.group(1)

    payload = {
        'op': op_value,
        'usr_login': '',
        'id': url.split("/")[-1],
        'fname': '',
        'referer': '',
        'method_free': 'Free Download'
    }

    # Submit the form to get the final download link
    time.sleep(5)  # Simulating the countdown timer
    post_response = session.post(action_url, data=payload)

    # Extract the final download URL
    final_match = re.search(r'href="(https://[^"]+)"', post_response.text)
    if final_match:
        return final_match.group(1)
    else:
        return "❌ Error: Direct download link not found."

# Telegram bot command handler
@bot.on_message(filters.command("start"))
def start_command(client: Client, message: Message):
    message.reply_text("✅ Bot is running! Send me a DropGalaxy link to bypass.")

# Telegram bot handler for DropGalaxy links
@bot.on_message(filters.text & ~filters.command(["start"]))
def handle_dropgalaxy(client: Client, message: Message):
    text = message.text.strip()

    if "dropgalaxy" in text:
        message.reply_text("⏳ Processing your DropGalaxy link, please wait...")
        
        direct_link = bypass_dropgalaxy(text)

        message.reply_text(f"✅ Here is your direct download link:\n{direct_link}")
    else:
        message.reply_text("⚠️ Please send a valid DropGalaxy link.")

if __name__ == "__main__":
    # Start Flask app for health check in a separate thread
    def run_flask():
        app.run(host="0.0.0.0", port=5000)

    Thread(target=run_flask).start()

    # Start the Telegram bot
    bot.run()
