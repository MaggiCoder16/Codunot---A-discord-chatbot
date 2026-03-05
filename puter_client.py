import asyncio
import base64
import re
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
            raise Exception("PUTER_USERNAME and PUTER_PASSWORD must be set in .env")
        
        puter_chat_client = PuterAI(username=PUTER_USERNAME, password=PUTER_PASSWORD)
        if not puter_chat_client.login():
            raise PuterAuthError("Failed to login to Puter (Chat Client)")
    return puter_chat_client

async def _get_genai_client():
    global puter_genai_client
    if puter_genai_client is None:
        if not PUTER_USERNAME or not PUTER_PASSWORD:
            raise Exception("PUTER_USERNAME and PUTER_PASSWORD must be set in .env")
        
        puter_genai_client = PuterClient()
        await puter_genai_client.login(PUTER_USERNAME, PUTER_PASSWORD)
    return puter_genai_client


async def puter_generate_image(prompt: str, model: str = "gpt-image-1.5") -> bytes:
    try:
        client = await _get_genai_client()
        
        image_url = await client.ai_txt2img(prompt, model=model)
        
        if not image_url:
            raise ValueError("No image URL returned from Puter")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to download image: HTTP {resp.status}")
                return await resp.read()
                
    except Exception as e:
        raise Exception(f"Puter ImageGen Error: {e}")

async def puter_text_to_speech(text: str, voice: str = "21m00Tcm4TlvDq8ikWAM", model: str = "eleven_v3") -> bytes:
    if len(text) > 3000:
        raise ValueError("Text must be less than 3000 characters")
    
    try:
        client = await _get_genai_client()
        
        options = {
            "provider": "elevenlabs",
            "model": model,
            "voice": voice
        }
        audio_bytes = await client.ai_txt2speech(text, options=options)
        return audio_bytes
        
    except Exception as e:
        raise Exception(f"Puter TTS Error: {e}")

async def puter_chat(messages: list, model: str = "gpt-5.2-chat", temperature: float = 0.7) -> str:
    loop = asyncio.get_running_loop()
    
    def _generate():
        client = _get_chat_client()
        user_message = messages[-1]['content'] if messages else ""
        response = client.chat(user_message)
        return response
    
    try:
        return await loop.run_in_executor(None, _generate)
    except PuterAuthError as e:
        raise Exception(f"Puter auth error: {e}")
    except PuterAPIError as e:
        raise Exception(f"Puter API error: {e}")
