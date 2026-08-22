from telegram import Update
from telegram.ext import ContextTypes

from database import add_reminder, get_pending_reminders


async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    text = update.message.text or ""
    content = text.partition(" ")[2].strip()

    if not content or "|" not in content:
        await update.message.reply_text(
            "⏰ فرمت:\n\n"
            "/reminder 2026-08-24T08:00 | تماس با علی"
        )
        return

    remind_at, reminder_text = content.split("|", 1)

    remind_at = remind_at.strip()
    reminder_text = reminder_text.strip()

    if not reminder_text:
        await update.message.reply_text(
            "متن یادآوری خالی است."
        )
        return

    reminder_id = add_reminder(
        update.effective_user.id,
        reminder_text,
        remind_at,
    )

    await update.message.reply_text(
        f"⏰ یادآوری ذخیره شد.\n"
        f"شناسه: {reminder_id}\n"
        f"زمان: {remind_at}"
    )


async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    reminders = get_pending_reminders(
        update.effective_user.id
    )

    if not reminders:
        await update.message.reply_text(
            "⏰ یادآوری فعالی نداری."
        )
        return

    lines = ["⏰ یادآوری‌های فعال:\n"]

    for reminder in reminders:
        lines.append(
            f"#{reminder['id']} — {reminder['remind_at']}\n"
            f"{reminder['text']}\n"
        )

    await update.message.reply_text(
        "\n".join(lines)
    )
