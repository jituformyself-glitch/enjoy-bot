from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import logging
import json
from datetime import datetime, timedelta
import os
import asyncio

# -------------------- CONFIG --------------------
TOKEN = "8082388693:AAH4j1DMEUbEiBCp6IPspxwVYI9HNQFEadw"
GROUP_LINK = "https://t.me/joinchat/YourGroupLinkHere"
DATA_FILE = "user_data.json"
ADMIN_ID = "YOUR_TELEGRAM_ID"  # sirf aap check karne ke liye
PORT = int(os.environ.get("PORT", 5000))

# -------------------- LOGGING --------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# -------------------- FLASK APP --------------------
app = Flask(__name__)

# -------------------- TELEGRAM BOT --------------------
application = ApplicationBuilder().token(TOKEN).build()

# -------------------- HELPER FUNCTIONS --------------------
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
    data = {k: v for k, v in data.items() if datetime.fromisoformat(v['timestamp']) + timedelta(days=30) > now}
    save_data(data)

# -------------------- BOT HANDLERS --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(
        f"Hello {user.first_name}! Agar aapko money offering group join karna hai, toh pehle apna full name bheje."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_data()
    clean_old_data()

    if user_id not in data and update.message.text:
        # Save name
        data[user_id] = {"name": update.message.text, "timestamp": datetime.now().isoformat()}
        save_data(data)

        # Ask phone
        keyboard = [[KeyboardButton("Share Phone Number", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Ab apna phone number share kare.", reply_markup=reply_markup)

    elif user_id in data and 'phone' not in data[user_id] and update.message.contact:
        # Save phone
        data[user_id]['phone'] = update.message.contact.phone_number
        save_data(data)

        # Send group link
        await update.message.reply_text(f"Shukriya! Yaha aapka group link hai:\n{GROUP_LINK}")

    else:
        await update.message.reply_text("Already registered. Group link: " + GROUP_LINK)

# -------------------- REGISTER HANDLERS --------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT | filters.CONTACT, handle_message))

# -------------------- WEBHOOK --------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.create_task(application.process_update(update))
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

# -------------------- MAIN --------------------
if __name__ == "__main__":
    print("Starting bot with Flask + Webhook...")
    app.run(host="0.0.0.0", port=PORT)
