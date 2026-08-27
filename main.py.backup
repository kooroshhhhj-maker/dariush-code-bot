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
from database import (
    init_db,
    upsert_user,
    save_message,
    get_recent_messages,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if user:
        upsert_user(
            user.id,
            username=user.username,
            first_name=user.first_name,
        )

    await update.message.reply_text(
        "سلام 👋\n\n"
        "من داریوش هستم، دستیار شخصی شما. 🤖\n\n"
        "هر چیزی می‌خواهی بنویس."
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
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
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    user_message = update.message.text

    if not user_message:
        return

    try:
        await update.message.chat.send_action("typing")

        # ثبت / به‌روزرسانی کاربر
        upsert_user(
            user.id,
            username=user.username,
            first_name=user.first_name,
        )

        # ذخیره پیام کاربر
        save_message(
            user.id,
            "user",
            user_message,
        )

        # گرفتن تاریخچه مکالمه
        history_rows = get_recent_messages(
            user.id,
            limit=20,
        )

        # تبدیل تاریخچه SQLite به ساختار مورد نیاز AI
        messages = [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in history_rows
        ]

        # ارسال مکالمه به AI
        answer = chat(
            user_message,
            messages=messages,
        )

        # ذخیره پاسخ داریوش
        save_message(
            user.id,
            "assistant",
            answer,
        )

        await update.message.reply_text(answer)

    except Exception as error:
        print(f"AI ERROR: {error}")

        await update.message.reply_text(
            "متأسفانه فعلاً نتونستم پاسخ بدم. "
            "دوباره امتحان کن."
        )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print(f"BOT ERROR: {context.error}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    # ساخت جداول دیتابیس در صورت نبودن
    init_db()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

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
