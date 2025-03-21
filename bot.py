import os
import requests
import re
import time
import threading
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, Dispatcher

# Initialize Flask app
app = Flask(__name__)

# Telegram bot token (Replace with your actual bot token)
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
bot = Bot(token=TOKEN)

# Function to bypass DropGalaxy and get the direct download link
def bypass_dropgalaxy(url):
    session = requests.Session()

    # Visit the initial page
    response = session.get(url)
    if response.status_code != 200:
        return "Error: Unable to access DropGalaxy"

    # Extract form data for redirect
    match = re.search(r'action="([^"]+)"', response.text)
    if not match:
        return "Error: No action URL found"

    action_url = match.group(1)

    # Extract key parameter
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

    # Submit the form to get the final download link
    time.sleep(5)  # Wait for the countdown timer
    post_response = session.post(action_url, data=payload)

    # Extract the final download URL
    final_match = re.search(r'href="(https://[^"]+)"', post_response.text)
    if final_match:
        return final_match.group(1)
    else:
        return "Error: Direct link not found"

# Function to handle messages
def handle_message(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if "dropgalaxy" in text:
        update.message.reply_text("Processing your link, please wait...")

        direct_link = bypass_dropgalaxy(text)

        if "Error" in direct_link:
            update.message.reply_text(direct_link)
        else:
            update.message.reply_text(f"✅ Here is your direct download link:\n{direct_link}")
    else:
        update.message.reply_text("Please send a valid DropGalaxy link.")

# Flask Route for Uptime Monitoring
@app.route('/')
def home():
    return "Bot is running successfully!"

# Function to start the Telegram bot
def run_bot():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

# Run the bot in a separate thread
threading.Thread(target=run_bot).start()

# Run Flask App
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
