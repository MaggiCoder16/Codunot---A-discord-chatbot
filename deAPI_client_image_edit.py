# deAPI_client_image_edit.py

import os
import aiohttp
import asyncio
import random
import base64

DEAPI_API_KEY = os.getenv("DEAPI_API_KEY_IMAGE_EDITING", "").strip()
if not DEAPI_API_KEY:
    raise RuntimeError("DEAPI_API_KEY_IMAGE_EDITING not set")

IMG2IMG_URL = "https://api.deapi.ai/api/v1/client/img2img"
IMG_RESULT_URL = "https://api.deapi.ai/api/v1/client/result"

MODEL_NAME = "QwenImageEdit_Plus_NF4"
DEFAULT_STEPS = 15
MAX_STEPS = 40


async def poll_deapi_result(session, request_id, timeout=30):
    headers = {
        "Authorization": f"Bearer {DEAPI_API_KEY}",
    }

    for _ in range(timeout):
        async with session.get(
            f"{IMG_RESULT_URL}/{request_id}",
            headers=headers
        ) as resp:
            if resp.status != 200:
                await asyncio.sleep(1)
                continue

            data = await resp.json()

            # Image ready
            if "image" in data:
                return base64.b64decode(data["image"])

            # Still processing
            status = data.get("status") or data.get("data", {}).get("status")
            if status in ("pending", "processing"):
                await asyncio.sleep(1)
                continue

        await asyncio.sleep(1)

    raise RuntimeError("Timed out waiting for DeAPI image result")


async def edit_image(
    image_bytes: bytes,
    prompt: str,
    steps: int = DEFAULT_STEPS,
    seed: int | None = None
) -> bytes:

    steps = min(int(steps), MAX_STEPS)
    seed = seed or random.randint(1, 2**32 - 1)

    safe_prompt = prompt.replace("\n", " ").replace("\r", " ").strip()

    headers = {
        "Authorization": f"Bearer {DEAPI_API_KEY}",
    }

    form = aiohttp.FormData()
    form.add_field(
        "image",
        image_bytes,
        filename="input.png",
        content_type="image/png"
    )
    form.add_field("prompt", safe_prompt)
    form.add_field("model", MODEL_NAME)
    form.add_field("steps", str(steps))
    form.add_field("seed", str(seed))

    async with aiohttp.ClientSession() as session:
        async with session.post(IMG2IMG_URL, data=form, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(await resp.text())

            content_type = resp.headers.get("Content-Type", "")

            if content_type.startswith("image/"):
                return await resp.read()

            if "application/json" in content_type:
                data = await resp.json()

                # Immediate base64 image
                if "image" in data:
                    return base64.b64decode(data["image"])

                # Async job returned
                if "data" in data and "request_id" in data["data"]:
                    request_id = data["data"]["request_id"]
                    return await poll_deapi_result(session, request_id)

                raise RuntimeError(f"Unexpected JSON response: {data}")

            body = await resp.text()
            raise RuntimeError(
                f"Unexpected response type {content_type}: {body}"
            )
