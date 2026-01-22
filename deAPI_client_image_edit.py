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
    steps: int = DEFAULT_STEPS,
    seed: int | None = None,
    strength: float = 0.45,
) -> bytes:
    """
    RPD-SAFE DeAPI img2img call.
    """

    steps = min(int(steps), MAX_STEPS)
    seed = seed or random.randint(1, 2**32 - 1)
    safe_prompt = prompt.replace("\n", " ").replace("\r", " ").strip()

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
    form.add_field("prompt", safe_prompt)
    form.add_field("model", MODEL_NAME)
    form.add_field("steps", str(steps))
    form.add_field("seed", str(seed))
    form.add_field("strength", str(strength))
    form.add_field("return_result_in_response", "true")

    timeout = aiohttp.ClientTimeout(total=180)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(IMG2IMG_URL, data=form, headers=headers) as resp:
            body = await resp.read()
            content_type = resp.headers.get("Content-Type", "")

            if content_type.startswith("image/"):
                return body

            data = await resp.json()

            image_b64 = data.get("image") or data.get("data", {}).get("image")
            if image_b64:
                return base64.b64decode(image_b64)

            payload = data.get("data", {})

            result_url = payload.get("result_url")
            if result_url:
                async with session.get(result_url) as img_resp:
                    if img_resp.status == 200:
                        return await img_resp.read()
                    raise RuntimeError("Failed to download result image")

            status = payload.get("status")
            if status in ("pending", "processing", "queued"):
                raise RuntimeError(
                    "Image still processing. Try again shortly."
                )

            raise RuntimeError(f"Unexpected DeAPI response: {data}")
