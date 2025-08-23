import os
import json
import logging
from datetime import datetime, timedelta
import nest_asyncio
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ---------------- CONFIG ----------------
TOKEN = os.getenv("BOT_TOKEN")  # Render me environment variable set karo: BOT_TOKEN
GROUP_LINK = "https://t.me/campvoyzmoney"
DATA_FILE = "user_data.json"
PORT = int(os.environ.get("PORT", 5000))
URL = os.getenv("RENDER_EXTERNAL_URL")  # Render auto set karega

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------- FLASK ----------------
app = Flask(__name__)   # 👈 sabse pehle define karna

# ---------------- BOT APP ----------------
nest_asyncio.apply()
loop = asyncio.get_event_loop()
application = Application.builder().token(TOKEN).build()

# ---------------- DATA FUNCTIONS ----------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def clean_old_data():
    data = load_data()
    now = datetime.now()
    updated = {uid: info for uid, info in data.items() if datetime.fromisoformat(info["timestamp"]) > now - timedelta(days=30)}
    save_data(updated)

# ---------------- HANDLERS ----------------
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
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Ab apna phone number share kare.", reply_markup=reply_markup)

    elif "phone" not in data[user_id] and update.message.contact:
        data[user_id]["phone"] = update.message.contact.phone_number
        save_data(data)
        await update.message.reply_text(f"✅ Shukriya! Ye rahi group ki link:\n{GROUP_LINK}")

    else:
        await update.message.reply_text("Aap already register ho chuke ho. Group link: " + GROUP_LINK)

# ---------------- FLASK ROUTES ----------------
@app.post(f"/{TOKEN}")
async def webhook():
    """Telegram webhook endpoint"""
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)   # ✅ ab await kar raha hai
    return "ok", 200

@app.get("/")
def index():
    return "✅ Bot is running on Render!"

# ---------------- SETUP BOT ----------------
async def setup_bot():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ALL, handle_message))

    webhook_url = f"{URL}/{TOKEN}"
    await application.bot.set_webhook(webhook_url, drop_pending_updates=True)
    logger.info(f"✅ Webhook set to: {webhook_url}")

with app.app_context():
    loop.run_until_complete(setup_bot())
