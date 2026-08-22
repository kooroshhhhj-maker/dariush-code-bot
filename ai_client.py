import os
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv(dotenv_path=".env")


HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
HF_MODEL = os.getenv(
    "HUGGINGFACE_MODEL",
    "Qwen/Qwen3-4B-Instruct-2507",
)

API_URL = "https://router.huggingface.co/v1/chat/completions"

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
    if not HF_TOKEN:
        raise RuntimeError(
            "HUGGINGFACE_API_KEY در فایل .env تنظیم نشده است."
        )

    if not user_message:
        raise ValueError(
            "پیام کاربر خالی است."
        )

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    conversation = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    # تاریخچه مکالمه
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

    # اگر پیام فعلی قبلاً در history نبود،
    # آن را اضافه کن.
    if not conversation or conversation[-1].get("content") != user_message:
        conversation.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

    payload = {
        "model": HF_MODEL,
        "messages": conversation,
        "max_tokens": 500,
        "temperature": 0.7,
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    choices = data.get("choices")

    if not choices:
        raise RuntimeError(
            f"Hugging Face returned no choices: {data}"
        )

    message = choices[0].get("message", {})
    answer = message.get("content")

    if not answer:
        raise RuntimeError(
            f"Hugging Face returned an empty response: {data}"
        )

    answer = answer.strip()

    # تضمین Prefix داریوش
    prefix = "from thisisDariush 🤖:"

    if not answer.startswith(prefix):
        answer = f"{prefix} {answer}"

    return answer
