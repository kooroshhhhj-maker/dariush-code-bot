from telegram import Update
from telegram.ext import ContextTypes

from ai_client import chat

from database import (
    save_business_connection,
    get_business_connection,
)


async def handle_business_connection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    connection = update.business_connection

    if connection is None:
        return

    # Store the Business connection owner and current setting.
    existing = get_business_connection(connection.id)

    enabled = (
        bool(existing["enabled"])
        if existing is not None
        else True
    )

    save_business_connection(
        connection_id=connection.id,
        owner_user_id=connection.user.id,
        enabled=enabled,
    )

    print(
        "BUSINESS CONNECTION:",
        connection.id,
        "user_id=",
        connection.user.id,
        "is_enabled=",
        connection.is_enabled,
        "auto_reply=",
        enabled,
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
    print(
        "from_user_id  =",
        message.from_user.id if message.from_user else None,
    )
    print("text          =", repr(text))
    print("================================")

    connection = get_business_connection(connection_id)

    if connection is None:
        print(
            "BUSINESS: connection not registered yet. Ignoring message."
        )
        return

    owner_id = connection["owner_user_id"]

    # Never reply to the owner of the connected Business account.
    if (
        message.from_user is not None
        and message.from_user.id == owner_id
    ):
        print(
            "BUSINESS: ignoring owner's own message",
            "owner_id=",
            owner_id,
        )
        return

    # Auto Reply can be disabled from User Panel.
    if not bool(connection["enabled"]):
        print(
            "BUSINESS: auto reply is OFF",
            "connection_id=",
            connection_id,
        )
        return

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
