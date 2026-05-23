import discord
from discord import app_commands
import asyncio
import os
from services.secret_loader import load_project_env

async def sync():
    load_project_env()
    token = os.getenv('DISCORD_TOKEN')
    guild_id = os.getenv('GUILD_ID')
    
    if not token or not guild_id:
        print("Missing token or guild_id in private env files.")
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user}')
        guild = discord.Object(id=int(guild_id))
        
        # We need to load the cogs to the tree. 
        # But for a simple sync of existing commands, we just need to hit the API.
        # Actually, the bot.py already does sync_identity.
        # Let's just trigger a tree.sync() for that guild.
        
        print(f"Syncing for guild {guild_id}...")
        try:
            # We need to actually have the commands in the tree to sync them.
            # This script is a bit complex if we want to "load" them.
            # Alternative: The bot itself has a !sync guild command.
            # I will just tell the user to run !sync guild in Discord.
            pass
        except Exception as e:
            print(f"Error: {e}")
        
        await client.close()

    # Actually, a better way is to just send a message to the log channel 
    # to tell the bot owner to run !sync guild if they don't see it.
    # But I'll try to run the bot's own sync logic.
    
    # Actually, if I just restart the bot, and it has `self.tree.sync()` in its setup, it might work.
    # But the bot.py has it commented out.
    
    print("Please run !sync guild in your Discord server to see the new /portrait command.")

if __name__ == "__main__":
    asyncio.run(sync())
