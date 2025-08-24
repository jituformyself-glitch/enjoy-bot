import os
import json
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from quart import Quart, request
from datetime import datetime

# ==============================
# ENV Variables
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
GROUP_LINK = os.getenv("GROUP_LINK")
SHEET_ID = os.getenv("SHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
PUBLIC_URL = os.getenv("PUBLIC_URL")  # e.g. https://enjoy-bot.onrender.com
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"  # unique path per bot

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
bot = telegram_app.bot  # convenience

# ==============================
# Handlers
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        "Agar aapko *MONEY OFFERING GROUP* join karna hai toh phale apna "
        "**FULL NAME** aur **PHONE NUMBER** register karna hoga.\n\n"
        "Don't worry, ye 1000% secure hai ✅\n\n"
        "👉 Phela apna **full name** bhejo."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = str(update.effective_user.id)
    text = update.message.text or ""

    # Existing records
    records = sheet.get_all_records()
    user_record = next((r for r in records if str(r.get("UserID")) == user_id), None)

    # New user -> store name, empty phone
    if not user_record:
        sheet.append_row([user_id, text, "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        await update.message.reply_text("✅ Great! Ab apna **phone number** bhejo.")
        return

    # Phone number missing -> accept contact or digits
    if user_record and (user_record.get("Phone") == "" or user_record.get("Phone") is None):
        if update.message.contact:
            phone = update.message.contact.phone_number
        elif text.isdigit() and 10 <= len(text) <= 15:
            phone = text
        else:
            await update.message.reply_text("📱 Kripya sahi phone number bhejo.")
            return

        row_index = records.index(user_record) + 2  # +1 header, +1 1-indexed
        sheet.update_cell(row_index, 3, phone)
        await update.message.reply_text(f"✅ Shukriya! Ye rahi group ki link:\n{GROUP_LINK}")
        return

    # Already registered
    await update.message.reply_text("Aap already register ho chuke ho ✅\n\nGroup link: " + GROUP_LINK)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ Aap is command ke liye authorized nahi ho.")
        return

    records = sheet.get_all_records()
    if not records:
        await update.message.reply_text("⚠️ Abhi koi user register nahi hai.")
        return

    msg = "📋 Registered Users:\n\n"
    for r in records:
        msg += f"👤 {r.get('Name','-')} | 📱 {r.get('Phone','-')} | 📅 {r.get('Date','-')}\n"

    await update.message.reply_text(msg)

# Register handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("users", users))
telegram_app.add_handler(MessageHandler(filters.TEXT | filters.CONTACT, handle_message))

# ==============================
# Quart App (ASGI) for Webhook
# ==============================
app = Quart(__name__)

@app.before_serving
async def on_startup():
    # Start PTB without polling; just initialize runtime
    await telegram_app.initialize()
    await telegram_app.start()

    # Auto-set webhook if PUBLIC_URL provided
    if PUBLIC_URL:
        url = PUBLIC_URL.rstrip("/") + WEBHOOK_PATH
        await bot.set_webhook(url=url)
        print(f"✅ Webhook set to: {url}")

@app.after_serving
async def on_shutdown():
    # Keep webhook or delete (optional). Here we keep it.
    # await bot.delete_webhook(drop_pending_updates=False)
    await telegram_app.stop()
    await telegram_app.shutdown()

@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    data = await request.get_json()
    if not data:
        return "bad request", 400
    update = Update.de_json(data, bot)
    # Directly process update (no internal fetcher/queue) -> avoids pending task errors
    await telegram_app.process_update(update)
    return "ok", 200

# Health check
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ==============================
# Local dev entry (Render runs via start command)
# ==============================
if __name__ == "__main__":
    import asyncio
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:" + os.getenv("PORT", "8000")]
    asyncio.run(hypercorn.asyncio.serve(app, config))
