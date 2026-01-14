import os
import io
import asyncio
import replicate
import requests

# ============================================================
# CONFIG
# ============================================================

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise RuntimeError("REPLICATE_API_TOKEN not set")

# Replicate uses env var automatically
print("🔥 USING REPLICATE Imagen 4 via replicate.run 🔥")

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
# IMAGE GENERATION
# ============================================================

async def generate_image(prompt: str, is_diagram: bool = False) -> bytes:
    loop = asyncio.get_event_loop()

    if is_diagram:
        prompt = build_diagram_prompt(prompt)

    def sync_call():
        try:
            output = replicate.run(
                "google/imagen-4",
                input={
                    "prompt": prompt,
                    "aspect_ratio": "1:1",
                    "output_format": "png",
                    "safety_filter_level": "block_medium_and_above"
                }
            )

            # Imagen returns a File-like object
            return output.read()

        except Exception as e:
            print("[Replicate ERROR]", e)
            return None

    image_bytes = await loop.run_in_executor(None, sync_call)

    if not image_bytes:
        raise RuntimeError("Replicate failed to generate image")

    return image_bytes
