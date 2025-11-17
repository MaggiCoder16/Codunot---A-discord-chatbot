import aiohttp
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# default fallback model (not used often)
DEFAULT_MODEL = "google/gemini-flash-1.5"

SESSION: aiohttp.ClientSession | None = None


async def get_session():
    global SESSION
    if SESSION is None or SESSION.closed:
        SESSION = aiohttp.ClientSession()
    return SESSION


async def call_openrouter(prompt: str, model: str = None, max_tokens=512, retries=4) -> str:
    """
    Model can be overridden per call.
    Better generation settings so it stops cutting sentences.
    """
    if OPENROUTER_API_KEY is None:
        return "OpenRouter API key missing."

    session = await get_session()

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.8,
        "top_p": 0.95,
        "frequency_penalty": 0.2,
        "safe_prompt": False
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://example.com",
        "X-Title": "Codunot Discord Bot"
    }

    backoff = 1

    for attempt in range(1, retries + 1):
        try:
            async with session.post(
                OPENROUTER_URL, headers=headers, json=payload, timeout=15
            ) as resp:

                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]

                if resp.status == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 8)
                    continue

                text = await resp.text()
                print(f"[OpenRouter ERROR {resp.status}] {text}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 8)

        except asyncio.TimeoutError:
            print(f"[OpenRouter TIMEOUT] attempt {attempt}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 8)

        except Exception as e:
            print(f"[OpenRouter EXCEPTION] {e}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 8)

    return "Sorry, I couldn't think of a response right now 😅"
