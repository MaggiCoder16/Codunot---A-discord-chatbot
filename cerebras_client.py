import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

_client = None


def clean_log(text: str) -> str:
	if not text:
		return text
	if CEREBRAS_API_KEY:
		text = text.replace(CEREBRAS_API_KEY, "***")
	return text


def _get_client():
	"""Return a singleton Cerebras client instance."""
	global _client
	if _client is None:
		from cerebras.cloud.sdk import Cerebras
		_client = Cerebras(api_key=CEREBRAS_API_KEY)
	return _client


async def call_cerebras(
	prompt: str,
	model: str = "gpt-oss-120b",
	temperature: float = 0.2,
	retries: int = 3,
) -> str | None:
	"""
	Call Cerebras API for code testing and fixing.
	Uses gpt-oss-120b by default — intended for code tasks only.
	"""
	if not CEREBRAS_API_KEY:
		print("[CEREBRAS] Missing CEREBRAS_API_KEY")
		return None

	loop = asyncio.get_running_loop()

	backoff = 1
	for attempt in range(1, retries + 1):
		try:
			def _call():
				client = _get_client()
				chat = client.chat.completions.create(
					messages=[{"role": "user", "content": prompt}],
					model=model,
					temperature=temperature,
				)
				return chat.choices[0].message.content if chat.choices else None

			return await loop.run_in_executor(None, _call)

		except Exception as e:
			print(f"[CEREBRAS ERROR] Attempt {attempt}/{retries}: {clean_log(str(e))}")
			if attempt == retries:
				return None
			await asyncio.sleep(backoff)
			backoff = min(backoff * 2, 8)

	return None
