import subprocess
import sys
from services.secret_loader import get_secret_path, load_project_env

load_project_env()

def deploy():
    print("Deploying to Oracle Cloud...")
    try:
        subprocess.run("git add .", shell=True, check=True)
        msg = sys.argv[1] if len(sys.argv) > 1 else "Cloud update"
        subprocess.run(f'git commit -m "{msg}"', shell=True)
        key_path = get_secret_path("oracle_key.pem", "ORACLE_KEY_PATH")
        ssh_cmd = f'ssh -i "{key_path}" -o StrictHostKeyChecking=no'
        subprocess.run(f'git -c core.sshCommand="{ssh_cmd}" push oracle main', shell=True, check=True)
        print("Deployment Successful!")
    except Exception as e:
        print(f"Deployment Failed: {e}")

if __name__ == '__main__':
    deploy()
