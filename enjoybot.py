import os
import json
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from flask import Flask, request
from datetime import datetime

# ==============================
# ENV Variables
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
GROUP_LINK = os.getenv("GROUP_LINK")
SHEET_ID = os.getenv("SHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# ==============================
# Google Sheets Setup
# ==============================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    creds_dict = json.loads(base64.b64decode(CREDS_JSON).decode("utf-8"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    print("✅ Google Sheets connected successfully!")
except Exception as e:
    raise ValueError(f"❌ Google Sheets setup failed: {e}")

# ==============================
# Telegram Bot Setup
# ==============================
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot = telegram_app.bot

# ==============================
# Handlers
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        "Agar aapko *MONEY OFFERING GROUP* join karna hai toh phale apna "
        "**FULL NAME** aur **PHONE NUMBER** register karna hoga.\n\n"
        "Don't worry, ye 1000% secure hai ✅\n\n"
        "👉 Phela apna **full name** bhejo."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    records = sheet.get_all_records()
    user_record = next((r for r in records if str(r["UserID"]) == user_id), None)

    if not user_record:
        sheet.append_row([user_id, text, "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        await update.message.reply_text("✅ Great! Ab apna **phone number** bhejo.")
        return

    if user_record and user_record["Phone"] == "":
        if update.message.contact:
            phone = update.message.contact.phone_number
        elif text.isdigit() and 10 <= len(text) <= 15:
            phone = text
        else:
            await update.message.reply_text("📱 Kripya sahi phone number bhejo.")
            return

        row_index = records.index(user_record) + 2
        sheet.update_cell(row_index, 3, phone)
        await update.message.reply_text(f"✅ Shukriya! Ye rahi group ki link:\n{GROUP_LINK}")
        return

    await update.message.reply_text("Aap already register ho chuke ho ✅\n\nGroup link: " + GROUP_LINK)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ Aap is command ke liye authorized nahi ho.")
        return

    records = sheet.get_all_records()
    if not records:
        await update.message.reply_text("⚠️ Abhi koi user register nahi hai.")
        return

    msg = "📋 Registered Users:\n\n"
    for r in records:
        msg += f"👤 {r['Name']} | 📱 {r['Phone']} | 📅 {r['Date']}\n"

    await update.message.reply_text(msg)

# ==============================
# Flask App for Webhook
# ==============================
flask_app = Flask(__name__)

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(), bot)
    await telegram_app.update_queue.put(update)
    return "ok"

# ==============================
# Register Handlers
# ==============================
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("users", users))
telegram_app.add_handler(MessageHandler(filters.TEXT | filters.CONTACT, handle_message))

# ==============================
# Entry Point
# ==============================
if __name__ == "__main__":
    import asyncio
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:" + os.getenv("PORT", "8000")]
    asyncio.run(hypercorn.asyncio.serve(flask_app, config))
