import discord
from discord.ext import commands
import os
import asyncio
from services.secret_loader import load_project_env

load_project_env()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

async def clear_guild_sync():
    if not TOKEN or not GUILD_ID:
        print("Missing DISCORD_TOKEN or GUILD_ID in private env files.")
        return

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
        guild = discord.Object(id=int_guild_id)
        
        print(f"Clearing commands for guild: {int_guild_id}")
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        print("✅ Guild commands cleared.")
        
        # Also sync global once to be sure
        print("Syncing global commands...")
        await bot.tree.sync()
        print("✅ Global sync complete.")
        
        await bot.close()

    try:
        int_guild_id = int(GUILD_ID)
        await bot.start(TOKEN)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(clear_guild_sync())
