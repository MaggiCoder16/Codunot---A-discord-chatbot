# gemini_client.py
import aiohttp
from config import GEMINI_API_KEY

# Correct Google Generative Language API endpoint
API_URL = "https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generate"

async def call_gemini(prompt: str) -> str:
    """
    Call Google Gemini / Text-Bison API asynchronously.
    Returns generated text, or a safe placeholder if the API/network fails.
    """
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }

    json_data = {
        "prompt": {"text": prompt},  # correct format
        "temperature": 0.7,
        "max_output_tokens": 150
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    print(f"[Gemini API] HTTP error: {resp.status}")
                    return "(couldn't generate response)"
                data = await resp.json()
                return data.get("candidates", [{}])[0].get("content", "(empty response)")
    except aiohttp.ClientConnectorError as e:
        print(f"[Gemini API] Connection error: {e}")
        return "(network error)"
    except Exception as e:
        print(f"[Gemini API] Unexpected error: {e}")
        return "(unexpected error)"
