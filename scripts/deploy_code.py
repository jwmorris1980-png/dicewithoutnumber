import os
import sys
import paramiko
from scp import SCPClient
from services.secret_loader import load_project_env

def create_ssh_client(server, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=password)
    return client

def deploy():
    # Read IP
    if not os.path.exists("do_ip.txt"):
        print("do_ip.txt not found. Run do_deploy.py first.")
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
    
    print("Creating remote directory...")
    ssh.exec_command("mkdir -p /root/DICEwithoutNumber")
    
    print("Uploading files...")
    with SCPClient(ssh.get_transport()) as scp:
        # Upload all files in current dir except .venv, __pycache__, .git, .gemini
        for item in os.listdir("."):
            if item in [".venv", "__pycache__", ".git", ".gemini", "node_modules", ".vscode"]:
                continue
            
            # Use recursive upload for directories
            print(f"Uploading {item}...")
            scp.put(item, remote_path="/root/DICEwithoutNumber/", recursive=True)
            
    print("Setting up remote environment and systemd service...")
    # Install dependencies and start bot in ONE command session to preserve CWD and state
    setup_script = (
        "cd /root/DICEwithoutNumber && "
        "while fuser /var/lib/apt/lists/lock /var/lib/dpkg/lock /var/lib/dpkg/lock-frontend >/dev/null 2>&1 ; do sleep 5; done && "
        "apt-get update && "
        "while fuser /var/lib/apt/lists/lock /var/lib/dpkg/lock /var/lib/dpkg/lock-frontend >/dev/null 2>&1 ; do sleep 5; done && "
        "apt-get install -y python3-pip python-is-python3 && "
        "pip install --upgrade pip && "
        "pip install -r requirements.txt && "
        "cp dicewithoutnumber.service /etc/systemd/system/ && "
        "systemctl daemon-reload && "
        "systemctl enable dicewithoutnumber && "
        "systemctl restart dicewithoutnumber"
    )
    
    stdin, stdout, stderr = ssh.exec_command(setup_script)
    print(stdout.read().decode())
    print(stderr.read().decode())

    ssh.close()
    print("Deployment complete!")

if __name__ == "__main__":
    deploy()
