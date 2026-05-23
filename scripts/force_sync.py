import discord
from discord.ext import commands
import os
from services.secret_loader import load_project_env

load_project_env()
TOKEN = os.getenv("DISCORD_TOKEN")

# We must import the commands exactly as they are in bot.py to sync them
# Actually, if we just want to sync whatever the currently running bot (on the droplet) has,
# we can't do that from here easily unless we load all cogs.
# BUT wait, the droplet bot has a `!sync` command.
# I can just log in as a user and send `!sync`? No, self-bots are against TOS.
