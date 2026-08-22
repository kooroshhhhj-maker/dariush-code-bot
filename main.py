import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "من داریوش هستم؛ دستیار شخصی شما.\n\n"
        "فعلاً نسخه آزمایشی من فعال است.\n"
        "پیامت را بفرست تا باهات گفتگو کنم."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "دستورات فعلی:\n\n"
        "/start - شروع کار\n"
        "/help - راهنما\n"
        "/image - ساخت تصویر (به‌زودی)\n"
        "/note - یادداشت (به‌زودی)\n"
        "/reminder - یادآوری (به‌زودی)"
    )


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    await update.message.reply_text(
        f"پیامت دریافت شد ✅\n\n{text}\n\n"
        "🧠 موتور هوش مصنوعی در مرحله بعدی اضافه می‌شود."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"ERROR: {context.error}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN در فایل .env تنظیم نشده است."
        )

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat,
        )
    )

    app.add_error_handler(error_handler)

    print("Dariush Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
