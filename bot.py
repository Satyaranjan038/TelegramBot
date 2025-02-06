import re
import os
import urllib.parse
import requests
import asyncio
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = os.getenv("BOT_TOKEN") # Replace with your actual bot token


# Function to extract the correct TeraBox ID
def extract_terabox_id(url):
    parsed_url = urllib.parse.urlparse(url)
    match = re.search(r"/s/([A-Za-z0-9_-]+)", parsed_url.path)

    if match:
        video_id = match.group(1)
        if video_id.startswith("1"):  # Remove extra "1" if present
            video_id = video_id[1:]
        return video_id

    return None  # No valid ID found

# Function to get the direct video link
def get_direct_video_link(url):
    video_id = extract_terabox_id(url)
    if video_id:
        return f"https://www.1024terabox.com/sharing/embed?surl={video_id}", video_id
    return None, None  # Return None if invalid URL

# Function to get the video thumbnail
def get_video_thumbnail(video_id):
    return f"https://www.1024terabox.com/sharing/preview/surl/{video_id}.jpg"

# Function to download the image
def download_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return BytesIO(response.content)  # Convert image to bytes
    except Exception as e:
        print(f"Error downloading image: {e}")
    return None  # Return None if failed

# Command to start the bot
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hey! I am alive. Send me a TeraBox link to get the direct video link.")

# Message handler for extracting and sending video links
async def handle_message(update: Update, context: CallbackContext):
    message_text = update.message.text.strip()

    if "terabox.com" in message_text or "teraboxdownloader.pro" in message_text or "terasharelink.com" in message_text:
        direct_link, video_id = get_direct_video_link(message_text)

        if direct_link:
            stream_link = f"https://filedownloaderbot-jzw6.onrender.com/stream?surl={video_id}"  # Replace with your actual Flask URL

            keyboard = [[InlineKeyboardButton("🎬 Play Online", url=stream_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"🎥 **Stream Video Online:**\n{stream_link}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Invalid TeraBox link. Please check and try again.")
    else:
        await update.message.reply_text("❌ Please send a valid TeraBox link.")


# Main function to run the bot
def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    print("Bot is running...")
    app.run_polling()
    

if __name__ == "__main__":
    asyncio.run(main())
