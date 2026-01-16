import os
import asyncio
import aiohttp
import re
import random

# ============================================================
# CONFIG
# ============================================================

DEAPI_API_KEY = os.getenv("DEAPI_API_KEY")
if not DEAPI_API_KEY:
    raise RuntimeError("DEAPI_API_KEY not set")

MODEL_NAME = "ZImageTurbo_INT8"

DEFAULT_STEPS = 15
MAX_STEPS = 50

DEFAULT_WIDTH = 512
DEFAULT_HEIGHT = 512

TXT2IMG_URL = "https://api.deapi.ai/api/v1/client/txt2img"
STATUS_URL = "https://api.deapi.ai/api/v1/client/request-status"

MAX_POLL_SECONDS = 120

# ============================================================
# PROMPT HELPERS
# ============================================================

def clean_prompt(prompt: str) -> str:
    if not prompt or not prompt.strip():
        return "A clean, simple diagram"
    return re.sub(r"[\r\n]+", " ", prompt.strip())[:900]

# ============================================================
# IMAGE GENERATION
# ============================================================

async def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    steps: int = DEFAULT_STEPS,
) -> bytes:
    """
    Generate image using deAPI (ZImageTurbo_INT8).
    Returns raw PNG bytes.
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
    }

    async with aiohttp.ClientSession() as session:
        # ---------------------------
        # SUBMIT JOB
        # ---------------------------
        async with session.post(TXT2IMG_URL, json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(await resp.text())
            data = await resp.json()

        request_id = data["data"]["request_id"]
        print(f"[deAPI] request_id = {request_id}", flush=True)

        # ---------------------------
        # POLL STATUS
        # ---------------------------
        waited = 0
        while waited < MAX_POLL_SECONDS:
            async with session.get(f"{STATUS_URL}/{request_id}", headers=headers) as r:
                status_data = await r.json()
                print("[deAPI STATUS]", status_data, flush=True)

                data = status_data["data"]
                status = data["status"]

                if status == "done":
                    result_url = data.get("result_url")
                    if not result_url:
                        raise RuntimeError("Job done but no result_url returned")

                    # ---------------------------
                    # DOWNLOAD IMAGE
                    # ---------------------------
                    async with session.get(result_url) as img_resp:
                        if img_resp.status != 200:
                            raise RuntimeError("Failed to download image")
                        return await img_resp.read()

                if status == "failed":
                    raise RuntimeError(f"Generation failed: {status_data}")

            await asyncio.sleep(1)
            waited += 1

        raise RuntimeError("deAPI image generation timed out")
