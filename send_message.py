"""
send_message.py
───────────────
Run this ONCE to broadcast the Codunot moderation announcement
to every server the bot is in.

Usage:
    python send_message.py

It will try to find the best channel in each server to send to,
print a summary of successes and failures, and exit.
"""

import asyncio
import os
import discord
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ── The embed that gets sent to every server ──────────────────────────────────

def build_announce_embed(guild: discord.Guild) -> discord.Embed:
    me = guild.me
    p  = me.guild_permissions

    required = {
        "Ban Members":      p.ban_members,
        "Kick Members":     p.kick_members,
        "Moderate Members": p.moderate_members,
        "Manage Messages":  p.manage_messages,
        "Manage Channels":  p.manage_channels,
    }

    missing = [name for name, ok in required.items() if not ok]
    all_good = len(missing) == 0

    embed = discord.Embed(
        title="🛡️ Codunot now does Moderation!",
        description=(
            "Hey! Big update — **Codunot is no longer just a chatbot**.\n\n"
            "It now includes a **full server moderation system** — completely free to set up!\n\n"
            "**Run `/setup-moderation` to get started.** It's a 6-step wizard that takes ~2 minutes."
        ),
        color=0xFFA500,
    )

    embed.add_field(
        name="🛡️ What's included",
        value=(
            "• **AutoMod** — auto-deletes bad words, blocks links, times out spammers, locks during raids\n"
            "• `/warn` `/warns` `/clearwarns` — full warning system (auto-timeout at 3 warns)\n"
            "• `/ban` `/unban` `/modkick` `/mute` `/unmute`\n"
            "• `/clear` `/slowmode` `/lock` `/unlock`\n"
            "• `/userinfo` `/case` — member info & case lookup\n"
            "🌟 **Premium/Gold:** `/tempban` `/massban` `/modstats` `/note`"
        ),
        inline=False,
    )

    if all_good:
        embed.add_field(
            name="✅ Permissions",
            value="Codunot already has all the permissions it needs in this server. You're good to go!",
            inline=False,
        )
    else:
        embed.add_field(
            name="⚠️ Action Required — Missing Permissions",
            value=(
                "Codunot is **missing some permissions** needed for mod commands to work.\n\n"
                "**Missing:**\n" + "\n".join(f"• `{p}`" for p in missing) + "\n\n"
                "**How to fix:**\n"
                "1. Go to **Server Settings → Roles**\n"
                "2. Find and click the **Codunot** role\n"
                "3. Enable the permissions listed above\n"
                "4. Save — done! ✅\n\n"
                "*(Mod commands will show `❌ No permission` errors until this is fixed)*"
            ),
            inline=False,
        )

    embed.add_field(
        name="🚀 Get started",
        value="Run `/setup-moderation` in this server — server owner or admins only.",
        inline=False,
    )
    embed.set_footer(text="Codunot — AI Chatbot + Moderation • by my creator aarav_2022")
    return embed

def pick_channel(guild: discord.Guild) -> discord.TextChannel | None:
    me = guild.me
    priority_names = ["announcements", "general", "bot-commands", "bot-spam", "bots", "chat"]

    for name in priority_names:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch and ch.permissions_for(me).send_messages:
            return ch

    for ch in guild.text_channels:
        if ch.permissions_for(me).send_messages:
            return ch

    return None

class AnnouncerBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(intents=intents)

    async def on_ready(self):
        print(f"[ANNOUNCER] Logged in as {self.user} ({self.user.id})")
        print(f"[ANNOUNCER] Sending to {len(self.guilds)} server(s)...\n")

        success = []
        failed  = []
        skipped = []

        for guild in self.guilds:
            channel = pick_channel(guild)
            if channel is None:
                skipped.append(f"{guild.name} ({guild.id}) — no writable channel found")
                continue

            try:
                embed = build_announce_embed(guild)
                await channel.send(embed=embed)
                success.append(f"✅ {guild.name} → #{channel.name}")
                print(f"  ✅ Sent to {guild.name} → #{channel.name}")
            except Exception as e:
                failed.append(f"❌ {guild.name} ({guild.id}) — {e}")
                print(f"  ❌ Failed {guild.name}: {e}")

            await asyncio.sleep(1.5)

        print("\n── SUMMARY ─────────────────────────────")
        print(f"Sent:    {len(success)}")
        print(f"Failed:  {len(failed)}")
        print(f"Skipped: {len(skipped)}")

        if failed:
            print("\nFailed servers:")
            for f in failed:
                print(f"  {f}")

        if skipped:
            print("\nSkipped servers (no writable channel):")
            for s in skipped:
                print(f"  {s}")

        print("\n[ANNOUNCER] Done. Closing.")
        await self.close()


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not set in .env")
        exit(1)

    client = AnnouncerBot()
    client.run(DISCORD_TOKEN)
