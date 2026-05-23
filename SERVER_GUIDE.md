# 🚀 Oracle Cloud Server: Management Guide

This guide covers how to manage your projects on the Oracle Cloud server (`129.153.219.159`).

## 📡 Connection Details
- **User:** `ubuntu`
- **IP:** `129.153.219.159`
- **Identity:** `~/.dicewithoutnumber/oracle_key.pem` or `ORACLE_KEY_PATH`

---

## 🏗️ Managing Projects

### 1. Starting a New Project
To make a new folder "Cloud-Ready":
1. Copy `scripts/init_oracle_deploy.py` and keep your SSH key in `~/.dicewithoutnumber/` or point `ORACLE_KEY_PATH` there.
2. Run: `python init_oracle_deploy.py`
3. This creates a Git remote and a `deploy.py` helper.

### 2. Standard Deployment
In any project folder with the toolkit set up:
```powershell
python deploy.py "Added new features"
```
*This handles the Git add, commit, and push automatically.*

---

## 🛠️ Server-Side Commands
You can run these from your local terminal using SSH:

### View Live Logs
```powershell
ssh -i %USERPROFILE%\.dicewithoutnumber\oracle_key.pem ubuntu@129.153.219.159 "sudo journalctl -u [project_name] -f"
```

### Restart a Service
```powershell
ssh -i %USERPROFILE%\.dicewithoutnumber\oracle_key.pem ubuntu@129.153.219.159 "sudo systemctl restart [project_name]"
```

### Stop / Start
```powershell
ssh -i %USERPROFILE%\.dicewithoutnumber\oracle_key.pem ubuntu@129.153.219.159 "sudo systemctl stop [project_name]"
ssh -i %USERPROFILE%\.dicewithoutnumber\oracle_key.pem ubuntu@129.153.219.159 "sudo systemctl start [project_name]"
```

---

## 📂 Troubleshooting
- **Permission Denied (publickey):** Ensure the path in `ORACLE_KEY_PATH` points to your private SSH key.
- **Service Not Found:** Ensure the service name matches the folder name exactly (e.g., `dicewithoutnumber.service`).
- **Bot not updating:** Check the `post-receive` hook on the server if the `git push` succeeds but the files don't change.
