import paramiko
import os
from services.secret_loader import load_project_env

def check_status():
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
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, password=password)
    
    with open("droplet_diagnosis.txt", "w", encoding="utf-8") as f:
        f.write("--- Port Check (8080) ---\n")
        stdin, stdout, stderr = client.exec_command("lsof -i :8080 || netstat -tuln | grep 8080")
        f.write(stdout.read().decode('utf-8', errors='ignore'))
        
        f.write("\n--- Running Python Processes ---\n")
        stdin, stdout, stderr = client.exec_command("ps aux | grep python")
        f.write(stdout.read().decode('utf-8', errors='ignore'))

        print("Fetching systemd logs...")
        stdin, stdout, stderr = client.exec_command("journalctl -u dicewithoutnumber -n 50 --no-pager")
        f.write("\n--- Systemd Service Logs ---\n")
        f.write(stdout.read().decode('utf-8', errors='replace'))
        f.write(stderr.read().decode('utf-8', errors='replace'))
    
    print("Diagnosis saved to droplet_diagnosis.txt")
    client.close()

if __name__ == "__main__":
    check_status()
