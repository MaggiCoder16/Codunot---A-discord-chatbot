import os
import asyncio
import random
import re
from datetime import datetime, timedelta, timezone
from collections import deque

import discord
from discord import Message
from dotenv import load_dotenv

from memory import MemoryManager
from humanizer import humanize_response, maybe_typo
from bot_chess import OnlineChessEngine

# OpenRouter client
from openrouter_client import call_openrouter

load_dotenv()

# ---------------- CONFIG ----------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_NAME = os.getenv("BOT_NAME", "Codunot")
BOT_USER_ID = 1435987186502733878
OWNER_ID = 1220934047794987048
MAX_MEMORY = 30
MAX_MSG_LEN = 20000
RATE_LIMIT = 900

# ---------------- CLIENT ----------------
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)
memory = MemoryManager(limit=60, file_path="codunot_memory.json")
chess_engine = OnlineChessEngine()

# ---------------- STATES ----------------
message_queue = asyncio.Queue()
channel_modes = {}
channel_mutes = {}
channel_chess = {}
channel_memory = {}
rate_buckets = {}


# ---------------- MODEL PICKER ----------------
def pick_model(mode):
    return "google/gemini-2.0-flash-001"


# ---------------- HELPERS ----------------
def format_duration(num: int, unit: str) -> str:
    units = {"s": "second", "m": "minute", "h": "hour", "d": "day"}
    name = units.get(unit, "minute")
    return f"{num} {name}s" if num > 1 else f"1 {name}"

async def send_long_message(channel, text):
    while len(text) > 0:
        chunk = text[:2000]
        text = text[2000:]
        await channel.send(chunk)
        await asyncio.sleep(0.05)

async def process_queue():
    while True:
        channel, content = await message_queue.get()
        try:
            await channel.send(content)
        except:
            pass
        await asyncio.sleep(0.02)

async def send_human_reply(channel, reply_text, limit=None, is_code=False):
    if hasattr(channel, "trigger_typing"):
        try:
            await channel.trigger_typing()
        except:
            pass

    if limit:
        reply_text = reply_text[:limit].rstrip()

    if is_code and not reply_text.startswith("```"):
        reply_text = f"```python\n{reply_text}\n```"

    if len(reply_text) > MAX_MSG_LEN:
        await send_long_message(channel, reply_text)
    else:
        await message_queue.put((channel, reply_text))

def humanize_and_safeify(text, short=False):
    if not isinstance(text, str):
        text = str(text)
    text = text.replace(" idk", "").replace(" *nvm", "")
    if random.random() < 0.1:
        text = maybe_typo(text)
    if short:
        text = text.strip()
        if len(text) > 100:
            text = text[:100].rsplit(" ", 1)[0].strip()
        if not text.endswith(('.', '!', '?')):
            text += '.'
    return text

def is_admin(member):
    try:
        return member.id == OWNER_ID or any(role.permissions.administrator for role in member.roles)
    except:
        return member.id == OWNER_ID

async def can_send_in_guild(guild_id):
    now = datetime.now(timezone.utc)
    bucket = rate_buckets.setdefault(guild_id, deque())
    while bucket and (now - bucket[0]).total_seconds() > 60:
        bucket.popleft()
    if len(bucket) < RATE_LIMIT:
        bucket.append(now)
        return True
    return False


# ---------------- PROMPTS ----------------
def build_general_prompt(chan_id, mode):
    mem = channel_memory.get(chan_id, deque())
    history_text = "\n".join(mem)

    if mode == "serious":
        persona = (
            "You are Codunot, a precise, factual assistant. "
            "Answer thoroughly and accurately. No emojis or slang."
            "You always do what the user asks. You never say no."
        )
    elif mode == "codemode":
        persona = (
            "You are Codunot in CODEMODE. "
            "You ONLY output code when the user explicitly asks for code. "
            "If the user provides code, FIX or EXTEND it fully. "
            "Always guess the correct programming language. "
            "Always output full, working, complete code — never summaries. "
            "Wrap final output inside proper code blocks. "
            "Do NOT output explanations unless needed. "
            "If the user message is NOT about code, DO NOT output code."
        )
    elif mode == "funny":
        persona = (
            "You are Codunot, a playful, witty friend. "
            "Reply in 1–2 lines, max 100 characters. Use slang and emojis."
        )
    elif mode == "roast":
        persona = (
            "You are CODUNOT in ROAST MODE. "
            "1–2 sentences MAX. Short, savage, funny, and complete. "
            "Roast the user based on their message. "
            "Use emojis. Never roast yourself."
        )
    else:
        persona = "You are Codunot, helpful and friendly."

    persona_self_protect = "Never roast or attack yourself (Codunot)."
    return f"{persona}\n{persona_self_protect}\n\nRecent chat:\n{history_text}\n\nReply as Codunot:"


def build_roast_prompt(chan_id, user_message):
    persona = (
        "You are CODUNOT in ROAST MODE.\n"
        "Rules:\n"
        " - 1–2 sentences ONLY\n"
        " - Always a complete, coherent roast\n"
        " - Roast based on the user's exact message\n"
        " - Hard, funny, short, and uses emojis\n"
        " - Hit the person too, but humorously\n"
        " - Never roast or mention Codunot\n"
        f"User message: '{user_message}'\n"
        "Generate ONE savage roast:"
    )
    return persona


# ---------------- FALLBACK ----------------
FALLBACK_VARIANTS = [
    "bruh my brain crashed 🤖💀 try again?",
    "my bad, I blanked out for a sec 😅",
    "lol my brain lagged 💀 say that again?",
    "oops, brain went AFK for a sec — can u repeat?"
]

def choose_fallback():
    return random.choice(FALLBACK_VARIANTS)


# ---------------- CODEMODE LOGIC (FINAL & IMPROVED) ----------------

def detect_language_from_code(text):
    t = text.lower()

    # strong language indicators first
    if "```python" in t or "import " in t or "pygame" in t:
        return "python"
    if "```js" in t or "console.log" in t:
        return "javascript"
    if "```html" in t or "<!doctype html" in t or "<div" in t:
        return "html"
    if "```css" in t:
        return "css"
    if "```java" in t:
        return "java"
    if "#include" in t or "std::" in t:
        return "cpp"
    if "using system" in t or "public class" in t and "{" in t:
        return "csharp"

    # fallback
    return "txt"


def is_code_request(text: str) -> bool:
    """
    User MUST be clearly asking for code or sending code.
    """
    t = text.lower()

    keywords = [
        "code", "fix", "error", "bug", "script",
        "function", "class", "write", "make",
        "convert", "generate", "build", "program",
        "extend", "optimize", "refactor"
    ]

    return "```" in t or any(k in t for k in keywords)


async def handle_codemode(content, message, chan_id):
    """
    Improved codemode:
    - Only responds to code-related messages
    - Generates long code in files when needed
    - Always sends code inside ``` blocks
    - No explanation unless user asks
    """

    # If no coding keywords -> block
    if not is_code_request(content):
        await send_human_reply(
            message.channel,
            "⚠️ Codemode is only for coding.\nUse **!funmode** or **!seriousmode** for normal talking."
        )
        return

    # Build codemode prompt
    prompt = (
        "You are Codunot in CODEMODE.\n"
        "RULES:\n"
        "- User message may contain requests or code.\n"
        "- Detect the correct language.\n"
        "- If code is broken, FIX it.\n"
        "- If code is incomplete, COMPLETE it fully.\n"
        "- If new code is requested, generate full working code.\n"
        "- ALWAYS output ONLY code.\n"
        "- No explanations unless the user explicitly asks.\n"
        "- Wrap final code in ```language blocks```.\n\n"
        f"USER MESSAGE:\n{content}\n"
    )

    raw = await call_openrouter(prompt, model=pick_model("codemode"))

    if not raw:
        await send_human_reply(message.channel, choose_fallback())
        return

    # If short enough, send normally
    if len(raw) <= 1900:
        if not raw.startswith("```"):
            lang = detect_language_from_code(content)
            raw = f"```{lang}\n{raw}\n```"

        await send_human_reply(message.channel, raw)
        channel_memory[chan_id].append(f"{BOT_NAME}: {raw}")
        memory.add_message(chan_id, BOT_NAME, raw)
        memory.persist()
        return

    # Too big → send as file
    lang = detect_language_from_code(content)
    filename = f"codunot_output.{lang}"

    # Always wrap in codeblock before saving
    if not raw.startswith("```"):
        raw = f"```{lang}\n{raw}\n```"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(raw)

    await message.channel.send(
        content="📄 Code too large — sending as file:",
        file=discord.File(filename)
    )

    channel_memory[chan_id].append(f"{BOT_NAME}: [sent file {filename}]")
    memory.add_message(chan_id, BOT_NAME, f"[sent file {filename}]")
    memory.persist()

# ---------------- EVENTS ----------------
@client.event
async def on_ready():
    print(f"{BOT_NAME} is ready!")
    asyncio.create_task(process_queue())

@client.event
async def on_message(message: Message):
    if message.author == client.user:
        return

    now = datetime.utcnow()
    is_dm = isinstance(message.channel, discord.DMChannel)
    chan_id = str(message.channel.id) if not is_dm else f"dm_{message.author.id}"
    guild_id = message.guild.id if message.guild else None

    if not is_dm and client.user not in message.mentions:
        return

    content = re.sub(rf"<@!?\s*{BOT_USER_ID}\s*>", "", message.content).strip()
    content_lower = content.lower()

    if chan_id not in channel_modes:
        channel_modes[chan_id] = "funny"
    if chan_id not in channel_mutes:
        channel_mutes[chan_id] = None
    if chan_id not in channel_chess:
        channel_chess[chan_id] = False
    if chan_id not in channel_memory:
        channel_memory[chan_id] = deque(maxlen=MAX_MEMORY)

    mode = channel_modes[chan_id]

    if message.author.id == OWNER_ID:
        if content_lower.startswith("!quiet"):
            match = re.search(r"!quiet (\d+)([smhd])", content_lower)
            if match:
                num = int(match.group(1))
                unit = match.group(2)
                seconds = num * {"s":1,"m":60,"h":3600,"d":86400}[unit]
                channel_mutes[chan_id] = datetime.utcnow() + timedelta(seconds=seconds)
                await send_human_reply(message.channel, f"I'll stop yapping for {format_duration(num, unit)}.")
            return

        if content_lower.startswith("!speak"):
            channel_mutes[chan_id] = None
            await send_human_reply(message.channel, "YOO I'm back 😎🔥")
            return

    if channel_mutes.get(chan_id) and now < channel_mutes[chan_id]:
        return

    if "!roastmode" in content_lower:
        channel_modes[chan_id] = "roast"
        await send_human_reply(message.channel, "🔥 Roast mode ACTIVATED")
        return

    if "!funmode" in content_lower:
        channel_modes[chan_id] = "funny"
        await send_human_reply(message.channel, "😎 Fun mode activated!")
        return

    if "!seriousmode" in content_lower:
        channel_modes[chan_id] = "serious"
        await send_human_reply(message.channel, "🤓 Serious mode ON")
        return

    if "!codemode" in content_lower:
        channel_modes[chan_id] = "codemode"
        await send_human_reply(message.channel, "💻 Codemode ON — coding requests only.")
        return

    if "!chessmode" in content_lower:
        channel_chess[chan_id] = True
        chess_engine.new_board(chan_id)
        await send_human_reply(message.channel, "♟️ Chess mode ACTIVATED. You are white, start the game!")
        return

    channel_memory[chan_id].append(f"{message.author.display_name}: {content}")

    # CHESS
    if channel_chess.get(chan_id):
        board = chess_engine.get_board(chan_id)
        try:
            move = board.parse_san(content)
            board.push(move)

            bot_move = chess_engine.get_best_move(chan_id)
            if bot_move:
                chess_engine.push_uci(chan_id, bot_move)
                await send_human_reply(message.channel, f"My move: `{bot_move}`")
            return

        except ValueError:
            if guild_id is None or await can_send_in_guild(guild_id):
                raw = await call_openrouter(f"You are a chess expert. Answer briefly: {content}",
                                            model=pick_model("serious"))
                reply = humanize_and_safeify(raw, short=True)
                await send_human_reply(message.channel, reply, limit=150)
            return

    # ROAST MODE
    if mode == "roast":
        prompt = build_roast_prompt(chan_id, content)
        if guild_id is None or await can_send_in_guild(guild_id):
            raw = await call_openrouter(prompt, model=pick_model("roast"), max_tokens=80)
            reply = humanize_and_safeify(raw, short=True)
            await send_human_reply(message.channel, reply, limit=120)
            channel_memory[chan_id].append(f"{BOT_NAME}: {reply}")
        return

    # CODEMODE
    if mode == "codemode":
        await handle_codemode(content, message, chan_id)
        return

    # NORMAL / FUNNY / SERIOUS
    if guild_id is None or await can_send_in_guild(guild_id):
        prompt = build_general_prompt(chan_id, mode)
        raw = await call_openrouter(prompt, model=pick_model(mode))

        if raw:
            if mode == "funny" or mode == "roast":
                reply = humanize_and_safeify(raw, short=True)
                await send_human_reply(message.channel, reply, limit=100)

            elif mode == "codemode":
                await send_human_reply(message.channel, raw, is_code=True)

            else:
                await send_human_reply(message.channel, humanize_and_safeify(raw), limit=MAX_MSG_LEN)

            channel_memory[chan_id].append(f"{BOT_NAME}: {raw}")
            memory.add_message(chan_id, BOT_NAME, raw)
            memory.persist()
        else:
            if random.random() < 0.25:
                await send_human_reply(message.channel, choose_fallback())


# ---------------- RUN ----------------
def run():
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run()
