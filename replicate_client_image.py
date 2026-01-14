import os
import io
import base64
import asyncio
import replicate
from PIL import Image

# ============================================================
# CONFIG
# ============================================================

# Set your Replicate API token in environment variables
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
if not REPLICATE_API_TOKEN:
    raise ValueError("Please set your REPLICATE_API_TOKEN environment variable")

# Initialize client
client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# Default model to use
DEFAULT_MODEL = "stability-ai/stable-diffusion-2"

# ============================================================
# PROMPT HELPER (for diagrams)
# ============================================================

def build_diagram_prompt(user_text: str) -> str:
    """
    Simple, SD-friendly diagram style.
    """
    return (
        "Simple clean diagram, flat vector style, white background, "
        "clear labels, arrows, minimal design, educational, no realism.\n\n"
        f"{user_text}"
    )

# ============================================================
# INTERNAL: generate image async
# ============================================================

async def generate_image_replicate(prompt: str, width: int = 512, height: int = 512, steps: int = 20) -> bytes | None:
    """
    Generate an image using Replicate. Returns raw PNG bytes or None on failure.
    """
    loop = asyncio.get_event_loop()

    def sync_call():
        try:
            # Replicate's Python client call is synchronous
            output_urls = client.predict(
                model=DEFAULT_MODEL,
                input={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_inference_steps": steps
                }
            )
            if not output_urls:
                print("[Replicate ERROR] No output URLs returned")
                return None

            # The model returns a list of URLs, take first
            img_url = output_urls[0]
            import requests
            resp = requests.get(img_url)
            if resp.status_code != 200:
                print("[Replicate ERROR] Failed to fetch image from URL:", resp.status_code)
                return None

            return resp.content

        except Exception as e:
            print("[Replicate ERROR]", e)
            return None

    return await loop.run_in_executor(None, sync_call)
