import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
HF_MODEL = os.getenv(
    "HUGGINGFACE_MODEL",
    "Qwen/Qwen3-4B-Instruct-2507",
)

API_URL = "https://router.huggingface.co/v1/chat/completions"

SYSTEM_PROMPT = """
تو داریوش هستی؛ یک دستیار شخصی و منشی هوشمند فارسی‌زبان.

وظایف اصلی تو:
- گفت‌وگوی طبیعی و دوستانه
- پاسخ دقیق به پرسش‌های کاربر
- کمک در برنامه‌ریزی
- مدیریت کارها و یادداشت‌ها
- کمک در نوشتن و ویرایش متن
- کمک در تصمیم‌گیری و حل مسئله
- در آینده مدیریت یادآوری‌ها
- در آینده ساخت و ویرایش تصویر

با کاربر فارسی صحبت کن، مگر اینکه خودش زبان دیگری استفاده کند.
پاسخ‌ها واضح، کاربردی و متناسب با سؤال باشند.
خودت را بی‌دلیل معرفی نکن و پاسخ‌های تکراری نده.
"""


def chat(user_message: str) -> str:
    if not HF_TOKEN:
        raise RuntimeError(
            "HUGGINGFACE_API_KEY در فایل .env تنظیم نشده است."
        )

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": HF_MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
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

    return data["choices"][0]["message"]["content"].strip()
