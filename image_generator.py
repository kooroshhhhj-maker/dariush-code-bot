import os
import base64
import random
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

MODEL = "@cf/black-forest-labs/flux-1-schnell"

API_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL}"
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "generated_images"
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_image(prompt: str) -> Path:
    if not CLOUDFLARE_API_TOKEN:
        raise RuntimeError("CLOUDFLARE_API_TOKEN is missing.")

    if not CLOUDFLARE_ACCOUNT_ID:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID is missing.")

    prompt = prompt.strip()

    if not prompt:
        raise ValueError("Image prompt is empty.")

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "steps": 4,
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=(30, 300),
    )

    print("CLOUDFLARE STATUS:", response.status_code)

    if not response.ok:
        print("CLOUDFLARE RESPONSE:")
        print(response.text[:5000])
        response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise RuntimeError(
            f"Cloudflare AI error: {data}"
        )

    result = data.get("result")

    if not result:
        raise RuntimeError(
            f"Cloudflare returned no result: {data}"
        )

    image_b64 = result.get("image")

    if not image_b64:
        raise RuntimeError(
            f"Cloudflare returned no image: {data}"
        )

    try:
        image_data = base64.b64decode(image_b64)
    except Exception as error:
        raise RuntimeError(
            f"Invalid Base64 image returned by Cloudflare: {error}"
        )

    filename = (
        f"dariush_{random.randint(100000, 999999)}.jpg"
    )

    output_path = OUTPUT_DIR / filename

    output_path.write_bytes(image_data)

    return output_path
