import aiohttp
import os
import asyncio

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Pick a good default model
MODEL = "meta-llama/llama-3.2-3b-instruct"

# Reuse one aiohttp session
SESSION: aiohttp.ClientSession | None = None


async def get_session():
    global SESSION
    if SESSION is None or SESSION.closed:
        SESSION = aiohttp.ClientSession()
    return SESSION


async def call_openrouter(prompt: str, max_tokens=220, retries=4) -> str:
    """
    Safe OpenRouter call w/ retries, backoff, no timeouts, no crashes.
    """

    if OPENROUTER_API_KEY is None:
        return "OpenRouter API key missing."

    session = await get_session()

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
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

                # Handle rate-limit gracefully
                if resp.status == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 8)
                    continue

                # Other server errors
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
