import aiohttp
import asyncio
import os
import sys
import discord
from discord import app_commands
from discord.ext import commands
import logging
import json
from services.secret_loader import load_project_env

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sync_safe")

# Ensure we can find the cogs
sys.path.append(os.getcwd())

def get_token():
    load_project_env()
    return os.getenv("DISCORD_TOKEN")

TOKEN = get_token()

class MockBot(commands.Bot):
    def __init__(self, app_id):
        intents = discord.Intents.default()
        # Use a dummy app_id for the tree
        super().__init__(command_prefix="!", intents=intents, help_command=None, application_id=app_id)

async def safe_global_sync():
    if not TOKEN:
        logger.error("No token found in private env files.")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
        
        # 1. Get Application ID
        async with session.get("https://discord.com/api/v10/users/@me", headers=headers) as resp:
            if resp.status != 200:
                logger.error(f"Error fetching app info: {resp.status}")
                sys.exit(1)
            data = await resp.json()
            app_id = int(data['id'])
            logger.info(f"App ID resolved: {app_id}")

        # 2. Load Cogs and build Payload
        logger.info("Gathering commands from cogs...")
        bot = MockBot(app_id=app_id)
        
        cog_dir = os.path.join(os.getcwd(), "cogs")
        if not os.path.exists(cog_dir):
            logger.error(f"Cog directory '{cog_dir}' not found.")
            sys.exit(1)

        loaded_cogs = []
        for filename in os.listdir(cog_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module = f"cogs.{filename[:-3]}"
                try:
                    await bot.load_extension(module)
                    loaded_cogs.append(module)
                except Exception as e:
                    logger.warning(f"Failed to load {module}: {e}")

        logger.info(f"Successfully loaded {len(loaded_cogs)} cogs.")

        # Extract all app commands from the tree
        payload = []
        all_tree_cmds = list(bot.tree.walk_commands())
        logger.info(f"Walking tree: found {len(all_tree_cmds)} total objects.")

        for cmd in all_tree_cmds:
            # We want top-level commands or groups
            if cmd.parent is None:
                try:
                    cmd_json = cmd.to_dict(bot.tree)
                    payload.append(cmd_json)
                    logger.info(f"Added command to payload: /{cmd.name}")
                except Exception as e:
                    logger.error(f"Failed to convert /{cmd.name} to dict: {e}")
        
        # FINAL SAFETY CHECK
        if not payload:
            logger.error("CRITICAL: Zero commands found in tree! Aborting sync to prevent global deletion.")
            sys.exit(1)
            
        logger.info(f"Final payload contains {len(payload)} commands.")
        with open("sync_payload.json", "w") as f:
            json.dump(payload, f, indent=2)
        logger.info("Saved payload to sync_payload.json")

        # 3. Handle Entry Point
        url = f"https://discord.com/api/v10/applications/{app_id}/commands"
        async with session.get(url, headers=headers) as resp:
            existing_cmds = await resp.json()
            entry_point = next((c for c in existing_cmds if c.get('name') == 'map' and c.get('type') == 4), None)
        
        if entry_point:
            logger.info(f"Temporarily removing Entry Point 'map' (ID: {entry_point['id']})...")
            await session.delete(f"{url}/{entry_point['id']}", headers=headers)

        # 4. Perform Bulk Upsert
        logger.info("Sending bulk update to Discord API...")
        async with session.put(url, headers=headers, json=payload) as resp:
            if resp.status in (200, 201):
                logger.info("Success! Global commands updated.")
            else:
                body = await resp.text()
                logger.error(f"Sync failed ({resp.status}): {body}")
                sys.exit(1)

        # 5. Restore Entry Point
        restore_payload = {
            "type": 4, # PRIMARY_ENTRY_POINT
            "name": "map",
            "description": "",
            "handler": 2 # DISCORD_LAUNCH_ACTIVITY
        }
        logger.info("Restoring Entry Point 'map'...")
        async with session.post(url, headers=headers, json=restore_payload) as resp:
            if resp.status in (200, 201):
                logger.info("Entry Point restored successfully.")
            else:
                logger.error(f"Failed to restore entry point ({resp.status})")

if __name__ == "__main__":
    asyncio.run(safe_global_sync())
