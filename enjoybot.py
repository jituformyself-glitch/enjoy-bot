import json
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ==== CONFIG ====
TOKEN = "8082388693:AAH4j1DMEUbEiBCp6IPspxwVYI9HNQFEadw"
ADMIN_ID = 6364785460
GROUP_LINK = "https://t.me/campvoyzmoney"
DATA_FILE = "users_data.json"

# ==== States ====
ASK_NAME, ASK_PHONE = range(2)

# ==== Data Handling ====
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

users_data = load_data()
user_count = len(users_data)

# ==== Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}! 👋\n"
        "Agar aapko 'Money Offering Group' join karna hai toh pehle apna **Name** aur **Phone Number** register karna hoga.\n"
        "Don't worry, ye 100% secure hai ✅\n\n"
        "👉 Pehle apna *Name* bhejo."
    )
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Great 👍 Ab apna *Phone Number* bhejo:")
    return ASK_PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_count
    phone = update.message.text
    name = context.user_data.get("name")

    user_count += 1
    join_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    users_data[user_count] = {
        "name": name,
        "phone no.": phone,
        "joined_at": join_time
    }

    save_data(users_data)

    await update.message.reply_text(
        f"Thanks {name} ✅\nAap ab group join kar sakte ho 👇\n{GROUP_LINK}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancel kar diya gaya ❌")
    return ConversationHandler.END

# ==== Admin Only: Show Users ====
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Aap authorized nahi ho is command ke liye.")
        return

    if not users_data:
        await update.message.reply_text("⚠️ Abhi tak koi user join nahi hua.")
        return

    msg = "📋 Registered Users:\n\n"
    for num, data in users_data.items():
        msg += f"{num}. Name: {data['name']} | Phone: {data['phone no.']} | Joined: {data['joined_at']}\n"

    await update.message.reply_text(msg)

# ==== MAIN ====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("users", show_users))

    app.run_polling()

if __name__ == "__main__":
    main()
