import paramiko
import os
from services.secret_loader import load_project_env

def restart():
    with open("do_ip.txt", "r") as f:
        ip = f.read().strip()
    
    user = "root"
    load_project_env()
    password = os.getenv("ORACLE_PASSWORD")
    if not password:
        print("Missing ORACLE_PASSWORD in your private env file.")
        return
    
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, password=password)
    
    print("Killing existing bot processes on 8080...")
    client.exec_command("fuser -k 8080/tcp")
    
    print("Restarting systemd service...")
    stdin, stdout, stderr = client.exec_command("systemctl restart dicewithoutnumber")
    print("Verifying tracker.py content...")
    stdin, stdout, stderr = client.exec_command("grep 'ac: int,' /root/DICEwithoutNumber/cogs/tracker.py")
    output = stdout.read().decode()
    if "ac: int" in output:
        print("[v] New code confirmed in tracker.py")
    else:
        print("[!] Warning: New code not found in tracker.py on server!")

    print("Verifying index.html content...")
    stdin, stdout, stderr = client.exec_command("grep 'bench' /root/DICEwithoutNumber/web/index.html")
    output = stdout.read().decode()
    if "bench" in output:
        print("[v] New code confirmed in index.html")
    print("Inspecting DB for guild 1437247431560400928...")
    stdin, stdout, stderr = client.exec_command("cd /root/DICEwithoutNumber && python3 -c 'import sqlite3, json; conn=sqlite3.connect(\"data/bot_database.db\"); c=conn.cursor(); c.execute(\"SELECT data FROM trackers WHERE guild_id = 1437247431560400928\"); r=c.fetchone(); print(json.dumps(json.loads(r[0]), indent=2)) if r else print(\"No data\")'")
    print(stdout.read().decode())

    print("Checking logs for sync command...")
    stdin, stdout, stderr = client.exec_command("journalctl -u dicewithoutnumber -n 100 | grep -i sync")
    print(stdout.read().decode())

    client.close()

if __name__ == "__main__":
    restart()
