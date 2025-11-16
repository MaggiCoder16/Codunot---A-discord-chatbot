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

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEN_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_NAME = os.getenv("BOT_NAME", "Codunot")
CONTEXT_LENGTH = int(os.getenv("CONTEXT_LENGTH", "18"))

if not DISCORD_TOKEN or not GEN_API_KEY:
    raise SystemExit("Set DISCORD_TOKEN and GEMINI_API_KEY before running.")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

memory = MemoryManager(limit=60, file_path="codunot_memory.json")

# ---------------- BOT MODES ----------------
MODES = {"funny": True, "roast": False, "serious": False}
MAX_MSG_LEN = 200
dm_greeted_users = set()  # Track users already greeted in DMs

# ---------- dead chat channels ----------
DEAD_CHAT_CHANNELS = {
    "ROYALRACER FANS": ["testing", "coders", "general"],
    "OPEN TO ALL": ["general"]
}

# ---------- helper to send long messages ----------
async def send_long_message(channel, text, original_message: Message = None):
    while len(text) > 0:
        chunk = text[:MAX_MSG_LEN]
        text = text[MAX_MSG_LEN:]
        if len(text) > 0:
            chunk += "..."
            text = "..." + text
        await channel.send(chunk)

# ---------- send messages ----------
async def send_human_reply(channel, reply_text, original_message: Message = None):
    if len(reply_text) > MAX_MSG_LEN:
        await send_long_message(channel, reply_text, original_message)
    else:
        await channel.send(reply_text)

# ---------- dead channel check ----------
async def dead_channel_check():
    await client.wait_until_ready()
    while True:
        for guild in client.guilds:
            for channel in guild.text_channels:
                if guild.name in DEAD_CHAT_CHANNELS and channel.name in DEAD_CHAT_CHANNELS[guild.name]:
                    last_msg_time = memory.get_last_timestamp(str(channel.id))
                    if not last_msg_time or datetime.utcnow() - last_msg_time > timedelta(hours=1):
                        msg = "its dead in here... anyone wanna talk?"
                        await send_human_reply(channel, msg)
        await asyncio.sleep(3600)  # check every 1 hour

# ---------- start conversation ----------
async def initiate_conversation():
    await client.wait_until_ready()
    for guild in client.guilds:
        for channel in guild.text_channels:
            if guild.name in DEAD_CHAT_CHANNELS and channel.name in DEAD_CHAT_CHANNELS[guild.name]:
                msg = random.choice([
                    "heyyy anyone up for a chat? 😎",
                    "sup guys, let's talk a bit lol",
                    "sup everyone, what's up?"
                ])
                await send_human_reply(channel, msg)

# ---------- build prompts ----------
def build_general_prompt(mem_manager: MemoryManager, channel_id: str) -> str:
    recent = mem_manager.get_recent_flat(channel_id, n=CONTEXT_LENGTH)
    history_text = "\n".join(recent)
    if MODES["serious"]:
        persona = (
            "You are Codunot, friendly, helpful, concise, proper grammar. "
            "No slang, no emoji. Keep replies professional."
        )
    else:
        persona = (
            "You are Codunot, a normal human friend in a Discord chat. "
            "Keep replies short, casual, with slang, emojis, and occasional typos. "
            "Sometimes use 'idk', 'nvm', 'lol', 'bruh'."
        )
    return f"{persona}\n\nRecent chat:\n{history_text}\n\nReply as Codunot (one short message):"

def build_roast_prompt(mem_manager: MemoryManager, channel_id: str, target_name: str | None):
    recent = mem_manager.get_recent_flat(channel_id, n=12)
    history_text = "\n".join(recent)
    target_line = f"Target: {target_name}\n" if target_name else ""
    persona = (
        "You are Codunot, a witty human friend who can roast playfully. "
        "Write a short, HARD roast. "
        "Never attack protected classes or identity. "
        "Use slang and emoji. Keep it short (1-2 lines)."
    )
    return f"{persona}\n{target_line}\nRecent chat:\n{history_text}\n\nGive one HARD roast as Codunot:"

def humanize_and_safeify(text: str) -> str:
    t = maybe_typo(text)
    if random.random() < 0.45 and not MODES["serious"]:
        t = random.choice(["lol", "bruh", "ngl"]) + " " + t
    return t

# ---------- on_ready ----------
@client.event
async def on_ready():
    print(f"{BOT_NAME} is ready!")
    asyncio.create_task(dead_channel_check())
    asyncio.create_task(initiate_conversation())

# ---------- on_message ----------
@client.event
async def on_message(message: Message):
    if message.author == client.user:
        return  # ignore self

    chan_id = str(message.channel.id)
    memory.add_message(chan_id, message.author.display_name, message.content)

    # --- DM GREETING ---
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id not in dm_greeted_users:
            dm_greeted_users.add(message.author.id)
            greeting = (
                "Hi! I'm Codunot, a bot who yaps like a human, but is AI! "
                "I have 3 modes - !roastmode, !funmode, and !seriousmode. "
                "They're pretty self-explanatory, you know? Try them all!"
            )
            await send_human_reply(message.channel, greeting, message)
            return

    # --- MODE COMMANDS ---
    if message.content.startswith("!roastmode"):
        MODES["roast"] = True
        MODES["serious"] = False
        await message.channel.send("😂 Roast/funny mode activated!")
        return
    elif message.content.startswith("!seriousmode"):
        MODES["serious"] = True
        MODES["roast"] = False
        await message.channel.send("🤓 Serious/helpful mode activated!")
        return
    elif message.content.startswith("!funmode"):
        MODES["serious"] = False
        MODES["roast"] = False
        await message.channel.send("😎 Fun casual mode activated!")
        return

    # --- ROAST MODE ---
    if MODES["roast"]:
        roast_target = is_roast_trigger(message.content)
        if roast_target:
            memory.set_roast_target(chan_id, roast_target)

        target = memory.get_roast_target(chan_id)
        if target:
            roast_prompt = build_roast_prompt(memory, chan_id, target)
            try:
                raw = await call_gemini(roast_prompt)
            except:
                return  # silent on API error
            roast_text = humanize_and_safeify(raw)
            # Send in DM to target if possible
            for member in message.channel.members if hasattr(message.channel, "members") else []:
                if member.display_name == target:
                    try:
                        await member.send(roast_text)
                    except:
                        pass  # ignore if DM fails
            await send_human_reply(message.channel, roast_text, message)
            memory.add_message(chan_id, BOT_NAME, roast_text)
            return

    # --- GENERAL CONVERSATION ---
    prompt = build_general_prompt(memory, chan_id)
    try:
        raw_resp = await call_gemini(prompt)
    except:
        return  # silent on API error
    reply = humanize_response(raw_resp) if raw_resp.strip() else random.choice(["lol", "huh?", "true", "omg", "bruh"])
    await send_human_reply(message.channel, reply, message)
    memory.add_message(chan_id, BOT_NAME, reply)
    memory.persist()

# ---------- graceful shutdown ----------
async def _cleanup():
    await memory.close()
    await asyncio.sleep(0.1)

# ---------- run bot ----------
def run():
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run()
