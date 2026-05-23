import paramiko
import os
from services.secret_loader import load_project_env

def setup():
    try:
        with open('do_ip.txt', 'r') as f:
            ip = f.read().strip()
    except Exception as e:
        print("Error reading IP:", e)
        return

    print(f"Connecting to {ip}...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        load_project_env()
        password = os.getenv("ORACLE_PASSWORD")
        if not password:
            print("Missing ORACLE_PASSWORD in your private env file.")
            return
        ssh.connect(ip, username='root', password=password)
    except Exception as e:
        print("Error connecting:", e)
        return

    print("Checking current Nginx config...")
    stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-available/dicewithoutnumber")
    config = stdout.read().decode()
    
    if "client_max_body_size" not in config:
        print("Updating Nginx config...")
        # Insert client_max_body_size 50M; directly after server_name line
        cmd = "sed -i 's/server_name.*;/&\\n    client_max_body_size 50M;/g' /etc/nginx/sites-available/dicewithoutnumber"
        ssh.exec_command(cmd)
        
        # Test config
        stdin, stdout, stderr = ssh.exec_command("nginx -t")
        print(stderr.read().decode())
        
        print("Reloading Nginx...")
        ssh.exec_command("systemctl reload nginx")
    else:
        print("Already configured!")

    ssh.close()
    print("Done")

if __name__ == "__main__":
    setup()
