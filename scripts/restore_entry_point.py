import aiohttp
import asyncio
import os
from services.secret_loader import load_project_env

def get_token():
    load_project_env()
    return os.getenv("DISCORD_TOKEN")

TOKEN = get_token()

async def restore_entry_point():
    if not TOKEN:
        print("Error: Could not find DISCORD_TOKEN in private env files.")
        return

    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
        
        # 1. Get Application ID
        async with session.get("https://discord.com/api/v10/users/@me", headers=headers) as resp:
            data = await resp.json()
            app_id = data['id']
            print(f"Detected Application ID: {app_id}")

        # 2. Create the Primary Entry Point Command
        url = f"https://discord.com/api/v10/applications/{app_id}/commands"
        payload = {
            "type": 4, # PRIMARY_ENTRY_POINT
            "name": "map",
            "description": "",
            "handler": 2 # DISCORD_LAUNCH_ACTIVITY
        }
        
        print("Restoring Entry Point Command via Discord API...")
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status in (200, 201):
                result = await resp.json()
                print(f"Successfully restored Entry Point Command '{result.get('name')}' (ID: {result.get('id')})!")
            else:
                print(f"Failed to restore: {resp.status}")
                print(await resp.text())

if __name__ == "__main__":
    asyncio.run(restore_entry_point())
