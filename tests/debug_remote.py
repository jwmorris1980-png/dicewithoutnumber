import paramiko
import os
from services.secret_loader import load_project_env

def check_remote_file():
    if not os.path.exists('do_ip.txt'):
        print('do_ip.txt not found')
        return
    with open('do_ip.txt') as f:
        ip = f.read().strip()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        load_project_env()
        password = os.getenv("ORACLE_PASSWORD")
        if not password:
            print("Missing ORACLE_PASSWORD in your private env file.")
            return
        ssh.connect(ip, username='root', password=password)
        
        # Read bot.py lines 40-50
        print("--- bot.py lines 40-50 ---")
        stdin, stdout, stderr = ssh.exec_command('sed -n "40,50p" /root/DICEwithoutNumber/bot.py')
        print(stdout.read().decode('utf-8'))
        
        # Check current running process command line
        print("--- Running process ---")
        stdin, stdout, stderr = ssh.exec_command('ps aux | grep bot.py | grep -v grep')
        print(stdout.read().decode('utf-8'))
        
        # Check logs for "Message received"
        print("--- Recent logs with 'Message received' ---")
        stdin, stdout, stderr = ssh.exec_command('grep "Message received" /root/DICEwithoutNumber/bot_new.log | tail -n 10')
        print(stdout.read().decode('utf-8'))
        
        ssh.close()
    except Exception as e:
        print(f"SSH Error: {e}")

if __name__ == '__main__':
    check_remote_file()
