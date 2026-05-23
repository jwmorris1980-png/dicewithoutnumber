import paramiko
import os
from services.secret_loader import load_project_env

def check_remote_status():
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
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, password=password)
    
    output_file = "remote_status.txt"
    with open(output_file, "w", encoding='utf-8') as f:
        f.write("--- Service Status ---\n")
        stdin, stdout, stderr = client.exec_command("systemctl status dicewithoutnumber")
        f.write(stdout.read().decode('utf-8', 'ignore'))
        
        f.write("\n--- Recent Logs ---\n")
        stdin, stdout, stderr = client.exec_command("journalctl -u dicewithoutnumber -n 20")
        f.write(stdout.read().decode('utf-8', 'ignore'))
        
        f.write("\n--- Network Listeners ---\n")
        stdin, stdout, stderr = client.exec_command("ss -tulpn | grep python")
        f.write(stdout.read().decode('utf-8', 'ignore'))

        f.write("\n--- DuckDNS Update ---\n")
        # Run curl to update DuckDNS with the SERVER IP
        duckdns_domain = os.getenv("DUCKDNS_DOMAIN", "dicewithoutnumber")
        duckdns_token = os.getenv("DUCKDNS_TOKEN")
        if duckdns_token:
            update_cmd = f'curl -k "https://www.duckdns.org/update?domains={duckdns_domain}&token={duckdns_token}"'
        else:
            update_cmd = 'echo "Missing DUCKDNS_TOKEN"'
        stdin, stdout, stderr = client.exec_command(update_cmd)
        f.write(stdout.read().decode('utf-8', 'ignore'))
    
    print(f"Status saved to {output_file}")
    client.close()

if __name__ == "__main__":
    check_remote_status()
