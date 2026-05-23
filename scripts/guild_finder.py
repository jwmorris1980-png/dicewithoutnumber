import os
import discord
import asyncio
from services.secret_loader import load_project_env

async def test_ids():
    load_project_env()
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("No token found")
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    # We don't need to run the full bot, just login and fetch guilds
    await client.login(token)
    
    print("Fetching accessible guilds...")
    async for guild in client.fetch_guilds(limit=10):
        print(f"GUILD_MATCH: {guild.name} (ID: {guild.id})")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_ids())
