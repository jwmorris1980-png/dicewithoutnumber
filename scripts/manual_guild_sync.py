import discord
from discord import app_commands
from bot import WithoutNumberBot
import asyncio
import os
from services.secret_loader import load_project_env

async def main():
    load_project_env()
    token = os.getenv("DISCORD_TOKEN")
    guild_id = os.getenv("GUILD_ID")
    
    if not token or not guild_id:
        print("Missing token or guild_id")
        return

    bot = WithoutNumberBot()
    
    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
        guild = discord.Object(id=int(guild_id))
        
        print("Copying global commands to guild...")
        bot.tree.copy_global_to(guild=guild)
        
        print(f"Syncing for guild {guild_id}...")
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} commands.")
        
        await bot.close()

    try:
        await bot.start(token)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
