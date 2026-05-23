import os
import paramiko
from services.secret_loader import load_project_env

def create_ssh_client(server, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=password)
    return client

def check_logs():
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
    
    # Get the last 100 lines and show the WHOLE block between 18:56 and 18:58
    print("Log block around sync time:")
    stdin, stdout, stderr = ssh.exec_command("grep -A 50 'Sync Identity triggered' /root/DICEwithoutNumber/bot_new.log | tail -n 60")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    check_logs()
