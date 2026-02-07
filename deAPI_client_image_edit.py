import os
import aiohttp
import io
import random

DEAPI_API_KEY = os.getenv("DEAPI_API_KEY", "").strip()
WEBHOOK_URL = os.getenv("DEAPI_WEBHOOK_URL", "").strip()

if not DEAPI_API_KEY:
    raise RuntimeError("DEAPI_API_KEY not set")
if not WEBHOOK_URL:
    raise RuntimeError("DEAPI_WEBHOOK_URL not set")

IMG2IMG_URL = "https://api.deapi.ai/api/v1/client/img2img"
MODEL_NAME = "Flux_2_Klein_4B_BF16"
DEFAULT_STEPS = 4
MAX_STEPS = 4

async def edit_image(
    image_bytes: bytes,
    prompt: str,
    steps: int = DEFAULT_STEPS,
) -> str:
    """
    Submit an image edit job to deAPI using a webhook.
    Returns the request_id for webhook tracking.
    """

    seed = random.randint(1, 2**32 - 1)
    steps = min(steps, MAX_STEPS)
    prompt = (prompt or "").strip()

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
    form.add_field("prompt", prompt)
    form.add_field("model", MODEL_NAME)
    form.add_field("steps", str(steps))
    form.add_field("seed", str(seed))
    form.add_field("strength", "1.0")
    form.add_field("webhook_url", WEBHOOK_URL)

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
        async with session.post(IMG2IMG_URL, data=form, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Image edit submission failed ({resp.status}): {text}")

            data = await resp.json()
            request_id = data.get("data", {}).get("request_id")
            if not request_id:
                raise RuntimeError(f"No request_id returned: {data}")

            print(f"[deAPI EDIT] Submitted | request_id={request_id} | seed={seed}")
            print("The edited image will be delivered to your webhook when ready.")

            return request_id
