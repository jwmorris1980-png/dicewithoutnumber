import os
import paramiko
from services.secret_loader import load_project_env

def create_ssh_client(server, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=password)
    return client

def test_guild_ids():
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
    
    ids = ["411578653374414894", "454047930056441857"]
    
    print("Testing IDs on droplet...")
    for gid in ids:
        test_script = (
            "cd /root/DICEwithoutNumber && "
            f"python3 -c \"import os; import discord; from dotenv import load_dotenv; load_dotenv(); "
            f"from bot import WithoutNumberBot; "
            f"import asyncio; "
            f"async def test(): "
            f"  bot = WithoutNumberBot(); "
            f"  await bot.login(os.getenv('DISCORD_TOKEN')); "
            f"  guild = await bot.fetch_guild({gid}); "
            f"  if guild: print(f'FOUND GUILD: {{guild.name}} (ID: {gid})'); "
            f"  await bot.close(); "
            f"asyncio.run(test())\""
        )
        stdin, stdout, stderr = ssh.exec_command(test_script)
        print(stdout.read().decode())
        print(stderr.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    test_guild_ids()
