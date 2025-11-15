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
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

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

analyzer = SentimentIntensityAnalyzer()
memory = MemoryManager(limit=60, file_path="codunot_memory.json")

# Modes: "funny" = roast mode, "serious" = normal helpful mode
BOT_MODE = "funny"

# ---------- channels for dead chat messages ----------
DEAD_CHAT_CHANNELS = {
    "ROYALRACER FANS": ["testing", "coders", "general"],
    "OPEN TO ALL": ["general"]
}

# ---------- send messages instantly ----------
async def send_human_reply(channel, reply_text, original_message: Message = None):
    await channel.send(reply_text)

# ---------- build prompts ----------
def build_general_prompt(mem_manager: MemoryManager, channel_id: str) -> str:
    recent = mem_manager.get_recent_flat(channel_id, n=CONTEXT_LENGTH)
    history_text = "\n".join(recent)
    if BOT_MODE == "serious":
        persona = (
            "You are Codunot, a helpful human-like assistant in a Discord chat. "
            "Give concise, factual answers, including coding/helpful info. No slang, no emojis. "
            "Keep answers professional, informative, and short."
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
        "Write a short, funny, non-malicious roast. "
        "Never attack protected classes or someone's identity. "
        "Use slang and emoji. Keep it short (1-2 lines)."
    )
    return f"{persona}\n{target_line}\nRecent chat:\n{history_text}\n\nGive one playful roast as Codunot:"

def humanize_and_safeify(text: str) -> str:
    t = maybe_typo(text)
    if random.random() < 0.45:
        t = random.choice(["lol", "bruh", "ngl"]) + " " + t
    return t

# ---------- proactive chat & roast ----------
async def proactive_chat_check():
    await client.wait_until_ready()
    while True:
        for guild in client.guilds:
            for channel in guild.text_channels:
                chan_id = str(channel.id)
                if not channel.permissions_for(guild.me).send_messages:
                    continue

                last_msg_time = memory.get_last_timestamp(chan_id)
                target = memory.get_roast_target(chan_id) if hasattr(memory, "get_roast_target") else None

                # If no messages yet, send a starter
                if not last_msg_time:
                    starter = "Heyyy, anyone up for a chat? 😎"
                    await send_human_reply(channel, starter)
                    memory.add_message(chan_id, BOT_NAME, starter)
                    continue

                # Roast Mode: proactive roast every 2 min
                if target and BOT_MODE == "funny":
                    if (datetime.utcnow() - last_msg_time).total_seconds() > 120:
                        roast_prompt = build_roast_prompt(memory, chan_id, target)
                        raw = await call_gemini(roast_prompt)
                        roast_text = humanize_and_safeify(raw)
                        if len(roast_text) > 200:
                            roast_text = roast_text[:200] + "..."
                        await send_human_reply(channel, roast_text)
                        memory.add_message(chan_id, BOT_NAME, roast_text)
                        continue

                # Normal chat if dead 3+ min
                if (datetime.utcnow() - last_msg_time).total_seconds() > 180:
                    prompt = build_general_prompt(memory, chan_id)
                    raw_resp = await call_gemini(prompt)
                    reply = humanize_response(raw_resp) if raw_resp.strip() else random.choice(["lol", "huh?", "true", "omg", "bruh"])
                    if len(reply) > 200:
                        reply = reply[:200] + "..."
                    await send_human_reply(channel, reply)
                    memory.add_message(chan_id, BOT_NAME, reply)

        await asyncio.sleep(60)

# ---------- on_ready ----------
@client.event
async def on_ready():
    print(f"{BOT_NAME} is ready!")
    asyncio.create_task(proactive_chat_check())

# ---------- message handler ----------
@client.event
async def on_message(message: Message):
    global BOT_MODE
    if message.author == client.user or message.author.bot:
        return

    chan_id = str(message.channel.id)
    memory.add_message(chan_id, message.author.display_name, message.content)

    # Commands for switching modes
    if message.content.lower().startswith("!roastmode"):
        BOT_MODE = "funny"
        await message.channel.send("😂 Roast mode activated!")
        return
    if message.content.lower().startswith("!seriousmode"):
        BOT_MODE = "serious"
        await message.channel.send("🤓 Serious/helpful mode activated!")
        return

    # Check if message triggers roast
    roast_target = is_roast_trigger(message.content)
    if roast_target:
        # Set persistent roast target
        if hasattr(memory, "set_roast_target"):
            memory.set_roast_target(chan_id, roast_target)

    # Check if roast mode is active
    target = memory.get_roast_target(chan_id) if hasattr(memory, "get_roast_target") else None
    if target and BOT_MODE == "funny":
        roast_prompt = build_roast_prompt(memory, chan_id, target)
        raw = await call_gemini(roast_prompt)
        roast_text = humanize_and_safeify(raw)
        if len(roast_text) > 200:
            roast_text = roast_text[:200] + "..."
        await send_human_reply(message.channel, roast_text, message)
        memory.add_message(chan_id, BOT_NAME, roast_text)
        return

    # Normal conversation
    prompt = build_general_prompt(memory, chan_id)
    raw_resp = await call_gemini(prompt)
    reply = humanize_response(raw_resp) if raw_resp.strip() else random.choice(["lol", "huh?", "true", "omg", "bruh"])
    if len(reply) > 200:
        reply = reply[:200] + "..."
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
