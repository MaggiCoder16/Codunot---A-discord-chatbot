import os
import aiohttp
import re
import random

# ============================================================
# CONFIG
# ============================================================

DEAPI_API_KEY = os.getenv("DEAPI_API_KEY")
if not DEAPI_API_KEY:
    raise RuntimeError("DEAPI_API_KEY not set")

WEBHOOK_URL = os.getenv("DEAPI_WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("DEAPI_WEBHOOK_URL not set")

MODEL_NAME = "ZImageTurbo_INT8"

DEFAULT_STEPS = 15
MAX_STEPS = 50

DEFAULT_WIDTH = 512
DEFAULT_HEIGHT = 512

TXT2IMG_URL = "https://api.deapi.ai/api/v1/client/txt2img"

# ============================================================
# PROMPT HELPERS
# ============================================================

def clean_prompt(prompt: str) -> str:
    if not prompt or not prompt.strip():
        return "A clean, simple diagram"
    return re.sub(r"[\r\n]+", " ", prompt.strip())[:900]

# ============================================================
# IMAGE GENERATION (WEBHOOK EVENT-DRIVEN)
# ============================================================

async def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    steps: int = DEFAULT_STEPS,
) -> str:
    """
    Generate image using deAPI (ZImageTurbo_INT8) via webhook.
    Returns the request_id immediately. Image will be sent to your webhook when ready.
    """

    prompt = clean_prompt(prompt)
    steps = min(int(steps), MAX_STEPS)

    width = height = DEFAULT_WIDTH
    if aspect_ratio == "16:9":
        width, height = 768, 432
    elif aspect_ratio == "9:16":
        width, height = 432, 768
    elif aspect_ratio == "1:2":
        width, height = 384, 768

    headers = {
        "Authorization": f"Bearer {DEAPI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "negative_prompt": "",
        "seed": random.randint(1, 2**32 - 1),
        "webhook_url": WEBHOOK_URL,  # your webhook in secrets
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(TXT2IMG_URL, json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(await resp.text())
            data = await resp.json()

    request_id = data["data"]["request_id"]
    print(f"[deAPI] request_id={request_id} submitted. Image will be sent to your webhook.")
    return request_id
