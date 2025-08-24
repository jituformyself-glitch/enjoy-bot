import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from datetime import datetime

# ==============================
# ENV Variables
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")   # apna Telegram ID
GROUP_LINK = os.getenv("GROUP_LINK")
SHEET_NAME = os.getenv("SHEET_NAME")
CREDS_JSON = os.getenv("GOOGLE_SHEET_CREDS")

# ==============================
# Google Sheets Setup
# ==============================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds_dict = json.loads(CREDS_JSON)  # ENV se JSON load
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# ==============================
# Start Command
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

# ==============================
# Handle Messages
# ==============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    # Check agar user already sheet me hai
    records = sheet.get_all_records()
    user_record = next((r for r in records if str(r["UserID"]) == user_id), None)

    # Agar user sheet me nahi hai
    if not user_record:
        # Pahla message = Name
        sheet.append_row([user_id, text, "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        await update.message.reply_text("✅ Great! Ab apna **phone number** bhejo.")
        return

    # Agar user hai but phone empty hai
    if user_record and user_record["Phone"] == "":
        if update.message.contact:  # Agar contact bheja
            phone = update.message.contact.phone_number
        elif text.isdigit() and 10 <= len(text) <= 15:  # Agar manually bheja
            phone = text
        else:
            await update.message.reply_text("📱 Kripya sahi phone number bhejo.")
            return

        # Update phone number in sheet
        row_index = records.index(user_record) + 2  # row 1 header hoti hai
        sheet.update_cell(row_index, 3, phone)  # column 3 = Phone

        await update.message.reply_text(
            f"✅ Shukriya! Ye rahi group ki link:\n{GROUP_LINK}"
        )
        return

    # Agar already register ho chuka
    await update.message.reply_text("Aap already register ho chuke ho ✅\n\nGroup link: " + GROUP_LINK)

# ==============================
# Admin Command: /users
# ==============================
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
# Main Function
# ==============================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(MessageHandler(filters.TEXT | filters.CONTACT, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
