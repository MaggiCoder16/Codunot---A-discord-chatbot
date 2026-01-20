import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing!")

intents = discord.Intents.none()  # we don't need message intents
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # remove ALL global slash commands (all servers)
    await bot.tree.clear_commands(guild=None)  # guild=None = global commands
    await bot.tree.sync()

    print("ALL global slash commands deleted.")
    await bot.close()

bot.run(TOKEN)
