import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    BusinessConnectionHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN
from ai_client import chat
from image_generator import (
    generate_image,
    generate_pixel_art,
)

from database import (
    init_db,
    upsert_user,
    save_message,
    get_recent_messages,
    get_notes,
    get_pending_reminders,
    get_daily_reminders,
    get_due_daily_reminders,
    complete_reminder,
    advance_daily_reminder,
    get_due_scheduled_notes,
    mark_note_schedule_completed,
    get_business_connection,
    set_business_auto_reply,
)

from handlers.notes import (
    note_command,
    notes_command,
    delete_note_command,
    notes_callback,
    handle_note_text,
)

from handlers.reminders import (
    reminder_command,
    reminders_command,
    reminders_callback,
    handle_reminder_text,
)

from handlers.business import (
    handle_business_connection,
    handle_business_message,
)


# =========================
# Main Keyboard
# =========================

def main_keyboard():
    keyboard = [
        [
            KeyboardButton("🤖 Dariush AI"),
        ],
        [
            KeyboardButton("📝 Notes"),
            KeyboardButton("⏰ Reminders"),
        ],
        [
            KeyboardButton("🎨 Create Image"),
        ],
        [
            KeyboardButton("📰 Post Maker"),
            KeyboardButton("🕹️ Pixel Art"),
        ],
        [
            KeyboardButton("👤 User Panel"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )


# =========================
# /start
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.effective_user or not update.message:
        return

    user = update.effective_user

    upsert_user(
        user.id,
        username=user.username,
        first_name=user.first_name,
    )

    await update.message.reply_text(
        "Hello 👋\n\n"
        "I'm Dariush, your personal assistant and smart secretary. 🤖\n\n"
        "Use the buttons below or send me a message directly.",
        reply_markup=main_keyboard(),
    )


# =========================
# Help
# =========================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    await update.message.reply_text(
        "🤖 Dariush Help\n\n"
        "/start — Main menu\n"
        "/help — Help\n"
        "/note — Save a note\n"
        "/notes — Show notes\n"
        "/delete_note — Delete a note\n"
        "/reminder — Create a reminder\n"
        "/reminders — Show active reminders",
        reply_markup=main_keyboard(),
    )


# =========================
# User Panel
# =========================

async def user_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    user_id = user.id

    notes = get_notes(user_id)
    reminders = get_pending_reminders(user_id)

    username = (
        f"@{user.username}"
        if user.username
        else "Not set"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💼 Business Auto Reply",
                callback_data="business:panel",
            )
        ]
    ]

    await update.message.reply_text(
        "👤 User Panel\n\n"
        f"Name: {user.first_name or 'Unknown'}\n"
        f"Username: {username}\n\n"
        f"📝 Notes: {len(notes)}\n"
        f"⏰ Active reminders: {len(reminders)}\n\n"
        "💼 Business Auto Reply\n"
        "Tap the button below to manage it.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def business_panel_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None or query.from_user is None:
        return

    await query.answer()

    user_id = query.from_user.id

    from database import get_connection

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT connection_id, enabled
            FROM business_connections
            WHERE owner_user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()

    if not rows:
        await query.edit_message_text(
            "💼 Business Auto Reply\n\n"
            "No Telegram Business connection was found "
            "for this account yet.\n\n"
            "Connect the bot to your Telegram Business "
            "account first."
        )
        return

    connection_id = rows[0]["connection_id"]
    enabled = bool(rows[0]["enabled"])

    if enabled:
        button_text = "🔴 Turn OFF Auto Reply"
        status = "🟢 ON"
    else:
        button_text = "🟢 Turn ON Auto Reply"
        status = "🔴 OFF"

    keyboard = [
        [
            InlineKeyboardButton(
                button_text,
                callback_data=(
                    "business:off"
                    if enabled
                    else "business:on"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Refresh",
                callback_data="business:panel",
            )
        ],
    ]

    await query.edit_message_text(
        "💼 Business Auto Reply\n\n"
        f"Status: {status}\n\n"
        "When ON, the bot automatically replies to "
        "customers.\n"
        "Messages sent by the account owner are always ignored.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def business_toggle_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None or query.from_user is None:
        return

    await query.answer()

    user_id = query.from_user.id

    from database import get_connection

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT connection_id, enabled
            FROM business_connections
            WHERE owner_user_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        await query.edit_message_text(
            "❌ Business connection not found."
        )
        return

    connection_id = row["connection_id"]
    new_enabled = not bool(row["enabled"])

    set_business_auto_reply(
        connection_id,
        new_enabled,
    )

    status = "🟢 ON" if new_enabled else "🔴 OFF"

    button_text = (
        "🔴 Turn OFF Auto Reply"
        if new_enabled
        else "🟢 Turn ON Auto Reply"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                button_text,
                callback_data=(
                    "business:off"
                    if new_enabled
                    else "business:on"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Refresh",
                callback_data="business:panel",
            )
        ],
    ]

    await query.edit_message_text(
        "💼 Business Auto Reply\n\n"
        f"Status: {status}\n\n"
        "Messages from the account owner are always ignored.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# Image Generation
# =========================

async def image_prompt_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    prompt = (update.message.text or "").strip()

    if not prompt:
        return

    import asyncio

    status = await update.message.reply_text(
        "🎨 Creating image."
    )

    context.user_data["mode"] = None

    stop_animation = asyncio.Event()

    async def animate():
        frames = [
            "🎨 Creating image.",
            "🎨 Creating image..",
            "🎨 Creating image...",
            "🧠 Processing prompt...",
            "⚡ Rendering image...",
            "🖼️ Generating pixels...",
            "✨ Almost done...",
        ]

        index = 0

        while not stop_animation.is_set():
            try:
                await status.edit_text(frames[index % len(frames)])
            except Exception:
                pass

            index += 1

            try:
                await asyncio.wait_for(
                    stop_animation.wait(),
                    timeout=0.8,
                )
            except asyncio.TimeoutError:
                pass

    animation_task = asyncio.create_task(animate())

    try:
        image_path = await asyncio.to_thread(
            generate_image,
            prompt,
        )

        stop_animation.set()
        await animation_task

        try:
            await status.delete()
        except Exception:
            pass

        with open(image_path, "rb") as image_file:
            await update.message.reply_photo(
                photo=image_file,
                caption="✨ Image created successfully.",
            )

    except Exception as error:
        stop_animation.set()

        try:
            await animation_task
        except Exception:
            pass

        print(f"IMAGE ERROR: {error}")

        try:
            await status.edit_text(
                "❌ Image generation failed. Please try again."
            )
        except Exception:
            await update.message.reply_text(
                "❌ Image generation failed. Please try again."
            )


async def pixel_art_prompt_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    prompt = (update.message.text or "").strip()

    if not prompt:
        return

    import asyncio

    status = await update.message.reply_text(
        "🕹️ Creating Pixel Art."
    )

    context.user_data["mode"] = None

    stop_animation = asyncio.Event()

    async def animate():
        frames = [
            "🕹️ Creating Pixel Art.",
            "🕹️ Creating Pixel Art..",
            "🕹️ Creating Pixel Art...",
            "🎨 Processing pixel style...",
            "🧱 Building pixel composition...",
            "⚡ Rendering pixels...",
            "✨ Almost done...",
        ]

        index = 0

        while not stop_animation.is_set():
            try:
                await status.edit_text(
                    frames[index % len(frames)]
                )
            except Exception:
                pass

            index += 1

            try:
                await asyncio.wait_for(
                    stop_animation.wait(),
                    timeout=0.8,
                )
            except asyncio.TimeoutError:
                pass

    animation_task = asyncio.create_task(animate())

    try:
        image_path = await asyncio.to_thread(
            generate_pixel_art,
            prompt,
        )

        stop_animation.set()
        await animation_task

        try:
            await status.delete()
        except Exception:
            pass

        with open(image_path, "rb") as image_file:
            try:
                await update.message.reply_photo(
                    photo=image_file,
                    caption="🕹️ Pixel Art created successfully.",
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=30,
                    pool_timeout=30,
                )
            except Exception as send_error:
                print(
                    f"PIXEL ART TELEGRAM SEND ERROR: "
                    f"{type(send_error).__name__}: {send_error}"
                )
                await update.message.reply_text(
                    "⚠️ تصویر ساخته شد، اما ارسال آن به تلگرام "
                    "زمان زیادی برد. دوباره تلاش کنید."
                )

    except Exception as error:
        stop_animation.set()

        try:
            await animation_task
        except Exception:
            pass

        print(f"PIXEL ART ERROR: {type(error).__name__}: {error}")
        import traceback
        traceback.print_exc()

        try:
            await status.edit_text(
                "❌ Pixel Art generation failed. Please try again."
            )
        except Exception:
            await update.message.reply_text(
                "❌ Pixel Art generation failed. Please try again."
            )


# =========================
# Menu Actions
# =========================


async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    text = update.message.text

    if text == "🤖 Dariush AI":
        await update.message.reply_text(
            "🤖 Chat mode is active.\n\n"
            "Send me a message."
        )

    elif text == "📝 Notes":
        await notes_command(update, context)

    elif text == "⏰ Reminders":
        await reminders_command(update, context)

    elif text == "🎨 Create Image":
        context.user_data["mode"] = "image"

        await update.message.reply_text(
            "🎨 Image mode enabled.\n\n"
            "Send me your image prompt."
        )

    elif text == "📰 Post Maker":
        context.user_data["mode"] = "post_maker"
        await update.message.reply_text(
            "📰 Post Maker enabled.\n\n"
            "Forward me a post or send me its text.\n"
            "I will turn it into a polished English "
            "Telegram post ready for @dariushcode.\n\n"
            "Send /start to leave Post Maker."
        )

    elif text == "🕹️ Pixel Art":
        context.user_data["mode"] = "pixel_art"

        await update.message.reply_text(
            "🕹️ Pixel Art mode enabled.\n\n"
            "Send me your image prompt."
        )

    elif text == "👤 User Panel":
        await user_panel(update, context)



# =========================
# Post Maker
# =========================

async def post_maker_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message or not update.effective_user:
        return

    message = update.message

    # Do not process the Post Maker menu button itself.
    if message.text == "📰 Post Maker":
        return

    # Only process messages while Post Maker mode is active.
    if context.user_data.get("mode") != "post_maker":
        return

    # Get content from a normal text message or a forwarded message.
    source_text = message.text or message.caption or ""

    if not source_text and message.reply_to_message:
        replied = message.reply_to_message
        source_text = replied.text or replied.caption or ""

    if not source_text:
        await message.reply_text(
            "📰 Post Maker\n\n"
            "Please send a text or forward a text post/message.\n\n"
            "I will turn it into a polished English Telegram post "
            "ready for @dariushcode."
        )
        return

    user_id = update.effective_user.id

    upsert_user(
        user_id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
    )

    save_message(
        user_id,
        "user",
        f"[Post Maker] {source_text}",
    )

    post_prompt = f"""
You are the professional content editor for the Telegram channel @dariushcode.

Turn the source content below into a polished English Telegram post.

Requirements:
- Preserve the important facts and meaning.
- Rewrite naturally; do not translate word-for-word.
- Make it concise, engaging, and easy to read on Telegram.
- Start with a strong, relevant headline.
- Use short paragraphs.
- Use emojis only where they improve readability.
- Add a clear call-to-action only when appropriate.
- Add 3 to 6 relevant hashtags at the end.
- Do not mention that you are an AI.
- Do not explain what you changed.
- Do not add unsupported facts.
- Do not put the post inside Markdown code fences.
- Return ONLY the final post.
- The post should be ready to copy and publish directly on Telegram.

SOURCE CONTENT:
{source_text}
""".strip()

    thinking_message = await message.reply_text("Thinking.")

    thinking_running = True

    async def thinking_animation():
        frames = [
            "Thinking.",
            "Thinking..",
            "Thinking...",
            "Thinking....",
            "Thinking.....",
        ]

        index = 0

        while thinking_running:
            try:
                await thinking_message.edit_text(
                    frames[index % len(frames)]
                )
                index += 1
                await asyncio.sleep(0.5)
            except Exception as animation_error:
                print(
                    "POST MAKER ANIMATION ERROR:",
                    type(animation_error).__name__,
                    animation_error,
                )
                break

    animation_task = asyncio.create_task(
        thinking_animation()
    )

    try:
        answer = await asyncio.to_thread(
            chat,
            post_prompt,
            messages=[],
        )

    finally:
        thinking_running = False

        animation_task.cancel()

        try:
            await animation_task
        except asyncio.CancelledError:
            pass

    save_message(
        user_id,
        "assistant",
        answer,
    )

    context.user_data.pop("mode", None)

    await thinking_message.edit_text(answer)


# =========================
# Chat Handler
# =========================

async def chat_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    user_message = update.message.text

    if not user_message:
        return

    # Notes/Reminders handlers own the message while their
    # corresponding creation mode is active. Do not let the
    # generic AI chat handler process the same message.
    if context.user_data.get("notes_mode") in {
        "new",
        "schedule",
        "time",
    }:
        return

    if context.user_data.get("reminders_mode") in {
        "text",
        "time",
    }:
        return

    menu_buttons = {
        "🤖 Dariush AI",
        "📝 Notes",
        "⏰ Reminders",
        "🎨 Create Image",
        "📰 Post Maker",
        "🕹️ Pixel Art",
        "👤 User Panel",
    }

    if user_message in menu_buttons:
        await menu_handler(update, context)
        return

    if context.user_data.get("mode") == "post_maker":
        await post_maker_handler(update, context)
        return

    if context.user_data.get("mode") == "image":
        await image_prompt_handler(update, context)
        return

    if context.user_data.get("mode") == "pixel_art":
        await pixel_art_prompt_handler(update, context)
        return

    try:
        upsert_user(
            user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
        )

        save_message(
            user_id,
            "user",
            user_message,
        )

        history = get_recent_messages(
            user_id,
            limit=20,
        )

        messages = [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in history
        ]

        # =========================
        # Animated Thinking
        # =========================

        thinking_message = await update.message.reply_text(
            "Thinking."
        )

        thinking_running = True

        async def thinking_animation():
            frames = [
                "Thinking.",
                "Thinking..",
                "Thinking...",
                "Thinking....",
                "Thinking.....",
            ]

            index = 0

            while thinking_running:
                try:
                    await thinking_message.edit_text(
                        frames[index % len(frames)]
                    )
                    index += 1
                    await asyncio.sleep(0.5)
                except Exception as animation_error:
                    print(
                        "THINKING ANIMATION ERROR:",
                        type(animation_error).__name__,
                        animation_error,
                    )
                    break

        animation_task = asyncio.create_task(
            thinking_animation()
        )

        try:
            # chat() is synchronous, so run it outside
            # the Telegram event loop.
            answer = await asyncio.to_thread(
                chat,
                user_message,
                messages=messages,
            )
        finally:
            thinking_running = False

            animation_task.cancel()

            try:
                await animation_task
            except asyncio.CancelledError:
                pass

        save_message(
            user_id,
            "assistant",
            answer,
        )

        await thinking_message.edit_text(answer)

    except Exception as error:
        print(f"AI ERROR: {error}")

        await update.message.reply_text(
            "I couldn't process your request right now. "
            "Please try again."
        )




# =========================
# Daily Reminder Job
# =========================

async def daily_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    reminders = get_due_daily_reminders()

    for reminder in reminders:
        try:
            await context.bot.send_message(
                chat_id=reminder["user_id"],
                text=(
                    "🔔 Daily Reminder\n\n"
                    f"📝 {reminder['text']}"
                ),
            )

            advance_daily_reminder(
                reminder["id"],
                reminder["remind_at"],
            )

        except Exception as error:
            print(
                f"DAILY REMINDER ERROR: "
                f"{type(error).__name__}: {error}"
            )


async def scheduled_note_job(
    context: ContextTypes.DEFAULT_TYPE,
):
    notes = get_due_scheduled_notes()

    for note in notes:
        try:
            await context.bot.send_message(
                chat_id=note["user_id"],
                text=(
                    "📝 Scheduled Note\n\n"
                    f"{note['content']}"
                ),
            )

            mark_note_schedule_completed(
                note["id"]
            )

        except Exception as error:
            print(
                f"SCHEDULED NOTE ERROR: "
                f"{type(error).__name__}: {error}"
            )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print(f"BOT ERROR: {type(context.error).__name__}: {context.error}")


# =========================
# Main
# =========================


class RenderHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Dariush AI Bot is running")

    def log_message(self, format, *args):
        pass


def start_render_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), RenderHealthHandler)
    server.serve_forever()

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is not configured."
        )

    init_db()
    threading.Thread(target=start_render_server, daemon=True).start()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue is unavailable. Install python-telegram-bot[job-queue]."
        )

    app.job_queue.run_repeating(
        daily_reminder_job,
        interval=60,
        first=10,
        name="daily_reminders",
    )

    app.job_queue.run_repeating(
        scheduled_note_job,
        interval=60,
        first=15,
        name="scheduled_notes",
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        CommandHandler("note", note_command)
    )

    app.add_handler(
        CommandHandler("notes", notes_command)
    )

    app.add_handler(
        CommandHandler(
            "delete_note",
            delete_note_command,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            notes_callback,
            pattern=r"^notes:",
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_note_text,
        ),
        group=0,
    )

    app.add_handler(
        CommandHandler(
            "reminder",
            reminder_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "reminders",
            reminders_command,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            reminders_callback,
            pattern=r"^reminders:",
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_reminder_text,
        ),
        group=1,
    )

    # =========================
    # Telegram Business
    # =========================
    app.add_handler(
        BusinessConnectionHandler(
            handle_business_connection,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            business_panel_callback,
            pattern=r"^business:panel$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            business_toggle_callback,
            pattern=r"^business:(on|off)$",
        )
    )


    app.add_handler(
        MessageHandler(
            filters.UpdateType.BUSINESS_MESSAGES,
            handle_business_message,
        ),
        group=2,
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat_handler,
        ),
        group=2,
    )

    app.add_error_handler(error_handler)

    print("Dariush AI Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
