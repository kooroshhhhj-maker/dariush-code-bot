from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN
from ai_client import chat


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n\n"
        "من داریوش هستم، دستیار شخصی شما. 🤖\n\n"
        "هر چیزی می‌خواهی بنویس."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "دستورات داریوش:\n\n"
        "/start — شروع\n"
        "/help — راهنما\n"
        "/image — ساخت تصویر\n"
        "/note — یادداشت\n"
        "/reminder — یادآوری"
    )


async def chat_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_message = update.message.text

    try:
        await update.message.chat.send_action("typing")

        answer = chat(user_message)

        await update.message.reply_text(answer)

    except Exception as error:
        print(f"AI ERROR: {error}")

        await update.message.reply_text(
            "متأسفانه فعلاً نتونستم پاسخ بدم. دوباره امتحان کن."
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"BOT ERROR: {context.error}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat_handler,
        )
    )

    app.add_error_handler(error_handler)

    print("Dariush AI Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
