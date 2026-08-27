from telegram import Update
from telegram.ext import ContextTypes

from database import add_note, get_notes, delete_note


async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    text = update.message.text or ""
    content = text.partition(" ")[2].strip()

    if not content:
        await update.message.reply_text(
            "📝 برای ذخیره یادداشت:\n\n"
            "/note متن یادداشت"
        )
        return

    note_id = add_note(user_id, content)

    await update.message.reply_text(
        f"📝 یادداشت ذخیره شد.\nشناسه: {note_id}"
    )


async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    notes = get_notes(update.effective_user.id)

    if not notes:
        await update.message.reply_text(
            "📝 هنوز هیچ یادداشتی نداری."
        )
        return

    lines = ["📝 یادداشت‌های تو:\n"]

    for note in notes:
        lines.append(
            f"#{note['id']}\n"
            f"{note['content']}\n"
        )

    await update.message.reply_text("\n".join(lines))


async def delete_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    text = update.message.text or ""
    argument = text.partition(" ")[2].strip()

    if not argument.isdigit():
        await update.message.reply_text(
            "/delete_note 1"
        )
        return

    deleted = delete_note(
        update.effective_user.id,
        int(argument),
    )

    await update.message.reply_text(
        "🗑️ یادداشت حذف شد."
        if deleted
        else "این یادداشت پیدا نشد."
    )
