import aiohttp
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Retrieve the API key from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"  # Correct API endpoint for chat completions

SESSION: aiohttp.ClientSession | None = None

def clean_log(text: str) -> str:
    """Sanitize the log by removing sensitive information like API keys."""
    if not text:
        return text
    if GROQ_API_KEY:
        text = text.replace(GROQ_API_KEY, "***")
    return text

async def get_session():
    """Get an aiohttp session, creating one if necessary."""
    global SESSION
    if SESSION is None or SESSION.closed:
        SESSION = aiohttp.ClientSession()
    return SESSION

async def call_groq(prompt: str, model: str, temperature: float = 1.0, retries: int = 4) -> str | None:
    """Call the GROQ API to generate text or perform tasks based on the prompt."""
    if not GROQ_API_KEY:
        print("Missing GROQ API Key")
        return None

    session = await get_session()

    # Build the request payload for the OpenAI-compatible endpoint
    payload = {
        "model": model,  # Model: Llama 3.3 70B or Llama 4 Scout (for vision)
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 200,  # You can adjust the max tokens if needed
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    backoff = 1
    for attempt in range(1, retries + 1):
        try:
            # Make the request to the GROQ API
            async with session.post(GROQ_URL, headers=headers, json=payload, timeout=60) as resp:
                text = await resp.text()
                
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]  # Assuming the response structure

                print("\n===== GROQ ERROR =====")
                print(f"Attempt {attempt}, Status: {resp.status}")
                print(clean_log(text))
                print("================================\n")

                # Handle specific status codes
                if resp.status == 401 or resp.status == 403:
                    return None  # Unauthorized access
                if resp.status == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 8)  # Exponential backoff for rate limiting
                    continue

        except Exception as e:
            print(f"Exception on attempt {attempt}: {clean_log(str(e))}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 8)  # Exponential backoff

    return None
