import os
import discord

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

bot = discord.Bot()  # Pycord bot with slash command support

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

    # Clear all global commands
    await bot.application_commands.clear()  # Pycord way
    print("All global slash commands removed!")

    # Close the bot
    await bot.close()

bot.run(DISCORD_TOKEN)
