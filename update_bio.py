import os
import nextcord
from nextcord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = nextcord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

bio_text = """**Codunot** is a Discord bot made for fun and utility. It can joke, roast, give serious help, and play chess, with different modes you can switch anytime.
In servers, you must ping @Codunot to use it; pinging is not required in DMs.

**Commands**
`!funmode`
`!roastmode`
`!seriousmode`
`!chessmode`
`!codunot_help` (all about the bot)

**Contact the owner:** `@aarav_2022` for all details, help, and commands.
"""

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")

    await bot.user.edit(about_me=bio_text)
    print("Bio updated successfully!")

    await bot.close()

bot.run(TOKEN)
