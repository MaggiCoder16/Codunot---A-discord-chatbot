import random

# ---------- Mood detection ----------
def detect_mood(text):
    text = text.lower()
    if any(w in text for w in ["lol", "lmao", "xd"]):
        return "happy"
    if any(w in text for w in ["sad", "upset", "cry"]):
        return "sad"
    if any(w in text for w in ["angry", "mad", "wtf"]):
        return "angry"
    return "neutral"

# ---------- Typing delays ----------
def human_delay():
    """Random human-like delay for typing."""
    return random.uniform(1.0, 2.0)

def random_typing_delay(length):
    """Return a realistic typing delay based on message length."""
    base = random.uniform(0.05, 0.12)  # seconds per character
    return max(0.3, length * base)

# ---------- Typos and corrections ----------
def maybe_typo(text):
    if random.random() < 0.12:
        pos = random.randint(0, len(text) - 1)
        return text[:pos] + random.choice("asdfghjkl") + text[pos:]
    return text

def maybe_correction(text):
    if random.random() < 0.07:
        return text + " *nvm"
    if random.random() < 0.07:
        return text + " idk"
    return text

def humanize(text):
    """Apply typos and corrections to text."""
    text = maybe_typo(text)
    text = maybe_correction(text)
    return text

def humanize_response(text):
    """Function used by bot.py to humanize Gemini responses."""
    text = maybe_typo(text)
    text = maybe_correction(text)
    return text

# ---------- Roast helpers ----------
def is_roast_trigger(text):
    text = text.lower()
    return any(trigger in text for trigger in ["roast me", "roast him", "roast her", "roast this", "insult me", "diss me"])

def generate_safe_roast(name):
    roasts = [
        f"bro {name} lookin like his wifi runs on hopes n prayers 💀",
        f"{name} talks like their brain is buffering rn",
        f"nah {name} typing like they're on a nokia 2002 😭",
        f"{name} got the energy of a lagging minecraft server",
        f"bro {name} probably gets confused by oxygen"
    ]
    return random.choice(roasts)
