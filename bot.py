import os
import re
import urllib.parse
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = os.getenv("BOT_TOKEN") # Replace with your actual bot token

# Function to extract TeraBox ID
def extract_terabox_id(url):
    parsed_url = urllib.parse.urlparse(url)
    match = re.search(r"/s/([A-Za-z0-9_-]+)", parsed_url.path)
    if match:
        video_id = match.group(1)
        if video_id.startswith("1"):
            video_id = video_id[1:]
        return video_id
    return None

# Function to get the direct video link
def get_direct_video_link(url):
    video_id = extract_terabox_id(url)
    if video_id:
        return f"https://www.1024terabox.com/sharing/embed?surl={video_id}", video_id
    return None, None

# Telegram Bot Commands
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hey! Send me a TeraBox link to get the streaming link.")

# Handle messages with TeraBox links
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

async def main():
    app_telegram = Application.builder().token(TOKEN).build()

    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Starting Telegram bot...")
    await app_telegram.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
