import aiohttp
import asyncio
import os
from services.secret_loader import load_project_env

load_project_env()
TOKEN = os.getenv("DISCORD_TOKEN")
APPLICATION_ID = "" # We'll need to find this or extract it from the token

async def fix_sync_error():
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bot {TOKEN}"}
        
        # 1. Get Application ID
        async with session.get("https://discord.com/api/v10/users/@me", headers=headers) as resp:
            data = await resp.json()
            app_id = data['id']
            print(f"Detected Application ID: {app_id}")

        # 2. Fetch all global commands
        url = f"https://discord.com/api/v10/applications/{app_id}/commands"
        async with session.get(url, headers=headers) as resp:
            commands = await resp.json()
            
        print(f"Found {len(commands)} global commands.")
        
        entry_point_id = None
        for cmd in commands:
            # Entry point commands usually have a specific type or name
            # Type 4 is Primary Entry Point
            print(f"Command: {cmd.get('name')} (ID: {cmd.get('id')}, Type: {cmd.get('type')})")
            if cmd.get('type') == 4:
                entry_point_id = cmd.get('id')
                print(f"!!! FOUND ENTRY POINT COMMAND: {cmd.get('name')} (ID: {entry_point_id})")

        if entry_point_id:
            print(f"Attempting to delete entry point command {entry_point_id} separately...")
            delete_url = f"{url}/{entry_point_id}"
            async with session.delete(delete_url, headers=headers) as resp:
                if resp.status == 204:
                    print("Successfully deleted entry point command!")
                else:
                    print(f"Failed to delete: {resp.status}")
                    print(await resp.text())
        else:
            print("No entry point command (type 4) found in global commands.")

if __name__ == "__main__":
    asyncio.run(fix_sync_error())
