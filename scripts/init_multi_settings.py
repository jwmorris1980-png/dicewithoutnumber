import os
import paramiko
import json
from services.secret_loader import load_project_env

def create_ssh_client(server, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=password)
    return client

def init_settings():
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
    
    # Read existing settings
    stdin, stdout, stderr = ssh.exec_command("cat /root/DICEwithoutNumber/settings.json")
    old_raw = stdout.read().decode().strip()
    
    try:
        old_data = json.loads(old_raw)
    except:
        old_data = {"app_name": "DICEwithoutNumber", "theme": "dark"}
    
    # Transform to NEW structure
    if "global" not in old_data:
        new_data = {
            "global": {
                "app_name": old_data.get("app_name", "DICEwithoutNumber"),
                "theme": old_data.get("theme", "dark")
            },
            "servers": {}
        }
        
        # Preserve current server as an override if we have GUILD_ID in ENV
        # Actually, better to just keep it clean for now.
        
        print(f"Transforming settings to NEW structure...")
        new_raw = json.dumps(new_data, indent=2)
        
        sftp = ssh.open_sftp()
        with sftp.file("/root/DICEwithoutNumber/settings.json", "w") as f:
            f.write(new_raw)
        sftp.close()
        print("Settings transformed successfully.")
    else:
        print("Settings already in NEW structure.")
    
    ssh.close()

if __name__ == "__main__":
    init_settings()
