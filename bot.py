import os
import requests
import re
import time
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

# Initialize Flask app
app = Flask(__name__)

# Get bot token from environment variables
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set. Please add it as an environment variable.")

# Function to bypass DropGalaxy and get the direct download link
def bypass_dropgalaxy(url):
    session = requests.Session()
    response = session.get(url)

    if response.status_code != 200:
        return "Error: Unable to access DropGalaxy"

    match = re.search(r'action="([^"]+)"', response.text)
    if not match:
        return "Error: No action URL found"

    action_url = match.group(1)

    match = re.search(r'name="op" value="([^"]+)"', response.text)
    if not match:
        return "Error: No operation key found"

    op_value = match.group(1)

    payload = {
        'op': op_value,
        'usr_login': '',
        'id': url.split("/")[-1],
        'fname': '',
        'referer': '',
        'method_free': 'Free Download'
    }

    time.sleep(5)  # Wait for the countdown timer
    post_response = session.post(action_url, data=payload)

    final_match = re.search(r'href="(https://[^"]+)"', post_response.text)
    if final_match:
        return final_match.group(1)
    else:
        return "Error: Direct link not found"

# Function to handle messages
async def handle_message(update: Update, context):
    text = update.message.text
    if "dropgalaxy" in text:
        await update.message.reply_text("Processing your link, please wait...")

        direct_link = bypass_dropgalaxy(text)

        if "Error" in direct_link:
            await update.message.reply_text(direct_link)
        else:
            await update.message.reply_text(f"✅ Here is your direct download link:\n{direct_link}")
    else:
        await update.message.reply_text("Please send a valid DropGalaxy link.")

# Flask Route for Uptime Monitoring
@app.route('/')
def home():
    return "Bot is running successfully!"

# Function to start the Telegram bot
async def run_bot():
    print("Initializing Telegram bot...")

    # Build the application without Updater
    app_telegram = Application.builder().token(TOKEN).build()

    # Add message handler
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    await app_telegram.run_polling(allowed_updates=Update.ALL_TYPES)

# Run the bot in a separate thread
def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# Start bot in background
threading.Thread(target=start_bot, daemon=True).start()

# Run Flask App
if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
