import discord
import asyncio
from config import GEMINI_API_KEY, DISCORD_TOKEN
from memory import add_message_to_memory, add_topic, update_mood, memory
from humanizer import humanize, detect_mood, human_delay, is_roast_trigger, generate_safe_roast
from google import genai

client = discord.Client(intents=discord.Intents.all())
gen = genai.Client(api_key=GEMINI_API_KEY)

def build_prompt(channel_id, latest_msg, user):
    channel_mem = memory.get(channel_id, {})
    topics = ", ".join(channel_mem.get("topics", []))
    moods = channel_mem.get("user_moods", {})
    mood_lines = "\n".join([f"{u} feels {m}" for u, m in moods.items()])

    personality = """
You are Codunot. A normal human teen in Discord chats.
Talk casually, freely, with emojis, typos, slang, sarcasm.
Never mention you are a bot or AI.
Reply ONLY to the latest message.
Keep your reply SHORT: 1 line max 30 characters.
"""
    return f"{personality}\nTopics: {topics}\nMoods:\n{mood_lines}\nLatest message from {user}: {latest_msg}\nReply like a real human teen."

async def generate_response(prompt):
    loop = asyncio.get_running_loop()
    try:
        # Run blocking GenAI call safely with timeout
        response = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: gen.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )),
            timeout=10  # seconds
        )
        reply = (response.text or "").strip().splitlines()[0][:30]
        return reply
    except Exception as e:
        # fallback short reply if API fails
        return "Oops, try again later 😅"

@client.event
async def on_message(message):
    if message.author.bot:
        return

    cid = str(message.channel.id)
    user = str(message.author)
    msg = message.content

    add_message_to_memory(cid, user, msg)
    update_mood(cid, user, detect_mood(msg))

    if is_roast_trigger(msg):
        roast = humanize(generate_safe_roast(user))[:30]
        await asyncio.sleep(human_delay())
        await message.channel.send(roast)
        add_message_to_memory(cid, "Codunot", roast)
        return

    if any(word in msg.lower() for word in ["today", "topic", "talk"]):
        add_topic(cid, msg)

    prompt = build_prompt(cid, msg, user)
    reply = await generate_response(prompt)
    reply = humanize(reply)

    await asyncio.sleep(human_delay())
    await message.channel.send(reply)
    add_message_to_memory(cid, "Codunot", reply)

client.run(DISCORD_TOKEN)
