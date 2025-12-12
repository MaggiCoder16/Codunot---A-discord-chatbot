import aiohttp
import os
import asyncio
import base64
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SESSION: aiohttp.ClientSession | None = None

def clean_log(text: str) -> str:
    if not text:
        return text
    if GROQ_API_KEY:
        text = text.replace(GROQ_API_KEY, "***")
    return text

async def get_session():
    global SESSION
    if SESSION is None or SESSION.closed:
        SESSION = aiohttp.ClientSession()
    return SESSION

def encode_image_bytes(image_bytes: bytes, mime: str = "image/png") -> str:
    """Return base64 data URL string."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"

async def call_groq(
    prompt: str | None = None,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 1.0,
    image_bytes: bytes | None = None,
    image_mime: str = "image/png",
    retries: int = 4
) -> str | None:
    """General Groq caller supporting text + vision models."""
    if not GROQ_API_KEY:
        print("Missing GROQ API Key")
        return None

    session = await get_session()

    # Build message content
    content_block = []

    if prompt:
        content_block.append({"type": "text", "text": prompt})

    if image_bytes is not None:
        img_url = encode_image_bytes(image_bytes, mime=image_mime)
        content_block.append({
            "type": "input_image",
            "image_url": img_url
        })

    # Default to text-only block if no image provided
    if not content_block:
        content_block = [{"role": "user", "content": prompt}]

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": content_block
            }
        ],
        "temperature": temperature,
        "max_tokens": 500
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    backoff = 1
    for attempt in range(1, retries + 1):
        try:
            async with session.post(GROQ_URL, headers=headers, json=payload, timeout=60) as resp:
                text = await resp.text()

                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]

                print("\n===== GROQ ERROR =====")
                print(f"Attempt {attempt}, Status: {resp.status}")
                print(clean_log(text))
                print("================================\n")

                if resp.status in (401, 403):
                    return None
                if resp.status == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 8)
                    continue

        except Exception as e:
            print(f"Exception on attempt {attempt}: {clean_log(str(e))}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 8)

    return None
