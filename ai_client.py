import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)

# =========================
# OpenRouter
# =========================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

# =========================
# Hugging Face fallback
# =========================

HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
HF_MODEL = os.getenv(
    "HF_MODEL",
    "openai/gpt-oss-120b:fastest",
)

HF_URL = (
    "https://router.huggingface.co/v1/chat/completions"
)

# =========================
# Prompt
# =========================

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


# =========================
# Helpers
# =========================

def build_conversation(user_message: str, messages=None):
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

    return conversation


def extract_answer(data):
    choices = data.get("choices")

    if not choices:
        raise RuntimeError(
            f"Provider returned no choices: {data}"
        )

    message = choices[0].get("message", {})
    answer = message.get("content")

    if not answer:
        raise RuntimeError(
            f"Provider returned an empty response: {data}"
        )

    return answer.strip()


def add_prefix(answer: str) -> str:
    prefix = "🤖BOT/:"

    # Remove old bot prefixes if the AI/provider included one.
    old_prefixes = (
        "from thisisDariush 🤖:",
        "از این‌این‌داریوش 🤖:",
        "از این داریوش 🤖:",
        "🤖BOT/:",
    )

    answer = answer.strip()

    for old_prefix in old_prefixes:
        if answer.startswith(old_prefix):
            answer = answer[len(old_prefix):].lstrip()
            break

    return f"{prefix} {answer}"


# =========================
# OpenRouter
# =========================

def chat_openrouter(conversation):
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY در فایل .env تنظیم نشده است."
        )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://openrouter.ai/",
        "X-Title": "Dariush AI Bot",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": conversation,
        "max_tokens": 1000,
        "temperature": 0.7,
    }

    print(
        f"AI: Trying OpenRouter model={OPENROUTER_MODEL}"
    )

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )

    print(
        f"OPENROUTER STATUS: {response.status_code}"
    )

    if not response.ok:
        print(
            "OPENROUTER ERROR:",
            response.text[:2000],
        )
        response.raise_for_status()

    data = response.json()

    return extract_answer(data)


# =========================
# Hugging Face fallback
# =========================

def chat_huggingface(conversation):
    if not HF_TOKEN:
        raise RuntimeError(
            "HF_TOKEN در فایل .env تنظیم نشده است."
        )

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": HF_MODEL,
        "messages": conversation,
        "max_tokens": 1000,
        "temperature": 0.7,
        "stream": False,
    }

    print(
        f"AI: Trying Hugging Face model={HF_MODEL}"
    )

    response = requests.post(
        HF_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )

    print(
        f"HUGGINGFACE STATUS: {response.status_code}"
    )

    if not response.ok:
        print(
            "HUGGINGFACE ERROR:",
            response.text[:2000],
        )
        response.raise_for_status()

    data = response.json()

    return extract_answer(data)


# =========================
# Main chat function
# =========================

def chat(user_message: str, messages=None) -> str:
    if not user_message:
        raise ValueError("پیام کاربر خالی است.")

    conversation = build_conversation(
        user_message,
        messages,
    )

    # ---------------------------------
    # 1. Try OpenRouter
    # ---------------------------------

    try:
        answer = chat_openrouter(conversation)

        print("AI: OpenRouter succeeded")

        return add_prefix(answer)

    except Exception as error:
        print(
            "OPENROUTER FAILED:",
            type(error).__name__,
            str(error),
        )

    # ---------------------------------
    # 2. Fallback to Hugging Face
    # ---------------------------------

    try:
        answer = chat_huggingface(conversation)

        print("AI: Hugging Face succeeded")

        return add_prefix(answer)

    except Exception as error:
        print(
            "HUGGINGFACE FAILED:",
            type(error).__name__,
            str(error),
        )

        raise RuntimeError(
            "هر دو سرویس OpenRouter و Hugging Face "
            "ناموفق بودند."
        )
