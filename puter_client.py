import asyncio
import os
import aiohttp
from puter import PuterAI, PuterAuthError, PuterAPIError
from putergenai import PuterClient

PUTER_USERNAME = os.getenv("PUTER_USERNAME", "")
PUTER_PASSWORD = os.getenv("PUTER_PASSWORD", "")

puter_chat_client = None
puter_genai_client = None


def _get_chat_client():
    global puter_chat_client

    if puter_chat_client is None:
        if not PUTER_USERNAME or not PUTER_PASSWORD:
            raise Exception("PUTER_USERNAME and PUTER_PASSWORD must be set")

        puter_chat_client = PuterAI(
            username=PUTER_USERNAME,
            password=PUTER_PASSWORD
        )

        if not puter_chat_client.login():
            raise PuterAuthError("Failed to login to Puter")

    return puter_chat_client


async def _get_genai_client():
    global puter_genai_client

    if puter_genai_client is None:
        if not PUTER_USERNAME or not PUTER_PASSWORD:
            raise Exception("PUTER_USERNAME and PUTER_PASSWORD must be set")

        puter_genai_client = PuterClient()
        await puter_genai_client.login(PUTER_USERNAME, PUTER_PASSWORD)

    return puter_genai_client

async def puter_generate_image(
    prompt: str,
    model: str = "gpt-image-1.5",
    quality: str = "low"
) -> bytes:

    client = await _get_genai_client()

    options = {
        "model": model,
        "quality": quality
    }

    image_url = await client.ai_txt2img(prompt, options=options)

    if not image_url:
        raise Exception("No image URL returned")

    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            if resp.status != 200:
                raise Exception(f"Image download failed: {resp.status}")
            return await resp.read()

async def puter_text_to_speech(
    text: str,
    voice: str = "21m00Tcm4TlvDq8ikWAM",
    model: str = "eleven_multilingual_v2"
) -> bytes:

    if len(text) > 3000:
        raise ValueError("Text must be under 3000 characters")

    client = await _get_genai_client()

    options = {
        "provider": "elevenlabs",
        "model": model,
        "voice": voice
    }

    audio_bytes = await client.ai_txt2speech(text, options=options)

    return audio_bytes

async def puter_chat(messages: list):

    loop = asyncio.get_running_loop()

    def _generate():
        client = _get_chat_client()
        user_message = messages[-1]["content"]
        return client.chat(user_message)

    return await loop.run_in_executor(None, _generate)
