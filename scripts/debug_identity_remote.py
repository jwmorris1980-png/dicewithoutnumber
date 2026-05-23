import os
import paramiko
from services.secret_loader import load_project_env

def create_ssh_client(server, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=password)
    return client

def deep_status():
    if not os.path.exists("do_ip.txt"):
        print("do_ip.txt not found.")
        return
    
    with open("do_ip.txt", "r") as f:
        ip = f.read().strip()
    
    user = "root"
    load_project_env()
    password = os.getenv("ORACLE_PASSWORD")
    if not password:
        print("Missing ORACLE_PASSWORD in your private env file.")
        return
    
    print(f"Connecting to {ip}...")
    ssh = create_ssh_client(ip, user, password)
    
    # Run a one-off script on the droplet to get bot status
    # We'll use the existing venv
    script = """
import os
import asyncio
import discord
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
guild_id = int(os.getenv('GUILD_ID'))

client = discord.Client(intents=discord.Intents.default())

@client.event
async def on_ready():
    guild = client.get_guild(guild_id)
    if not guild:
         print(f"ERROR: Guild {guild_id} not found.")
    else:
         me = guild.get_member(client.user.id)
         if not me:
              me = await guild.fetch_member(client.user.id)
         print(f"BOT_USERNAME: {client.user.name}")
         print(f"BOT_NICKNAME: {me.nick}")
         print(f"GUILD_NAME: {guild.name}")
    await client.close()

client.run(token)
"""
    # Write script to droplet
    sftp = ssh.open_sftp()
    with sftp.file("/root/DICEwithoutNumber/debug_identity.py", "w") as f:
        f.write(script)
    sftp.close()
    
    print("Running debug script on droplet...")
    stdin, stdout, stderr = ssh.exec_command("cd /root/DICEwithoutNumber && ./venv/bin/python debug_identity.py")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    deep_status()
