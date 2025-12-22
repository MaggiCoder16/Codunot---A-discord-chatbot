import re

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)   # yooooo -> yoo
    text = re.sub(r"[^\w\s]", "", text)         # remove emojis/punctuation
    text = re.sub(r"\s+", " ", text).strip()
    return text


SLANG_MAP = {

    # ---------------- GREETINGS ----------------
    "yo": "hi", "yoo": "hi", "yooo": "hi", "yoooo": "hi",
    "hey": "hi", "heyy": "hi", "heyyy": "hi", "hiya": "hi",
    "hello": "hi", "hii": "hi", "hiii": "hi",
    "sup": "hi", "wassup": "hi", "whatup": "hi",
    "wsg": "hi", "wsup": "hi", "whatsgood": "hi",
    "hola": "hi", "bonjour": "hi",

    # ---------------- HOW ARE YOU ----------------
    "hru": "how are you", "hr u": "how are you",
    "howru": "how are you", "how r u": "how are you",
    "howyou": "how are you",
    "howdy": "how are you",
    "how you doing": "how are you",
    "how you doin": "how are you",
    "hows life": "how are you",
    "hows it going": "how are you",
    "u good": "how are you",
    "hbu": "how are you",

    # ---------------- QUESTIONS ----------------
    "wyd": "what are you doing",
    "wya": "where are you",
    "wru": "where are you",
    "wdym": "what do you mean",
    "wfym": "what do you mean",
    "wtf": "what the fuck",
    "tf": "the fuck",
    "omg": "oh my god",
    "idk": "i dont know",
    "idc": "i dont care",
    "ikr": "i know right",

    # ---------------- QUICK ACTIONS ----------------
    "brb": "be right back",
    "afk": "away",
    "gtg": "goodbye",
    "g2g": "goodbye",
    "ttyl": "goodbye",
    "omw": "on my way",

    # ---------------- AGREEMENT ----------------
    "ye": "yes", "yea": "yes", "yeah": "yes", "yep": "yes",
    "yuh": "yes", "yah": "yes",
    "nah": "no", "nope": "no", "nuh": "no",
    "bet": "yes",
    "fr": "for real",
    "frfr": "for real",

    # ---------------- LAUGHTER / REMOVE ----------------
    "lol": "", "lmao": "", "lmfao": "", "rofl": "",
    "haha": "", "hehe": "", "xd": "",
    "rip": "", "dead": "",
    "😭": "", "😂": "", "💀": "", "🤣": "",
    "ijbol": "",

    # ---------------- SWEAR / EMPHASIS ----------------
    "damn": "", "bruh": "", "bro": "",
    "fk": "fuck", "fck": "fuck",
    "shit": "shit",

    # ---------------- GRATITUDE ----------------
    "thx": "thanks", "ty": "thanks", "tys": "thanks",
    "tysm": "thanks", "thanku": "thanks",
    "thank you": "thanks", "appreciate it": "thanks",

    # ---------------- APOLOGIES ----------------
    "sry": "sorry", "srry": "sorry",
    "mb": "sorry", "my bad": "sorry",

    # ---------------- GOODBYE ----------------
    "bye": "bye", "cya": "bye", "see ya": "bye",
    "gn": "good night", "gng": "good night",
    "night": "good night",

    # ---------------- LOVE / RELATIONSHIP ----------------
    "ily": "i love you",
    "ilym": "i love you",
    "ilysm": "i love you",
    "ilyb": "i love you",
    "imy": "i miss you",
    "imysm": "i miss you",
    "bae": "partner",
    "bff": "best friend",
    "mbs": "best friend",
    "luv": "love",
    "qt": "cutie",
    "xoxo": "love",

    # ---------------- INTERNET / GEN Z ----------------
    "ngl": "not gonna lie",
    "tbh": "to be honest",
    "imo": "in my opinion",
    "imho": "in my opinion",
    "irl": "in real life",
    "asap": "as soon as possible",
    "fomo": "fear of missing out",
    "iykyk": "inside joke",
    "npc": "npc",
    "goat": "greatest of all time",
    "mid": "average",
    "valid": "good",
    "slay": "good",
    "bussin": "good",
    "rizz": "charisma",
    "aura": "vibe",
    "delulu": "delusional",
    "cooked": "done",
    "crash out": "angry",
    "lock in": "focus",
}


def apply_slang_map(text: str) -> str:
    for slang, meaning in SLANG_MAP.items():
        text = re.sub(rf"\b{re.escape(slang)}\b", meaning, text)
    return normalize_text(text)
