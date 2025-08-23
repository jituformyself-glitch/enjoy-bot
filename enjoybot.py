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
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # Apna Telegram ID yaha env me set karna

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------- FLASK ----------------
app = Flask(__name__)

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
    """30 din se purane users ko delete karo"""
    data = load_data()
    now = datetime.now()
    updated = {
        uid: info
        for uid, info in data.items()
        if datetime.fromisoformat(info["timestamp"]) > now - timedelta(days=30)
    }
    if len(updated) != len(data):
        save_data(updated)
    return updated

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

    if user_id not in data and not update.message.contact:
        # Save name
        data[user_id] = {"name": text, "timestamp": datetime.now().isoformat()}
        save_data(data)

        # Ask for phone number
        keyboard = [[KeyboardButton("📱 Share Phone Number", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        await update.message.reply_text("Ab apna phone number share kare.", reply_markup=reply_markup)

    elif "phone" not in data[user_id] and update.message.contact:
        # Save phone
        data[user_id]["phone"] = update.message.contact.phone_number
        save_data(data)
        await update.message.reply_text(f"✅ Shukriya! Ye rahi group ki link:\n{GROUP_LINK}")

    else:
        await update.message.reply_text("Aap already register ho chuke ho. Group link: " + GROUP_LINK)

# ---------------- ADMIN COMMAND ----------------
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Permission denied. Ye command sirf admin ke liye hai.")
        return

    data = clean_old_data()
    if not data:
        await update.message.reply_text("⚠️ Abhi tak koi active user register nahi hai.")
        return

    msg = "📋 Registered Users (last 30 days):\n\n"
    for uid, info in data.items():
        name = info.get("name", "❌ No Name")
        phone = info.get("phone", "❌ No Phone")
        time = info.get("timestamp", "")
        msg += f"👤 {name}\n📱 {phone}\n🕒 {time}\n\n"

    await update.message.reply_text(msg)

# ---------------- FLASK ROUTES ----------------
@app.post(f"/{TOKEN}")
async def webhook():
    """Telegram webhook endpoint"""
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok", 200

@app.get("/")
def index():
    return "✅ Bot is running on Render!"

# ---------------- SETUP BOT ----------------
async def setup_bot():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", list_users))  # admin only
    application.add_handler(MessageHandler(filters.ALL, handle_message))

    await application.initialize()
    await application.start()

    webhook_url = f"{URL}/{TOKEN}"
    await application.bot.set_webhook(webhook_url, drop_pending_updates=True)
    logger.info(f"✅ Webhook set to: {webhook_url}")

with app.app_context():
    loop.run_until_complete(setup_bot())
