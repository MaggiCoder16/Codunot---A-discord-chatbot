import discord
import asyncio
import random
from google import genai
from config import GEMINI_API_KEY, DISCORD_TOKEN, OWNER_ID
from memory import add_message_to_memory, add_topic, update_mood, memory
from humanizer import humanize, detect_mood, human_delay, is_roast_trigger, generate_safe_roast

gen = genai.Client(api_key=GEMINI_API_KEY)

MAX_CHAR = 67
IDLE_SECONDS = 180

def build_prompt(channel_id):
    channel_mem = memory.get(channel_id, {})
    msgs = "\n".join(channel_mem.get("messages", []))
    topics = ", ".join(channel_mem.get("topics", []))
    moods = channel_mem.get("user_moods", {})
    mood_lines = "\n".join([f"{u} feels {m}" for u, m in moods.items()])
    personality = (
        "You are Codunot. A tired teen in Discord chats.\n"
        "Talk casual, free, small roasts sometimes.\n"
        "Use emojis, typos, randomness. Don't say AI.\n"
    )
    return f"{personality}\nTopics: {topics}\nMoods:\n{mood_lines}\nChat:\n{msgs}\nReply like a teen."

async def generate_reply(prompt):
    response = gen.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    reply = response.text or ""
    reply = humanize(reply)[:MAX_CHAR]
    return reply

class CodunotClient(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_message_time = {}
    
    async def setup_hook(self):
        self.loop.create_task(self.idle_check())
    
    async def idle_check(self):
        await self.wait_until_ready()
        while not self.is_closed():
            now = discord.utils.utcnow().timestamp()
            for channel_id, last in self.last_message_time.items():
                if now - last > IDLE_SECONDS:
                    channel = self.get_channel(int(channel_id))
                    if channel:
                        msg = random.choice([
                            "hi!!!! where is everybody?",
                            "anyone wanna talk? 😴",
                            "oof its dead in here lol"
                        ])
                        await channel.send(msg[:MAX_CHAR])
                        self.last_message_time[channel_id] = now
            await asyncio.sleep(10)

    async def on_message(self, message):
        if message.author.bot:
            return

        cid = str(message.channel.id)
        user = str(message.author)
        msg = message.content
        self.last_message_time[cid] = discord.utils.utcnow().timestamp()

        add_message_to_memory(cid, user, msg)
        update_mood(cid, user, detect_mood(msg))

        if "who made u" in msg.lower():
            if str(message.author.id) == OWNER_ID:
                reply = f"you made me, buddy. ty for making me enter this world"
            else:
                reply = f"<@{OWNER_ID}> made me"
            await message.reply(reply[:MAX_CHAR])
            add_message_to_memory(cid, "Codunot", reply)
            return

        if is_roast_trigger(msg):
            roast = generate_safe_roast(user)
            roast = humanize(roast)[:MAX_CHAR]
            await asyncio.sleep(human_delay())
            if random.random() < 0.5:
                await message.reply(roast)
            else:
                await message.channel.send(roast)
            add_message_to_memory(cid, "Codunot", roast)
            return

        if any(word in msg.lower() for word in ["today", "topic", "talk"]):
            add_topic(cid, msg)

        prompt = build_prompt(cid)
        reply = await generate_reply(prompt)
        await asyncio.sleep(human_delay())
        if random.random() < 0.5:
            await message.reply(reply)
        else:
            await message.channel.send(reply)
        add_message_to_memory(cid, "Codunot", reply)

client = CodunotClient(intents=discord.Intents.all())
client.run(DISCORD_TOKEN)
