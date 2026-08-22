import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "stealth/ox-alpha",
)

API_URL = "https://openrouter.ai/api/v1/chat/completions"

BASE_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BASE_DIR / "prompts" / "dariush.txt"


def load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {PROMPT_PATH}"
        )

    return PROMPT_PATH.read_text(
        encoding="utf-8"
    ).strip()


SYSTEM_PROMPT = load_system_prompt()


def chat(
    user_message: str,
    messages=None,
) -> str:

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY در فایل .env تنظیم نشده است."
        )

    if not user_message:
        raise ValueError(
            "پیام کاربر خالی است."
        )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://openrouter.ai/",
        "X-Title": "Dariush AI Bot",
    }

    conversation = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    if messages:
        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if role not in ("user", "assistant"):
                continue

            if not content:
                continue

            conversation.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    if (
        not conversation
        or conversation[-1].get("content") != user_message
    ):
        conversation.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": conversation,
        "max_tokens": 1000,
        "temperature": 0.7,
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )

    if not response.ok:
        print("OPENROUTER STATUS:", response.status_code)
        print("OPENROUTER ERROR:", response.text)
        response.raise_for_status()

    data = response.json()

    choices = data.get("choices")

    if not choices:
        raise RuntimeError(
            f"OpenRouter returned no choices: {data}"
        )

    message = choices[0].get("message", {})
    answer = message.get("content")

    if not answer:
        raise RuntimeError(
            f"OpenRouter returned an empty response: {data}"
        )

    answer = answer.strip()

    prefix = "from thisisDariush 🤖:"

    if not answer.startswith(prefix):
        answer = f"{prefix} {answer}"

    return answer
