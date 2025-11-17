print("Starting bot.py...")

import os
import asyncio
import random
import re
from datetime import datetime, timedelta
import discord
from discord import Message
from dotenv import load_dotenv

from memory import MemoryManager
from humanizer import humanize_response, maybe_typo, is_roast_trigger
from gemini_client import call_gemini
from bot_chess import OnlineChessEngine  # chess engine

# ---------------- LOAD ENV ----------------
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEN_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_NAME = os.getenv("BOT_NAME", "Codunot")
BOT_USER_ID = 1435987186502733878
CONTEXT_LENGTH = int(os.getenv("CONTEXT_LENGTH", "18"))
OWNER_ID = 1220934047794987048

if not DISCORD_TOKEN or not GEN_API_KEY:
    raise SystemExit("Set DISCORD_TOKEN and GEMINI_API_KEY before running.")

# ---------------- DISCORD CLIENT ----------------
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)

# ---------------- MEMORY & QUEUES ----------------
memory = MemoryManager(limit=60, file_path="codunot_memory.json")
message_queue = asyncio.Queue()

# ---------------- BOT MODES ----------------
MAX_MSG_LEN = 3000
channel_modes = {}  # channel_id -> mode
channel_mutes = {}  # channel_id -> mute_until
channel_chess = {}  # channel_id -> chess mode active
chess_engine = OnlineChessEngine()  # chess engine

# ---------------- HELPERS ----------------
def format_duration(num: int, unit: str) -> str:
    unit_map = {"s": "second", "m": "minute", "h": "hour", "d": "day"}
    name = unit_map.get(unit, "minute")
    return f"{num} {name}s" if num > 1 else f"1 {name}"

async def send_long_message(channel, text):
    """Send a message in chunks if too long."""
    while len(text) > 0:
        chunk = text[:MAX_MSG_LEN]
        text = text[MAX_MSG_LEN:]
        if len(text) > 0:
            chunk += "..."
            text = "..." + text
        await message_queue.put((channel, chunk))

async def process_queue():
    """Continuously send messages from the queue."""
    while True:
        channel, content = await message_queue.get()
        try:
            await channel.send(content)
        except:
            pass
        await asyncio.sleep(0.02)

async def send_human_reply(channel, reply_text, limit=None):
    """Send a reply with optional character limit."""
    if limit:
        reply_text = reply_text[:limit].rstrip()
    if len(reply_text) > MAX_MSG_LEN:
        await send_long_message(channel, reply_text)
    else:
        await message_queue.put((channel, reply_text))

def humanize_and_safeify(text, short=False):
    """Make responses slightly human-like and safe."""
    if not isinstance(text, str):
        text = str(text)
    text = text.replace(" idk", "").replace(" *nvm", "")
    if random.random() < 0.1:
        text = maybe_typo(text)
    if short:
        text = text.strip()[:100]
        if not text.endswith(('.', '!', '?')):
            text += '.'
    return text

# ---------------- PROMPTS ----------------
def build_general_prompt(mem_manager, channel_id, mode):
    recent = mem_manager.get_recent_flat(channel_id, n=CONTEXT_LENGTH)
    history_text = "\n".join(recent)
    persona_self_protect = "Never roast or attack yourself (Codunot). If asked to roast Codunot, gently refuse."
    if mode == "serious":
        persona = "You are Codunot, a precise and knowledgeable helper. No emojis or slang."
    else:
        persona = "You are Codunot, a playful, witty friend. Reply in 1–2 lines. Use slang, emojis."
    return f"{persona}\n{persona_self_protect}\nMy user ID is {BOT_USER_ID}.\n\nRecent chat:\n{history_text}\n\nReply as Codunot:"

def build_roast_prompt(mem_manager, channel_id, target_name, mode):
    if str(target_name).lower() in ["codunot", str(BOT_USER_ID)]:
        return "Refuse to roast yourself in a funny way."
    recent = mem_manager.get_recent_flat(channel_id, n=12)
    history_text = "\n".join(recent)
    if mode == "roast":
        persona = "You are Codunot, a brutal roast-master. Short 1–2 line roast, max 100 chars."
    else:
        persona = "Friendly, playful one-line roast with emojis (max 100 chars)."
    return f"{persona}\nTarget: {target_name}\nRecent chat:\n{history_text}\nRoast:"

# ---------------- ON READY ----------------
@client.event
async def on_ready():
    print(f"{BOT_NAME} is ready!")
    asyncio.create_task(process_queue())

# ---------------- API CALL WITH RATE LIMIT ----------------
async def safe_call_gemini(prompt):
    """Call Gemini with automatic delay if rate-limited (429)."""
    while True:
        try:
            resp = await call_gemini(prompt)
            return resp
        except Exception as e:
            # Check for 429, sleep, retry silently
            if "429" in str(e):
                await asyncio.sleep(1)  # short delay
            else:
                return "Hmm, something went wrong 😅"

# ---------------- ON MESSAGE ----------------
@client.event
async def on_message(message: Message):
    if message.author == client.user:
        return

    now = datetime.utcnow()
    is_dm = isinstance(message.channel, discord.DMChannel)
    chan_id = str(message.channel.id) if not is_dm else f"dm_{message.author.id}"

    # Always respond in DMs, or in server if bot mentioned
    if not is_dm and client.user not in message.mentions:
        return

    # ---------- defaults ----------
    if chan_id not in channel_modes:
        channel_modes[chan_id] = "funny"
    if chan_id not in channel_mutes:
        channel_mutes[chan_id] = None
    if chan_id not in channel_chess:
        channel_chess[chan_id] = False
    mode = channel_modes[chan_id]

    # ---------- OWNER COMMANDS ----------
    if message.author.id == OWNER_ID:
        if message.content.startswith("!quiet"):
            match = re.search(r"!quiet (\d+)([smhd])", message.content.lower())
            if match:
                num = int(match.group(1))
                unit = match.group(2)
                seconds = num * {"s":1, "m":60, "h":3600, "d":86400}[unit]
                channel_mutes[chan_id] = datetime.utcnow() + timedelta(seconds=seconds)
                await send_human_reply(message.channel, f"I'll stop yapping for {format_duration(num, unit)}!")
            return
        if message.content.startswith("!speak"):
            channel_mutes[chan_id] = None
            await send_human_reply(message.channel, "I'm back! 😎")
            return

    # ---------- check mute ----------
    if channel_mutes[chan_id] and now < channel_mutes[chan_id]:
        return

    memory.add_message(chan_id, message.author.display_name, message.content)
    content_lower = message.content.lower()

    # ---------- MODE SWITCH ----------
    if "!roastmode" in content_lower:
        channel_modes[chan_id] = "roast"
        await send_human_reply(message.channel, "🔥 Roast mode ACTIVATED!")
        return
    if "!funmode" in content_lower:
        channel_modes[chan_id] = "funny"
        await send_human_reply(message.channel, "😎 Fun mode activated!")
        return
    if "!seriousmode" in content_lower:
        channel_modes[chan_id] = "serious"
        await send_human_reply(message.channel, "🤓 Serious mode activated!")
        return
    mode = channel_modes[chan_id]

    # ---------- HELP ----------
    help_keywords = ["mode", "modes", "commands", "what can you do", "how to use"]
    if any(kw in message.content.lower() for kw in help_keywords):
        help_text = (
            "I have 4 modes:\n"
            "1️⃣ Fun mode: !funmode — playful, light roasts, emojis allowed.\n"
            "2️⃣ Roast mode: !roastmode — savage 1–2 line roasts.\n"
            "3️⃣ Serious mode: !seriousmode — factual, direct, no slang.\n"
            "4️⃣ Chess mode: !chessmode — play chess or ask chess questions.\n"
            "Use the commands above to switch modes!"
        )
        await send_human_reply(message.channel, help_text)
        return

    # ---------- CHESS MODE ----------
    if message.content.lower().startswith("!chessmode"):
        channel_chess[chan_id] = True
        chess_engine.new_board(chan_id)
        await send_human_reply(message.channel, "♟️ Chess mode ACTIVATED! Play or ask chess questions.")
        return

    if channel_chess.get(chan_id):
        move_text = message.content.strip()
        board = chess_engine.get_board(chan_id)
        try:
            # Try SAN move first
            move = board.parse_san(move_text)
            board.push(move)
            bot_move = chess_engine.get_best_move(chan_id)
            if bot_move:
                chess_engine.push_uci(chan_id, bot_move)
                await send_human_reply(message.channel, f"My move: `{bot_move}`")
            return
        except ValueError:
            # Treat as chess knowledge question
            prompt = f"You are a chess expert. Answer briefly: {move_text}"
            raw_resp = await safe_call_gemini(prompt)
            reply = humanize_and_safeify(raw_resp, short=True)
            await send_human_reply(message.channel, reply)
            return

    # ---------- ROAST/FUN ----------
    short_mode = mode in ["funny", "roast"]
    roast_target = is_roast_trigger(message.content)
    if roast_target:
        memory.set_roast_target(chan_id, roast_target)
    target = memory.get_roast_target(chan_id)
    if target:
        roast_prompt = build_roast_prompt(memory, chan_id, target, mode)
        raw = await safe_call_gemini(roast_prompt)
        reply = humanize_and_safeify(raw, short=short_mode)
        await send_human_reply(message.channel, reply, limit=100 if short_mode else None)
        memory.add_message(chan_id, BOT_NAME, reply)
        return

    # ---------- GENERAL CHAT ----------
    prompt = build_general_prompt(memory, chan_id, mode)
    raw_resp = await safe_call_gemini(prompt)
    reply = humanize_and_safeify(raw_resp, short=short_mode)
    await send_human_reply(message.channel, reply, limit=100 if short_mode else None)
    memory.add_message(chan_id, BOT_NAME, reply)
    memory.persist()

# ---------------- CLEANUP ----------------
async def _cleanup():
    await memory.close()
    await asyncio.sleep(0.1)

# ---------------- RUN ----------------
def run():
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run()
