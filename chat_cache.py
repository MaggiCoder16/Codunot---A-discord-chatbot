import json, os
from datetime import datetime
from slang_normalizer import apply_slang_map

CACHE_FILE = "chat_cache.json"

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        return json.load(f)

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def save_interaction(user_text, bot_reply):
    cache = load_cache()

    canonical = apply_slang_map(user_text)

    cache.setdefault(canonical, [])
    cache[canonical].append({
        "reply": bot_reply,
        "time": datetime.utcnow().isoformat()
    })

    save_cache(cache)
