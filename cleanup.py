import asyncio
import discord
import os

# Bot token from GitHub Actions secret
TOKEN = os.environ["DISCORD_TOKEN"]

# Channel ID (works for both DM and server channels)
CHANNEL_ID = 1439456449813151764

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True      # ← For DMs
intents.guilds = True           # ← For server channels

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    try:
        print(f"Bot logged in as {client.user}")
        
        channel = await client.fetch_channel(CHANNEL_ID)
        print(f"Found channel: {channel} (Type: {type(channel).__name__})")
        
        # Check if it's a valid channel type (DM or server text channel)
        if not isinstance(channel, (discord.TextChannel, discord.DMChannel)):
            raise RuntimeError(f"Channel is {type(channel).__name__}, not a TextChannel or DMChannel")
        
        deleted = 0
        async for message in channel.history(limit=100):
            # Only delete messages sent by your bot
            if message.author.id == client.user.id:
                try:
                    await message.delete()
                    deleted += 1
                    print(f"Deleted message {deleted}: {message.content[:50]}...")
                    await asyncio.sleep(0.5)  # Avoid rate limits
                except discord.Forbidden:
                    print(f"No permission to delete message")
                except Exception as e:
                    print(f"Error deleting message: {e}")
                
                if deleted >= 3:  # Stop after deleting 3 messages
                    break
        
        print(f"Deleted {deleted} bot messages")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()

async def main():
    async with client:
        await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
