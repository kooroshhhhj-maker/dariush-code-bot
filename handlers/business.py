from telegram import Update
from telegram.ext import ContextTypes

from ai_client import chat


async def handle_business_connection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    connection = update.business_connection

    if connection is None:
        return

    print(
        "BUSINESS CONNECTION:",
        connection.id,
        "user_id=",
        connection.user.id,
        "is_enabled=",
        connection.is_enabled,
        "rights=",
        connection.rights,
    )


async def handle_business_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.business_message

    if message is None:
        return

    text = (message.text or "").strip()

    if not text:
        print("BUSINESS MESSAGE: NON-TEXT MESSAGE")
        return

    connection_id = message.business_connection_id

    print("================================")
    print("BUSINESS MESSAGE RECEIVED")
    print("connection_id =", connection_id)
    print("chat_id       =", message.chat_id)
    print("text          =", repr(text))
    print("================================")

    try:
        await message.chat.send_action(
            "typing",
            business_connection_id=connection_id,
        )

        print("BUSINESS: typing sent")
        print("BUSINESS: calling AI...")

        answer = chat(text)

        print("BUSINESS: AI RESPONSE =", repr(answer))

        sent = await context.bot.send_message(
            chat_id=message.chat_id,
            text=answer,
            business_connection_id=connection_id,
        )

        print(
            "BUSINESS: MESSAGE SENT OK, message_id =",
            sent.message_id,
        )

    except Exception as error:
        print("================================")
        print("BUSINESS AI ERROR")
        print("TYPE:", type(error).__name__)
        print("ERROR:", repr(error))
        print("================================")
