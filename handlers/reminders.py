from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    add_reminder,
    get_pending_reminders,
    get_reminder,
    set_reminder_daily,
    delete_reminder,
)


def reminders_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📋 My Reminders",
                callback_data="reminders:list",
            ),
            InlineKeyboardButton(
                "➕ New Reminder",
                callback_data="reminders:new",
            ),
        ]
    ])


def reminder_actions(reminder_id, daily):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔕 Daily OFF" if daily else "🔔 Daily ON",
                callback_data=f"reminders:daily:{reminder_id}",
            ),
            InlineKeyboardButton(
                "🗑️ Delete",
                callback_data=f"reminders:delete:{reminder_id}",
            ),
        ]
    ])


def date_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data="reminders:date:0",
            ),
            InlineKeyboardButton(
                "📅 Tomorrow",
                callback_data="reminders:date:1",
            ),
        ],
        [
            InlineKeyboardButton(
                "📅 In 2 Days",
                callback_data="reminders:date:2",
            ),
        ],
        [
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data="reminders:cancel",
            ),
        ],
    ])


def time_menu():
    times = [
        "08:00",
        "10:00",
        "12:00",
        "14:00",
        "18:00",
        "20:00",
        "22:00",
    ]

    buttons = []

    for i in range(0, len(times), 2):
        row = []

        for time_value in times[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    time_value,
                    callback_data=f"reminders:time:{time_value}",
                )
            )

        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            "❌ Cancel",
            callback_data="reminders:cancel",
        )
    ])

    return InlineKeyboardMarkup(buttons)


async def reminder_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.effective_user or not update.message:
        return

    context.user_data["reminders_mode"] = "text"

    await update.message.reply_text(
        "⏰ New Reminder\n\n"
        "Send the reminder text.\n\n"
        "Example:\n"
        "Call Ali"
    )


async def reminders_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.effective_user or not update.message:
        return

    await update.message.reply_text(
        "⏰ Reminders",
        reply_markup=reminders_menu(),
    )


async def reminders_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query or not update.effective_user:
        return

    await query.answer()

    user_id = update.effective_user.id
    action = query.data or ""

    if action == "reminders:list":
        reminders = get_pending_reminders(user_id)

        if not reminders:
            await query.edit_message_text(
                "⏰ You do not have any active reminders.",
                reply_markup=reminders_menu(),
            )
            return

        await query.edit_message_text(
            "⏰ Your active reminders:"
        )

        for reminder in reminders:
            reminder_id = reminder["id"]

            full_reminder = get_reminder(
                user_id,
                reminder_id,
            )

            if not full_reminder:
                continue

            daily = bool(full_reminder["daily"])

            await query.message.reply_text(
                f"#{reminder_id}\n"
                f"🕐 {reminder['remind_at']}\n"
                f"📝 {reminder['text']}",
                reply_markup=reminder_actions(
                    reminder_id,
                    daily,
                ),
            )

        return

    if action == "reminders:new":
        context.user_data["reminders_mode"] = "text"

        await query.edit_message_text(
            "➕ New Reminder\n\n"
            "Send the reminder text."
        )

        return

    if action.startswith("reminders:date:"):
        try:
            days = int(action.split(":")[-1])
        except ValueError:
            await query.answer(
                "Invalid date.",
                show_alert=True,
            )
            return

        base_date = datetime.now().date()
        selected_date = base_date + timedelta(days=days)

        context.user_data["reminder_date"] = selected_date.isoformat()
        context.user_data["reminders_mode"] = "time"

        await query.edit_message_text(
            f"📅 Date selected: {selected_date.isoformat()}\n\n"
            "Choose a time:",
            reply_markup=time_menu(),
        )

        return

    if action.startswith("reminders:time:"):
        time_value = action.split(":", 2)[-1]

        reminder_date = context.user_data.get(
            "reminder_date"
        )

        reminder_text = context.user_data.get(
            "reminder_text"
        )

        if not reminder_date or not reminder_text:
            await query.answer(
                "Reminder data is missing.",
                show_alert=True,
            )
            return

        remind_at = f"{reminder_date}T{time_value}:00"

        reminder_id = add_reminder(
            user_id,
            reminder_text,
            remind_at,
        )

        context.user_data["reminders_mode"] = None
        context.user_data.pop("reminder_date", None)
        context.user_data.pop("reminder_text", None)

        await query.edit_message_text(
            "✅ Reminder saved.\n\n"
            f"📝 {reminder_text}\n"
            f"🕐 {remind_at}",
            reply_markup=reminders_menu(),
        )

        return

    if action.startswith("reminders:daily:"):
        try:
            reminder_id = int(
                action.split(":")[-1]
            )
        except ValueError:
            await query.answer(
                "Invalid reminder.",
                show_alert=True,
            )
            return

        reminder = get_reminder(
            user_id,
            reminder_id,
        )

        if not reminder:
            await query.answer(
                "Reminder not found.",
                show_alert=True,
            )
            return

        new_value = not bool(reminder["daily"])

        set_reminder_daily(
            user_id,
            reminder_id,
            new_value,
        )

        await query.edit_message_reply_markup(
            reply_markup=reminder_actions(
                reminder_id,
                new_value,
            )
        )

        await query.answer(
            "Daily schedule enabled."
            if new_value
            else "Daily schedule disabled."
        )

        return

    if action.startswith("reminders:delete:"):
        try:
            reminder_id = int(
                action.split(":")[-1]
            )
        except ValueError:
            await query.answer(
                "Invalid reminder.",
                show_alert=True,
            )
            return

        deleted = delete_reminder(
            user_id,
            reminder_id,
        )

        if deleted:
            await query.edit_message_text(
                "🗑️ Reminder deleted.",
                reply_markup=reminders_menu(),
            )
        else:
            await query.answer(
                "Reminder not found.",
                show_alert=True,
            )

        return

    if action == "reminders:cancel":
        context.user_data["reminders_mode"] = None
        context.user_data.pop("reminder_date", None)
        context.user_data.pop("reminder_text", None)

        await query.edit_message_text(
            "❌ Reminder creation cancelled.",
            reply_markup=reminders_menu(),
        )


async def handle_reminder_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message or not update.effective_user:
        return False

    mode = context.user_data.get(
        "reminders_mode"
    )

    if mode == "text":
        content = (update.message.text or "").strip()

        if not content:
            await update.message.reply_text(
                "Please send a non-empty reminder."
            )
            return True

        context.user_data["reminder_text"] = content
        context.user_data["reminders_mode"] = "date"

        await update.message.reply_text(
            "📅 Choose the reminder date:",
            reply_markup=date_menu(),
        )

        return True

    return False
