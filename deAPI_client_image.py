import os
import asyncio
import aiohttp
import re
import random
import base64

# ============================================================
# CONFIG
# ============================================================

DEAPI_API_KEY = os.getenv("DEAPI_API_KEY")
if not DEAPI_API_KEY:
    raise RuntimeError("DEAPI_API_KEY not set")

MODEL_NAME = "ZImageTurbo_INT8"

DEFAULT_STEPS = 8          # Turbo is designed for 8 steps
MAX_STEPS = 10

DEFAULT_WIDTH = 512
DEFAULT_HEIGHT = 512

TXT2IMG_URL = "https://api.deapi.ai/api/v1/client/txt2img"
POLL_URL = "https://api.deapi.ai/api/v1/client/inference"

MAX_POLL_SECONDS = 120     # hard stop (2 minutes)
MAX_404_SECONDS = 15       # abort early if never scheduled

# ============================================================
# PROMPT HELPERS
# ============================================================

def build_diagram_prompt(user_text: str) -> str:
    return (
        "Simple clean diagram, flat vector style, white background, "
        "clear labels, arrows, minimal design, educational, no realism.\n\n"
        + user_text
    )

def clean_prompt(prompt: str) -> str:
    if not prompt or not prompt.strip():
        return "A clean, simple diagram"
    prompt = re.sub(r"[\r\n]+", " ", prompt.strip())
    return prompt[:900]

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

    # ---- SAFETY ----
    steps = min(int(steps), MAX_STEPS)

    # ---- RESOLUTION ----
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
        # ====================================================
        # SEND REQUEST
        # ====================================================
        async with session.post(
            TXT2IMG_URL,
            json=payload,
            headers=headers,
        ) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(
                    f"deAPI txt2img failed ({resp.status}): {text}"
                )
            data = await resp.json()

        request_id = data.get("data", {}).get("request_id")
        if not request_id:
            raise RuntimeError(f"deAPI returned no request_id: {data}")

        print(f"[deAPI] request_id = {request_id}", flush=True)

        # ====================================================
        # POLLING
        # ====================================================
        waited = 0
        consecutive_404s = 0

        while waited < MAX_POLL_SECONDS:
            async with session.get(
                f"{POLL_URL}/{request_id}",
                headers=headers,
            ) as poll_resp:
                print(f"[deAPI POLL] HTTP {poll_resp.status}", flush=True)

                if poll_resp.status == 404:
                    consecutive_404s += 1
                    print("[deAPI POLL] not ready yet (404)", flush=True)

                    if consecutive_404s >= MAX_404_SECONDS:
                        raise RuntimeError(
                            "deAPI did not schedule the job (backend overload)"
                        )

                    await asyncio.sleep(1)
                    waited += 1
                    continue

                consecutive_404s = 0

                poll_data = await poll_resp.json()
                print("[deAPI POLL DATA]", poll_data, flush=True)

                status = poll_data.get("data", {}).get("status")

                if status == "succeeded":
                    result = poll_data["data"].get("result", {})
                    image_base64 = result.get("image_base64")
                    if not image_base64:
                        raise RuntimeError(
                            f"deAPI succeeded but no image returned: {poll_data}"
                        )
                    return base64.b64decode(image_base64)

                if status == "failed":
                    raise RuntimeError(
                        f"deAPI image generation failed: {poll_data}"
                    )

                print(f"[deAPI] status = {status}", flush=True)

            await asyncio.sleep(1)
            waited += 1

        raise RuntimeError(
            "deAPI image generation timed out"
        )
