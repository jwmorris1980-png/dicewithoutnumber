import os
import paramiko
from services.secret_loader import load_project_env

def create_ssh_client(server, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=password)
    return client

def check_structure():
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
    
    print("Listing directory structure:")
    stdin, stdout, stderr = ssh.exec_command("ls -F /root/DICEwithoutNumber/")
    print(stdout.read().decode())
    
    print("Checking venv:")
    stdin, stdout, stderr = ssh.exec_command("ls -F /root/DICEwithoutNumber/venv/bin/")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    check_structure()
