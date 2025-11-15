import os
import discord
from discord.ext import commands, tasks
from collections import deque
import aiohttp
import asyncio
import random
from datetime import datetime, timedelta, timezone
import re

# --- CONFIG ---
TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("GEN_API_KEY")  # Gemini or your LLM
BOT_NAME = os.getenv("BOT_NAME", "Codunot")
MAX_MEMORY = 30

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

OWNER_IDS = {1020353220641558598, 1167443519070290051}

# --- STATE ---
channel_memory = {}  # channel_id: deque(messages)
shushed_channels = {}  # channel_id: datetime to resume
current_mode = "funny"  # funny / serious / roast

# --- UTILITY ---
def is_owner(member: discord.Member):
    return member.id in OWNER_IDS

def extract_time(text: str):
    match = re.search(r"(\d+)(s|m|h|d)", text)
    if not match: return None
    num, unit = int(match.group(1)), match.group(2)
    return num * {"s":1, "m":60, "h":3600, "d":86400}[unit]

def random_delay():
    return random.uniform(0.05, 0.1)

async def fetch_ai_response(prompt: str, channel: discord.TextChannel):
    """
    Dummy AI call; replace with Gemini/HF API call.
    """
    # Add memory for context
    mem = channel_memory.get(channel.id, deque(maxlen=MAX_MEMORY))
    context = "\n".join(mem)
    full_prompt = f"[{current_mode.upper()} MODE]\n{prompt}\nContext:\n{context}"
    # Simulate AI delay
    await asyncio.sleep(random_delay())
    # Dummy AI response
    if current_mode == "funny":
        return random.choice([
            f"lol {BOT_NAME} says hi! 😂",
            f"what's up? 😎",
            f"bruh, let's chat 😏"
        ])
    elif current_mode == "serious":
        return random.choice([
            "🤔 Here's a thoughtful answer for you.",
            "Sure, let me explain this clearly.",
            "This is a serious response: pay attention."
        ])
    elif current_mode == "roast":
        return random.choice([
            "bro, u talk like a broken bot 💀",
            "lol nice try, but u fail 😎",
            "ur typing is slower than dial-up 😂"
        ])

# --- COMMANDS ---
@bot.command(name="seriousmode")
async def serious_mode(ctx):
    global current_mode
    if not is_owner(ctx.author):
        return await ctx.send("🚫 Only owner can change mode!")
    current_mode = "serious"
    await ctx.send("✅ Serious/helpful mode activated!")

@bot.command(name="funnymode")
async def funny_mode(ctx):
    global current_mode
    if not is_owner(ctx.author):
        return await ctx.send("🚫 Only owner can change mode!")
    current_mode = "funny"
    await ctx.send("✅ Funny/playful mode activated!")

@bot.command(name="roastmode")
async def roast_mode(ctx):
    global current_mode
    if not is_owner(ctx.author):
        return await ctx.send("🚫 Only owner can change mode!")
    current_mode = "roast"
    await ctx.send("🔥 Roast mode activated!")

@bot.command(name="shush")
async def shush(ctx, *args):
    if not is_owner(ctx.author):
        return await ctx.send("🚫 Only owner can shush me!")
    seconds = 600
    if args:
        t = extract_time(args[0])
        if t: seconds = t
    shushed_channels[ctx.channel.id] = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    await ctx.send(f"🔇 I'll be quiet for {seconds} seconds.")

@bot.command(name="rshush")
async def rshush(ctx):
    shushed_channels.pop(ctx.channel.id, None)
    await ctx.send("🔊 Mute lifted!")

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f"{BOT_NAME} ready as {bot.user}")
    proactive_chat.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        # Optional: bot talks to other bots
        pass

    if message.author == bot.user:
        return

    await bot.process_commands(message)

    # Ignore shushed channels
    if message.channel.id in shushed_channels:
        if datetime.now(timezone.utc) < shushed_channels[message.channel.id]:
            return
        else:
            del shushed_channels[message.channel.id]

    # Update memory
    if message.channel.id not in channel_memory:
        channel_memory[message.channel.id] = deque(maxlen=MAX_MEMORY)
    channel_memory[message.channel.id].append(f"{message.author.display_name}: {message.content}")

    # Generate response
    reply = await fetch_ai_response(message.content, message.channel)
    await message.channel.send(reply)
    channel_memory[message.channel.id].append(f"{BOT_NAME}: {reply}")

# --- PROACTIVE CHAT ---
@tasks.loop(seconds=180)
async def proactive_chat():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.id in shushed_channels: continue
            mem = channel_memory.get(channel.id, deque(maxlen=MAX_MEMORY))
            if not mem or (datetime.now(timezone.utc) - datetime.now(timezone.utc)) > timedelta(minutes=3):
                # Send proactive message
                await channel.send(random.choice([
                    f"Hey, anyone up for a chat? 😎",
                    f"{BOT_NAME} is bored... let's talk! 😂",
                    "It's quiet here, anyone wanna chat?"
                ]))

# --- RUN ---
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_TOKEN not set")
