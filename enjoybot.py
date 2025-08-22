from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import logging
import json
from datetime import datetime, timedelta
import os
import asyncio
import nest_asyncio

# ---------------- CONFIG ----------------
TOKEN = os.getenv("BOT_TOKEN", "8082388693:AAH4j1DMEUbEiBCp6IPspxwVYI9HNQFEadw")
GROUP_LINK = "https://t.me/campvoyzmoney"
DATA_FILE = "user_data.json"
PORT = int(os.environ.get("PORT", 5000))
URL = os.getenv("RENDER_EXTERNAL_URL", "https://enjoy-bot.onrender.com")

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------------- FLASK APP ----------------
app = Flask(__name__)

# ---------------- GLOBAL APP ----------------
application: Application = None  # PTB Application global banaya

# ---------------- HELPER FUNCTIONS ----------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def clean_old_data():
    data = load_data()
    now = datetime.now()
    data = {
        k: v
        for k, v in data.items()
        if datetime.fromisoformat(v["timestamp"]) + timedelta(days=30) > now
    }
    save_data(data)

# ---------------- BOT HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        f"Agar aapko money offering group join karna hai toh pehle apna full name bheje."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text
    data = load_data()
    clean_old_data()

    if user_id not in data:
        data[user_id] = {"name": text, "timestamp": datetime.now().isoformat()}
        save_data(data)
        keyboard = [[KeyboardButton("📱 Share Phone Number", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        await update.message.reply_text("Ab apna phone number share kare.", reply_markup=reply_markup)

    elif "phone" not in data[user_id] and update.message.contact:
        data[user_id]["phone"] = update.message.contact.phone_number
        save_data(data)
        await update.message.reply_text(f"✅ Shukriya! Ye rahi group ki link:\n{GROUP_LINK}")

    else:
        await update.message.reply_text("Aap already register ho chuke ho. Group link: " + GROUP_LINK)

# ---------------- FLASK ROUTES ----------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global application
    if application is None:
        return "Application not ready", 500

    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    # PTB ke loop me bhejna
    asyncio.run_coroutine_threadsafe(application.process_update(update), application.loop)
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"

# ---------------- MAIN ----------------
if __name__ == "__main__":
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    nest_asyncio.apply()

    async def main():
        global application
        application = Application.builder().token(TOKEN).build()

        # Handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.ALL, handle_message))

        # Webhook set
        webhook_url = f"{URL}/{TOKEN}"
        await application.bot.set_webhook(webhook_url)
        print(f"Webhook set to: {webhook_url}")

        # Hypercorn config
        config = Config()
        config.bind = [f"0.0.0.0:{PORT}"]

        await serve(app, config)

    asyncio.run(main())
