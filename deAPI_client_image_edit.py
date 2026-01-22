import os
import aiohttp
import random
import io
import base64

DEAPI_API_KEY = os.getenv("DEAPI_API_KEY_IMAGE_EDITING", "").strip()
if not DEAPI_API_KEY:
    raise RuntimeError("DEAPI_API_KEY_IMAGE_EDITING not set")

IMG2IMG_URL = "https://api.deapi.ai/api/v1/client/img2img"
MODEL_NAME = "QwenImageEdit_Plus_NF4"

DEFAULT_STEPS = 8        # keep low for merges
MAX_STEPS = 12           # hard cap to avoid long jobs

async def edit_image(
    image_bytes: bytes,
    prompt: str,
    steps: int = 12,
    seed: int | None = None,
    strength: float = 0.35,
) -> bytes:

    seed = seed or random.randint(1, 2**32 - 1)

    headers = {
        "Authorization": f"Bearer {DEAPI_API_KEY}",
        "Accept": "application/json",
    }

    form = aiohttp.FormData()
    form.add_field(
        "image",
        io.BytesIO(image_bytes),
        filename="input.png",
        content_type="image/png",
    )
    form.add_field("prompt", prompt.strip())
    form.add_field("model", MODEL_NAME)
    form.add_field("steps", str(steps))
    form.add_field("seed", str(seed))
    form.add_field("strength", str(strength))
    form.add_field("return_result_in_response", "true")

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=120)
    ) as session:
        async with session.post(IMG2IMG_URL, data=form, headers=headers) as resp:
            body = await resp.read()
            ctype = resp.headers.get("Content-Type", "")

            if ctype.startswith("image/"):
                return body

            data = await resp.json()
            payload = data.get("data", {})

            if payload.get("image"):
                return base64.b64decode(payload["image"])

            if payload.get("result_url"):
                async with session.get(payload["result_url"]) as img_resp:
                    if img_resp.status == 200:
                        return await img_resp.read()
                    raise RuntimeError("Failed to download result_url image")

            raise RuntimeError(f"No image returned: {data}")
