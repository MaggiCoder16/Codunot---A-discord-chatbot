# gemini_client.py
import aiohttp
from config import GEMINI_API_KEY

# Updated endpoint for Google Generative Language API
API_URL = "https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generate"

async def call_gemini(prompt: str) -> str:
    """
    Call Google Gemini / Text-Bison API asynchronously.
    Returns the generated text, or a safe error message if the API/network fails.
    """
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {
        "prompt": prompt,
        "temperature": 0.7,
        "max_output_tokens": 150
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    print(f"[Gemini API] HTTP error: {resp.status}")
                    return "(api error)"
                data = await resp.json()
                # Usually: data['candidates'][0]['content']
                return data.get("candidates", [{}])[0].get("content", "")
    except aiohttp.ClientConnectorError as e:
        print(f"[Gemini API] Connection error: {e}")
        return "(connection error)"
    except Exception as e:
        print(f"[Gemini API] Unexpected error: {e}")
        return "(unexpected error)"
