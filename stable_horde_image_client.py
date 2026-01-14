import os
import io
import base64
import aiohttp
import asyncio
from PIL import Image

# ============================================================
# CONFIG
# ============================================================
STABLE_HORDE_API_KEY = os.getenv("STABLE_HORDE_API_KEY", "")
STABLE_HORDE_URL = "https://stablehorde.net/api/v2/generate/async"
STABLE_HORDE_STATUS_URL = "https://stablehorde.net/api/v2/status"

# ============================================================
# PROMPT BUILDER (FOR DIAGRAMS)
# ============================================================
def build_diagram_prompt(user_text: str) -> str:
    """
    Returns a prompt suitable for educational diagrams.
    """
    return (
        "Clean educational diagram, flat vector style, "
        "white background, clear black text labels, arrows, "
        "simple shapes, top-to-bottom layout, "
        "no realism, no shadows, no textures.\n\n"
        f"{user_text}"
    )

# ============================================================
# PUBLIC IMAGE GENERATOR (ASYNC)
# ============================================================
async def generate_image_horde(prompt: str, *, diagram: bool = False, timeout: int = 120) -> bytes:
    """
    Generate an image using Stable Horde async API.
    Returns raw PNG bytes.
    """
    if diagram:
        prompt = build_diagram_prompt(prompt)

    headers = {"Content-Type": "application/json"}
    if STABLE_HORDE_API_KEY:
        headers["apikey"] = STABLE_HORDE_API_KEY

    payload = {
        "prompt": prompt,
        "params": {
            "steps": 25,
            "width": 512,
            "height": 512,
            "cfg_scale": 7.0,
            "sampler_name": "k_euler"
        },
        "nsfw": False
    }

    print("[Stable Horde] Sending payload:", payload)

    async with aiohttp.ClientSession() as session:
        # Step 1: Submit job
        async with session.post(STABLE_HORDE_URL, json=payload, headers=headers, timeout=timeout) as resp:
            text = await resp.text()
            if resp.status not in (200, 202):
                print(f"[Stable Horde ERROR] Status {resp.status}: {text}")
                raise RuntimeError(f"[Stable Horde] Failed with status {resp.status}: {text}")

            data = await resp.json()
            print("[Stable Horde] Job response:", data)

        job_id = data.get("id")
        if not job_id:
            raise RuntimeError(f"[Stable Horde] No job ID returned: {data}")

        # Step 2: Poll until image is ready
        for _ in range(timeout // 2):
            await asyncio.sleep(2)
            try:
                async with session.get(f"{STABLE_HORDE_STATUS_URL}/{job_id}", headers=headers, timeout=30) as status_resp:
                    status_data = await status_resp.json()
                    if "generations" in status_data and status_data["generations"]:
                        img_b64 = status_data["generations"][0].get("img")
                        if img_b64:
                            print("[Stable Horde] Image generated successfully")
                            return base64.b64decode(img_b64)
            except Exception as e:
                print("[Stable Horde ERROR] Polling failed:", e)

        raise RuntimeError("[Stable Horde] Timeout waiting for image")
