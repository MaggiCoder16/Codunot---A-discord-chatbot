import os
import asyncio
import requests
import base64

# ============================================================
# CONFIG
# ============================================================

DEAPI_API_KEY = os.getenv("DEAPI_API_KEY")
if not DEAPI_API_KEY:
    raise RuntimeError("DEAPI_API_KEY not set")

MODEL_NAME = "ZImageTurbo_INT8"

print(f"🔥 USING deAPI model {MODEL_NAME} 🔥")

# ============================================================
# DIAGRAM PROMPT HELPER
# ============================================================

def build_diagram_prompt(user_text: str) -> str:
    return (
        "Simple clean diagram, flat vector style, white background, "
        "clear labels, arrows, minimal design, educational, no realism.\n\n"
        + user_text
    )

# ============================================================
# IMAGE GENERATION (MATCHES groq_bot.py EXACTLY)
# ============================================================

async def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    steps: int = 20
) -> bytes:
    """
    Generate image using deAPI ZImageTurbo_INT8 model.
    Returns raw PNG bytes.
    """

    loop = asyncio.get_event_loop()

    def sync_call():
        try:
            # deAPI uses width/height instead of aspect_ratio
            width, height = (512, 512)
            if aspect_ratio == "16:9":
                width, height = 512, 288
            elif aspect_ratio == "9:16":
                width, height = 288, 512
            elif aspect_ratio == "1:2":
                width, height = 256, 512
            # Add more mappings if needed

            payload = {
                "prompt": prompt,
                "model": MODEL_NAME,
                "width": width,
                "height": height,
                "steps": steps
            }

            headers = {
                "Authorization": f"Bearer {DEAPI_API_KEY}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                "https://api.deapi.ai/api/v1/client/txt2img",
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            data = response.json()

            # deAPI returns base64-encoded PNG
            img_b64 = data["data"]["output"][0]["b64_json"]
            return base64.b64decode(img_b64)

        except Exception as e:
            print("[deAPI ERROR]", e)
            return None

    image_bytes = await loop.run_in_executor(None, sync_call)

    if not image_bytes:
        raise RuntimeError("deAPI failed to generate image")

    return image_bytes
