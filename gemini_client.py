# gemini_client.py
import os
import aiohttp
from config import GEMINI_API_KEY

API_URL = "https://api.genai.google/v1beta2/models/text-bison-001:generate"  # example

async def call_gemini(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {
        "prompt": prompt,
        "temperature": 0.7,
        "max_output_tokens": 150
    }

    async with aio
