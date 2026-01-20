import discord
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is missing!")

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)  # discord.py 2.x style

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

    # Clear all global slash commands
    await bot.tree.clear_commands(guild=None)
    print("All global slash commands removed!")

    await bot.close()

bot.run(DISCORD_TOKEN)
