import sys
import os
import asyncio
from unittest.mock import MagicMock

# Add current dir to path
sys.path.append(os.getcwd())

async def verify_bot_startup():
    print("🔍 Starting deployment verification...")
    
    # Mock discord.ext.commands.Bot
    from discord.ext import commands
    bot = MagicMock(spec=commands.Bot)
    bot.db = MagicMock()
    bot.web_service = MagicMock()
    
    cogs_to_test = [
        'cogs.dice', 'cogs.sheets', 'cogs.compendium', 'cogs.chargen'
    ]
    
    errors = []
    for cog_path in cogs_to_test:
        try:
            print(f"  - Loading {cog_path}...", end=" ")
            # Import the module
            module = __import__(cog_path, fromlist=['setup'])
            # Run setup
            await module.setup(bot)
            print("✅")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            errors.append((cog_path, str(e)))

    if errors:
        print("\n💥 VERIFICATION FAILED!")
        for cog, err in errors:
            print(f"  - {cog}: {err}")
        sys.exit(1)
    else:
        print("\n✨ ALL CORE COGS LOADED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(verify_bot_startup())
