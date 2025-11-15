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

memory = MemoryManager(limit=60)

# ----------------- Bot State -----------------
BOT_MODE = "funny"  # default
DEAD_CHAT_CHANNELS = {
    "ROYALRACER FANS": ["testing", "coders", "general"],
    "OPEN TO ALL": ["general"]
}

# ---------- Send reply instantly ----------
async def send_human_reply(channel, reply_text, original_message: Message = None):
    await asyncio.sleep(0.05)  # tiny delay to avoid API spam
    await channel.send(reply_text)

# ---------- Proactive starter ----------
async def proactive_chat_start():
    await client.wait_until_ready()
    for guild in client.guilds:
        for channel in guild.text_channels:
            chan_id = str(channel.id)
            if not memory.get_last_timestamp(chan_id):
                starter = "Heyyy, anyone up for a chat? 😎"
                await send_human_reply(channel, starter)
                memory.add_message(chan_id, BOT_NAME, starter)
    while True:
        await asyncio.sleep(60)  # check every 60 sec
        for guild in client.guilds:
            for channel in guild.text_channels:
                chan_id = str(channel.id)
                last_ts = memory.get_last_timestamp(chan_id)
                if not last_ts or datetime.utcnow() - last_ts > timedelta(minutes=3):
                    msg = "its dead in here... anyone wanna talk?"
                    await send_human_reply(channel, msg)
                    memory.add_message(chan_id, BOT_NAME, msg)

# ---------- Prompt builders ----------
def build_general_prompt(mem_manager: MemoryManager, channel_id: str) -> str:
    recent = mem_manager.get_recent_flat(channel_id, n=CONTEXT_LENGTH)
    history_text = "\n".join(recent)
    if BOT_MODE == "serious":
        persona = (
            "You are Codunot, a helpful, professional human friend. "
            "Provide short, clear, accurate answers. Use code blocks for code. "
            "No slang, no emojis, no jokes."
        )
    else:
        persona = (
            "You are Codunot, a witty, funny human friend in chat. "
            "Keep replies short, playful, with slang and emojis."
        )
    return f"{persona}\n\nRecent chat:\n{history_text}\n\nReply as Codunot (one short message):"

def build_roast_prompt(mem_manager: MemoryManager, channel_id: str, target_name: str):
    recent = mem_manager.get_recent_flat(channel_id, n=12)
    history_text = "\n".join(recent)
    persona = (
        "You are Codunot, a witty human friend who roasts playfully. "
        "Write a short, funny, non-malicious roast. Use slang and emojis."
    )
    return f"{persona}\nTarget: {target_name}\nRecent chat:\n{history_text}\n\nGive one playful roast as Codunot:"

def humanize_and_safeify(text: str) -> str:
    t = maybe_typo(text)
    if BOT_MODE == "funny" and random.random() < 0.45:
        t = random.choice(["lol", "bruh", "ngl"]) + " " + t
    return t

# ---------- Events ----------
@client.event
async def on_ready():
    print(f"{BOT_NAME} is ready!")
    asyncio.create_task(proactive_chat_start())

@client.event
async def on_message(message: Message):
    global BOT_MODE
    if message.author == client.user or message.author.bot:
        return

    chan_id = str(message.channel.id)
    memory.add_message(chan_id, message.author.display_name, message.content)

    # ---------- Mode Commands ----------
    if message.content.lower().startswith("!seriousmode"):
        BOT_MODE = "serious"
        await send_human_reply(message.channel, "🤓 Serious/helpful mode activated!")
        return
    if message.content.lower().startswith("!roastmode"):
        BOT_MODE = "funny"
        await send_human_reply(message.channel, "😂 Roast/funny mode activated!")
        return

    # ---------- Roast triggers ----------
    if BOT_MODE == "funny":
        roast_target = memory.get_roast_target(chan_id)
        if not roast_target:
            trigger_target = is_roast_trigger(message.content)
            if trigger_target:
                memory.set_roast_target(chan_id, trigger_target)
                roast_target = trigger_target
        if roast_target:
            roast_prompt = build_roast_prompt(memory, chan_id, roast_target)
            raw = await call_gemini(roast_prompt)
            roast_text = humanize_and_safeify(raw)
            if len(roast_text) > 200:
                roast_text = roast_text[:200] + "..."
            await send_human_reply(message.channel, roast_text, message)
            memory.add_message(chan_id, BOT_NAME, roast_text)
            return

    # ---------- General chat ----------
    prompt = build_general_prompt(memory, chan_id)
    raw_resp = await call_gemini(prompt)
    reply = humanize_response(raw_resp) if raw_resp.strip() else random.choice(["lol", "huh?", "true", "omg", "bruh"])
    if len(reply) > 200:
        reply = reply[:200] + "..."
    await send_human_reply(message.channel, reply, message)
    memory.add_message(chan_id, BOT_NAME, reply)
    memory.persist()

# ---------- Run bot ----------
def run():
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run()
