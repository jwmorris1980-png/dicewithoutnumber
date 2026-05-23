import os
import subprocess
import sys
from pathlib import Path

from services.secret_loader import get_secret_path

def run_command(command, description):
    print(f"[#] {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[!] Error: {e.stderr}")
        return None

def setup_project():
    project_dir = os.getcwd()
    project_name = os.path.basename(project_dir).lower().replace(" ", "_")
    
    print(f"Initializing Oracle Deployment for: {project_name}")

    # 1. Init Git
    if not os.path.exists(".git"):
        run_command("git init", "Initializing Git repository")

    # 2. Create refined .gitignore
    gitignore_content = """# Oracle Deployment Exclusions
venv/
.venv/
__pycache__/
*.pyc
.env
.env_actual
*.pem
do_ip.txt
*.log
*.zip
*.tar.gz
wheels/
.gemini/
node_modules/
dist/
build/
"""
    with open(".gitignore", "w") as f:
        f.write(gitignore_content)
    print("[+] Created standard .gitignore")

    # 3. Secure the Oracle Remote
    oracle_ip = "129.153.219.159"
    remote_url = f"ssh://ubuntu@{oracle_ip}/home/ubuntu/bot.git"
    
    # Check if remote already exists
    remotes = run_command("git remote", "Checking existing remotes")
    if "oracle" in remotes:
        run_command("git remote remove oracle", "Updating existing oracle remote")
    
    run_command(f"git remote add oracle {remote_url}", f"Linking to Oracle remote: {remote_url}")

    # 4. Deployment Helper Script (The "Quick-Push")
    deploy_script = f"""import subprocess
import sys
from services.secret_loader import get_secret_path, load_project_env

load_project_env()

def deploy():
    print("Deploying to Oracle Cloud...")
    try:
        subprocess.run("git add .", shell=True, check=True)
        msg = sys.argv[1] if len(sys.argv) > 1 else "Cloud update"
        subprocess.run(f'git commit -m "{{msg}}"', shell=True)
        key_path = get_secret_path("oracle_key.pem", "ORACLE_KEY_PATH")
        ssh_cmd = f'ssh -i "{{key_path}}" -o StrictHostKeyChecking=no'
        subprocess.run(f'git -c core.sshCommand="{{ssh_cmd}}" push oracle main', shell=True, check=True)
        print("Deployment Successful!")
    except Exception as e:
        print(f"Deployment Failed: {{e}}")

if __name__ == '__main__':
    deploy()
"""
    with open("deploy.py", "w") as f:
        f.write(deploy_script)
    print("[+] Created 'deploy.py' helper")

    print(f"\nSetup Complete!")
    print(f"To deploy, just run: python deploy.py 'your message'")
    print(f"NOTE: Store your private SSH key in {Path.home() / '.dicewithoutnumber' / 'oracle_key.pem'} or set ORACLE_KEY_PATH.")

if __name__ == "__main__":
    setup_project()
