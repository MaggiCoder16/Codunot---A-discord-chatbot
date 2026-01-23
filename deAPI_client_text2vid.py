import os
import aiohttp
import asyncio
import random

DEAPI_API_KEY = os.getenv("DEAPI_API_KEY_TEXT2VID", "").strip()
BASE_URL = "https://api.deapi.ai/api/v1/client"

TXT2VID_ENDPOINT = f"{BASE_URL}/txt2video"
RESULT_ENDPOINT = f"{BASE_URL}/results"

class Text2VidError(Exception):
    pass

async def text_to_video_512(
    *,
    prompt: str,
    guidance: float = 0.0,
    steps: int = 1,
    frames: int = 120,
    fps: int = 30,
    model: str = "Ltxv_13B_0_9_8_Distilled_FP8",
    negative_prompt: str | None = None,
):
    """
    Generate a 512x512 text-to-video clip.
    Returns raw video bytes (mp4).
    Uses two polls: first at 45s, second at 70s total.
    """

    if not prompt or not prompt.strip():
        raise Text2VidError("Prompt is required")

    # random seed
    seed = random.randint(0, 2**32 - 1)

    headers = {
        "Authorization": f"Bearer {DEAPI_API_KEY}",
        "Accept": "application/json",
    }

    form = aiohttp.FormData()
    form.add_field("prompt", prompt)
    form.add_field("width", "512")
    form.add_field("height", "512")
    form.add_field("guidance", str(guidance))
    form.add_field("steps", str(steps))
    form.add_field("frames", str(frames))
    form.add_field("seed", str(seed))
    form.add_field("model", model)
    form.add_field("fps", str(fps))
    if negative_prompt:
        form.add_field("negative_prompt", negative_prompt)

    async with aiohttp.ClientSession(headers=headers) as session:
        # ── SUBMIT JOB ──
        async with session.post(TXT2VID_ENDPOINT, data=form, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status != 200:
                raise Text2VidError(f"txt2video submit failed ({resp.status}): {await resp.text()}")
            payload = await resp.json()
            request_id = payload.get("data", {}).get("request_id")
            if not request_id:
                raise Text2VidError("No request_id returned")
            print(f"[VIDEO GEN] Request submitted. request_id = {request_id}, seed = {seed}")

        # ── FIRST POLL AFTER 45s ──
        await asyncio.sleep(45)
        async with session.get(f"{RESULT_ENDPOINT}/{request_id}") as resp:
            if resp.status == 200:
                result = await resp.json()
            elif resp.status == 404:
                print(f"[VIDEO GEN] Not ready yet, retrying second poll for request_id={request_id}")
                # ── SECOND POLL AFTER 30s (total 75s) ──
                await asyncio.sleep(30)
                async with session.get(f"{RESULT_ENDPOINT}/{request_id}") as resp2:
                    if resp2.status != 200:
                        raise Text2VidError(f"Failed to fetch result ({resp2.status}) for request_id={request_id}")
                    result = await resp2.json()
            else:
                raise Text2VidError(f"Unexpected status {resp.status} for request_id={request_id}")

        status = result.get("data", {}).get("status")
        if status == "completed":
            video_url = result.get("data", {}).get("output", {}).get("video_url")
            if not video_url:
                raise Text2VidError("Completed but no video_url")
            async with session.get(video_url) as vresp:
                if vresp.status != 200:
                    raise Text2VidError("Failed to download video")
                return await vresp.read()
        elif status in ("failed", "error"):
            raise Text2VidError(f"txt2video failed: {result}")
        else:
            raise Text2VidError(f"Video not ready after two polls, status={status}")
