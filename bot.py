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
from gemini_client import call_gemini  # your Gemini API wrapper

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEN_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_NAME = os.getenv("BOT_NAME", "Codunot")
BOT_USER_ID = 1435987186502733878
CONTEXT_LENGTH = int(os.getenv("CONTEXT_LENGTH", "18"))
MAX_MSG_LEN = 6700

if not DISCORD_TOKEN or not GEN_API_KEY:
    raise SystemExit("Set DISCORD_TOKEN and GEMINI_API_KEY before running.")

intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)

memory = MemoryManager(limit=60, file_path="codunot_memory.json")

# ---------------- BOT MODES ----------------
MODES = {"funny": True, "roast": False, "serious": False}

# ---------------- OWNER QUIET/SPEAK ----------------
OWNER_ID = 1220934047794987048
owner_mute_until = None

# ---------- allowed channels ----------
BOT_CHANNEL = 1439269712373485589        # talk-with-bots
GENERAL_CHANNEL = 1436339326509383820   # general (Open to All)
SERVER_ID = 1435926772972519446         # RoyalRacer Fans

# ---------- helper functions ----------
def format_duration(num: int, unit: str) -> str:
    unit_map = {"s": "second", "m": "minute", "h": "hour", "d": "day"}
    name = unit_map.get(unit, "minute")
    return f"{num} {name}s" if num > 1 else f"1 {name}"

async def send_long_message(channel, text):
    MAX_LEN = MAX_MSG_LEN
    while len(text) > 0:
        chunk = text[:MAX_LEN]
        text = text[MAX_LEN:]
        if len(text) > 0:
            chunk += "..."
            text = "..." + text
        await channel.send(chunk)

async def send_human_reply(channel, reply_text):
    if len(reply_text) > MAX_MSG_LEN:
        await send_long_message(channel, reply_text)
    else:
        await channel.send(reply_text)

def humanize_and_safeify(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.replace(" idk", "").replace(" *nvm", "")
    if random.random() < 0.1 and not MODES["serious"]:
        text = maybe_typo(text)
    # --- SHORT REPLIES FOR ROAST/FUN ---
    if MODES["roast"] or MODES["funny"]:
        max_len = 100
        if len(text) > max_len:
            end = text[:max_len].rfind(".")
            if end != -1:
                text = text[:end+1]
            else:
                text = text[:max_len].rstrip()
        return text
    return text[:MAX_MSG_LEN]

# ---------- PROMPTS ----------
def build_general_prompt(mem_manager, channel_id):
    recent = mem_manager.get_recent_flat(channel_id, n=CONTEXT_LENGTH)
    history_text = "\n".join(recent)
    persona_self_protect = (
        "Never roast or attack yourself (Codunot). "
        "If asked to roast Codunot, gently refuse or redirect."
    )
    if MODES["serious"]:
        persona = (
            "You are Codunot, a precise and knowledgeable helper. "
            "You answer with direct factual information. No emojis, no slang."
        )
    elif MODES["roast"]:
        persona = (
            "You are Codunot, a savage roast-master. "
            "NEVER roast yourself. Only roast non-bot users. "
            "Roasts are nuclear-level, offensive but NOT targeting protected classes."
        )
    else:
        persona = (
            "You are Codunot, a playful, funny Discord friend. "
            "Light roasts, friendly jokes, emojis allowed."
        )
    return (
        f"{persona}\n"
        f"{persona_self_protect}\n"
        f"My user ID is {BOT_USER_ID}.\n"
        f"If asked 'who made you', ALWAYS answer: '@aarav_2022 (ID: 1220934047794987048) made me.'\n\n"
        f"Recent chat:\n{history_text}\n\nReply as Codunot:"
    )

def build_roast_prompt(mem_manager, channel_id, target_name):
    if str(target_name).lower() in ["codunot", str(BOT_USER_ID)]:
        return "Refuse to roast yourself in a funny way."
    recent = mem_manager.get_recent_flat(channel_id, n=12)
    history_text = "\n".join(recent)
    if MODES["roast"]:
        persona = (
            "You are Codunot, a feral, brutal roast-master. "
            "Roast HARD. 1–3 brutal lines. No protected classes. No self-roasting."
        )
    else:
        persona = "Friendly, playful one-line roast with emojis."
    return f"{persona}\nTarget: {target_name}\nChat:\n{history_text}\nRoast:"

# ---------- on_ready ----------
@client.event
async def on_ready():
    print(f"{BOT_NAME} is ready!")

# ---------- on_message ----------
@client.event
async def on_message(message: Message):
    global owner_mute_until
    if message.author.id == BOT_USER_ID:
        return

    now = datetime.utcnow()
    if owner_mute_until and now < owner_mute_until:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    allowed = False

    mentioned = client.user in message.mentions or \
        f"<@{client.user.id}>" in message.content or \
        f"<@!{client.user.id}>" in message.content

    replied = False
    if message.reference:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg and ref_msg.author.id == BOT_USER_ID:
                replied = True
        except:
            pass

    # DM → always
    if is_dm:
        allowed = True
    # talk-with-bots → always
    elif message.channel.id == BOT_CHANNEL:
        allowed = True
    # RoyalRacer Fans → general (Open to All)
    elif message.guild and message.guild.id == SERVER_ID and message.channel.id == GENERAL_CHANNEL:
        if mentioned or replied or random.random() < 0.40:
            allowed = True

    if not allowed:
        return

    chan_id = str(message.channel.id) if not is_dm else f"dm_{message.author.id}"
    memory.add_message(chan_id, message.author.display_name, message.content.lower())

    # CREATOR QUESTION
    if "who made you" in message.content.lower():
        await send_human_reply(
            message.channel,
            "@aarav_2022, Discord user ID **1220934047794987048**, made me."
        )
        return

    # OWNER COMMANDS
    if message.content.startswith("!quiet"):
        if message.author.id != OWNER_ID:
            await send_human_reply(
                message.channel,
                f"Only my owner can mute me. Owner: @aarav_2022 (ID {OWNER_ID})."
            )
            return
        match = re.search(r"!quiet (\d+)([smhd])", message.content.lower())
        if match:
            num = int(match.group(1))
            unit = match.group(2)
            seconds = num * {"s":1, "m":60, "h":3600, "d":86400}[unit]
            owner_mute_until = datetime.utcnow() + timedelta(seconds=seconds)
            await send_human_reply(message.channel, f"Quiet for {num}{unit}.")
            return

    if message.content.startswith("!speak"):
        if message.author.id == OWNER_ID:
            owner_mute_until = None
            await send_human_reply(message.channel, "IM BACKKKKKKKKK 🔥🔥🔥")
        return

    # MODE SWITCH
    if message.content.startswith("!roastmode"):
        MODES.update({"roast": True, "serious": False, "funny": False})
        await send_human_reply(message.channel, "🔥 Roast mode activated!")
        return

    if message.content.startswith("!seriousmode"):
        MODES.update({"roast": False, "serious": True, "funny": False})
        await send_human_reply(message.channel, "🤓 Serious mode on.")
        return

    if message.content.startswith("!funmode") or message.content.startswith("!funnymode"):
        MODES.update({"roast": False, "serious": False, "funny": True})
        await send_human_reply(message.channel, "😎 Fun mode activated!")
        return

    # ROAST / FUN MODE
    if MODES["roast"] or MODES["funny"]:
        target = is_roast_trigger(message.content)
        if target:
            memory.set_roast_target(chan_id, target)
        target = memory.get_roast_target(chan_id)
        if target and str(target).lower() not in ["codunot", str(BOT_USER_ID)]:
            try:
                prompt = build_roast_prompt(memory, chan_id, target)
                raw = await call_gemini(prompt)
                reply = humanize_and_safeify(raw)
                await send_human_reply(message.channel, reply)
                memory.add_message(chan_id, BOT_NAME, reply)
            except:
                pass
            return

    # GENERAL RESPONSE
    try:
        prompt = build_general_prompt(memory, chan_id)
        raw = await call_gemini(prompt)
        reply = humanize_and_safeify(raw)
        await send_human_reply(message.channel, reply)
        memory.add_message(chan_id, BOT_NAME, reply)
        memory.persist()
    except:
        pass

# ---------- RUN BOT ----------
def run():
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run()
