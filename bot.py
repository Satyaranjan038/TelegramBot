import re
import urllib.parse
import logging
import asyncio
import requests
import os
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, 
    filters, CallbackContext
)

ADMIN_USER_ID = 973053041  # Set admin user ID

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Load environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Telegram Bot Token
MONGO_USERNAME = os.getenv("MONGO_USERNAME", "").strip()  # Ensure it's a string
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "").strip()  # Ensure it's a string
# Telegram Bot Token
response = requests.get("https://api64.ipify.org?format=json")
print("Server Public IP:", response.json()["ip"])

# URL encode MongoDB credentials
if not MONGO_USERNAME or not MONGO_PASSWORD:
    raise ValueError("MongoDB credentials are missing! Check environment variables.")

encoded_username = urllib.parse.quote_plus(str(MONGO_USERNAME))
encoded_password = urllib.parse.quote_plus(str(MONGO_PASSWORD))
MONGO_URI = f"mongodb+srv://{encoded_username}:{encoded_password}@cluster0.rzqy9ul.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client["terabox_bot"]
    likes_collection = db["likes"]
    favorites_collection = db["favorites"]
    video_links_collection = db["video_links"]
    logger.info("✅ Connected to MongoDB successfully.")
except Exception as e:
    logger.error(f"❌ MongoDB Connection Error: {e}")

# Extract TeraBox ID from URL
def extract_terabox_id(url):
    parsed_url = urllib.parse.urlparse(url)
    match = re.search(r"/s/([A-Za-z0-9_-]+)", parsed_url.path)

    if match:
        video_id = match.group(1)
        if video_id.startswith("1"):  # Remove extra "1" if present
            video_id = video_id[1:]
        return video_id

    return None  # No valid ID found

# Generate Direct Video Link
def get_direct_video_link(url):
    video_id = extract_terabox_id(url)
    if video_id:
        return f"https://filedownloaderbot-jzw6.onrender.com/stream?surl={video_id}", video_id
    return None, None

# Escape Markdown characters
def escape_markdown(text):
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join("\\" + char if char in escape_chars else char for char in text)

# /start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hey! Send me a TeraBox link to get the direct video link.")

# Handle messages with TeraBox links
async def handle_message(update: Update, context: CallbackContext):
    message_text = update.message.text.strip()
    user_id = update.effective_user.id  # Get user ID
    username = update.effective_user.username  # Get username
    display_name = update.effective_user.full_name  # Full name (first + last)

    logger.info(f"Received message from {user_id} ({display_name}): {message_text}")

    if any(domain in message_text for domain in ["terabox.com", "teraboxdownloader.pro", "terasharelink.com", "terafileshare.com"]):
        direct_link, video_id = get_direct_video_link(message_text)
        if direct_link:
            stream_link = direct_link
            keyboard = [
                [InlineKeyboardButton("🎬 Play Online", url=stream_link)],
                [InlineKeyboardButton("👍 Like", callback_data=f"like_{video_id}"),
                 InlineKeyboardButton("⭐ Favorite", callback_data=f"favorite_{video_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            escaped_text = escape_markdown(f"🎥 **Stream Video Online:**\n{stream_link}")

            await update.message.reply_text(
                escaped_text, reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
            logger.info(f"✅ Generated link for video: {video_id}")

            # Ensure no duplicate for the same user and video_id
            existing_entry = video_links_collection.find_one({"user_id": user_id, "video_id": video_id})
            
            if existing_entry:
                logger.info(f"❌ Video link for user {user_id} and video {video_id} already exists.")
            else:
                # Store stream link with user_id, username/display name in MongoDB
                video_links_collection.insert_one(
                    {"user_id": user_id, "video_id": video_id, "stream_link": stream_link, "username": username, "display_name": display_name}
                )

        else:
            await update.message.reply_text("❌ Invalid TeraBox link.")
    else:
        await update.message.reply_text("❌ Please send a valid TeraBox link.")



# Handle Like and Favorite button clicks
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id

    try:
        action, video_id = query.data.split("_", 1)
        stream_link_data = video_links_collection.find_one({"video_id": video_id})
        if not stream_link_data:
            await query.answer("❌ Error: Video not found in database.")
            return

        stream_link = stream_link_data["stream_link"]

        if action == "like":
            # Check if the user has already liked the video
            existing_like = likes_collection.find_one({"user_id": user_id, "video_id": video_id, "liked": True})
            if existing_like:
                await query.answer("❌ You have already liked this video.")
                return

            # Store the like if it's not already present
            likes_collection.update_one(
                {"user_id": user_id, "video_id": video_id},
                {"$set": {"liked": True, "stream_link": stream_link}},
                upsert=True
            )
            await query.answer("Liked! 👍")
            logger.info(f"✅ User {user_id} liked video {video_id}")

        elif action == "favorite":
            # Check if the user has already favorited the video
            existing_favorite = favorites_collection.find_one({"user_id": user_id, "video_id": video_id, "favorited": True})
            if existing_favorite:
                await query.answer("❌ You have already added this video to favorites.")
                return

            # Store the favorite if it's not already present
            favorites_collection.update_one(
                {"user_id": user_id, "video_id": video_id},
                {"$set": {"favorited": True, "stream_link": stream_link}},
                upsert=True
            )
            await query.answer("Added to Favorites! ⭐")
            logger.info(f"✅ User {user_id} added video {video_id} to favorites")

        await query.edit_message_reply_markup(reply_markup=None)

    except Exception as e:
        logger.error(f"❌ Error processing button click: {e}")
        await query.answer("Something went wrong. Please try again.")


# /like command - Show liked videos
async def like(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        likes = likes_collection.find({"user_id": user_id})
        response = "👍 **Your Liked Videos:**\n"
        response += "\n".join([f"- [Watch Here]({like['stream_link']})" for like in likes]) or "No liked videos yet."
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error fetching liked videos: {e}")
        await update.message.reply_text("Error retrieving your liked videos.")

# /favorite command - Show favorite videos
async def favorite(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        favorites = favorites_collection.find({"user_id": user_id})
        response = "⭐ **Your Favorite Videos:**\n"
        response += "\n".join([f"- [Watch Here]({fav['stream_link']})" for fav in favorites]) or "No favorite videos yet."
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error fetching favorite videos: {e}")
        await update.message.reply_text("Error retrieving your favorite videos.")

# /history command - Show liked and favorite videos
async def history(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        likes = list(likes_collection.find({"user_id": user_id}))
        favorites = list(favorites_collection.find({"user_id": user_id}))

        response = "📜 **Your Video History:**\n"
        if likes:
            response += "\n👍 **Liked Videos:**\n" + "\n".join([f"- [Watch Here]({like['stream_link']})" for like in likes])
        if favorites:
            response += "\n\n⭐ **Favorite Videos:**\n" + "\n".join([f"- [Watch Here]({fav['stream_link']})" for fav in favorites])

        await update.message.reply_text(response or "No history found.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error fetching history: {e}")
        await update.message.reply_text("Error retrieving your video history.")
# /myhistory command - Show user's streaming history
async def myhistory(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        # Fetch all video links stored for this user
        history = list(video_links_collection.find({"user_id": user_id}))

        if history:
            response = "📜 **Your Streaming History:**\n\n"
            response += "\n".join([f"- [Watch Here]({entry['stream_link']})" for entry in history])
        else:
            response = "No streaming history found."

        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error fetching history for user {user_id}: {e}")
        await update.message.reply_text("❌ Error retrieving your video history.")

async def admin_history(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ You are not an admin.")
        return

    try:
        # Fetch all stored video links
        history = list(video_links_collection.find({}))

        if history:
            response = "📜 **All User Streaming History:**\n\n"
            for entry in history:
                # Get user details (username or display name)
                user = update.effective_user
                display_name = user.username if user.username else f"{user.first_name} {user.last_name}"
                
                response += f"👤 User: `{display_name}` (User ID: `{entry['user_id']}`)\n"
                response += f"🎥 [Watch Here]({entry['stream_link']})\n\n"
        else:
            response = "No history found."

        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error fetching admin history: {e}")
        await update.message.reply_text("❌ Error retrieving video history.")


# Add Menu Button to show available commands

# Main function to run the bot
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("like", like))
    app.add_handler(CommandHandler("favorite", favorite))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("myhistory", myhistory))
    app.add_handler(CommandHandler("adminHistory", admin_history))
    #asyncio.get_event_loop().run_until_complete(set_bot_menu(app))
    logger.info("🤖 Bot is running...")
   
    app.run_polling()

# Run the bot
if __name__ == "__main__":
    main()
