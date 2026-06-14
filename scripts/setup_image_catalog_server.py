"""
setup_image_catalog_server.py
Run once: sets up the image catalog service on the Oracle server.
  python scripts/setup_image_catalog_server.py

What it does (all over SSH — no hands required):
  1. Installs fastapi + uvicorn on the server
  2. Drops the imagecatalog.service file into systemd
  3. Enables + starts the service on port 8001
  4. Adds an nginx location block at /catalog/ -> localhost:8001
  5. Updates the post-receive hook so future deploys restart both services
"""
import os
import secrets
import sys
import time
from pathlib import Path

import paramiko

# ── connection ─────────────────────────────────────────────────────────────
SERVER_IP   = "129.153.219.159"
SERVER_USER = "ubuntu"
KEY_ENV     = "ORACLE_KEY_PATH"
KEY_DEFAULT = str(Path.home() / ".dicewithoutnumber" / "oracle_key.pem")
KEY_PATH    = os.environ.get(KEY_ENV, KEY_DEFAULT)

# ── nginx snippet to inject ─────────────────────────────────────────────────
NGINX_LOCATION = """
    # Image Catalog — added by setup_image_catalog_server.py
    location /catalog/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
"""

# ──────────────────────────────────────────────────────────────────────────

def ssh_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER_IP, username=SERVER_USER, key_filename=KEY_PATH)
    return client


def run(client, cmd, check=True):
    print(f"  $ {cmd}")
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"    {out}")
    if err:
        print(f"    [stderr] {err}")
    return out


def main():
    print("=== Image Catalog Server Setup ===")
    print(f"Connecting to {SERVER_USER}@{SERVER_IP} ...")

    client = ssh_connect()
    print("Connected.\n")

    # 1. Install python deps
    print("[1/5] Installing fastapi + uvicorn ...")
    run(client, "pip3 install --quiet fastapi 'uvicorn[standard]'")

    # 2. Generate an admin key if one doesn't exist
    print("[2/5] Setting up IMAGE_ADMIN_KEY ...")
    key_file = "/home/ubuntu/.dicewithoutnumber/image_admin.key"
    existing = run(client, f"cat {key_file} 2>/dev/null || echo ''")
    if existing:
        print(f"    Admin key already exists.")
        admin_key = existing
    else:
        admin_key = secrets.token_urlsafe(32)
        run(client, f"mkdir -p /home/ubuntu/.dicewithoutnumber")
        run(client, f"echo -n '{admin_key}' > {key_file}")
        run(client, f"chmod 600 {key_file}")
        print(f"    Generated new admin key and saved to {key_file}")
        print(f"\n    *** SAVE THIS KEY — you need it for /addimage ***")
        print(f"    IMAGE_ADMIN_KEY = {admin_key}\n")

    # 3. Install systemd service
    print("[3/5] Installing imagecatalog.service ...")
    service_src = "/home/ubuntu/DICEwithoutNumber/imagecatalog.service"
    service_dst = "/etc/systemd/system/imagecatalog.service"
    run(client, f"sudo cp {service_src} {service_dst}")
    run(client, "sudo systemctl daemon-reload")
    run(client, "sudo systemctl enable imagecatalog.service")
    run(client, "sudo systemctl restart imagecatalog.service")
    time.sleep(2)
    status = run(client, "sudo systemctl is-active imagecatalog.service")
    print(f"    Service status: {status}")

    # 4. Patch nginx — add /catalog/ location if not already present
    print("[4/5] Patching nginx ...")
    already = run(client, "grep -c '/catalog/' /etc/nginx/sites-enabled/default 2>/dev/null || echo 0")
    if already.strip() == "0":
        # Insert location block before the closing } of the first server block
        patch = NGINX_LOCATION.replace("'", "'\\''")   # escape single quotes for shell
        run(client,
            "sudo python3 -c \""
            "import re, pathlib; "
            "p = pathlib.Path('/etc/nginx/sites-enabled/default'); "
            "txt = p.read_text(); "
            "block = r'''\\n    location /catalog/ {\\n"
            "        proxy_pass http://127.0.0.1:8001/;\\n"
            "        proxy_set_header Host \\$host;\\n"
            "        proxy_set_header X-Real-IP \\$remote_addr;\\n"
            "    }\\n'''; "
            "txt2 = re.sub(r'(location\\s*/\\s*\\{)', block + r'\\1', txt, count=1); "
            "p.write_text(txt2)"
            "\""
        )
        run(client, "sudo nginx -t && sudo systemctl reload nginx")
        print("    nginx patched and reloaded.")
    else:
        print("    nginx already has /catalog/ block — skipping.")

    # 5. Update the post-receive hook so future git pushes restart both services
    print("[5/5] Updating post-receive hook ...")
    hook_path = "/home/ubuntu/bot.git/hooks/post-receive"
    already_hook = run(client, f"grep -c 'imagecatalog' {hook_path} 2>/dev/null || echo 0")
    if already_hook.strip() == "0":
        run(client,
            f"sudo sed -i 's|systemctl restart dicewithoutnumber.service|"
            f"systemctl restart dicewithoutnumber.service\\n"
            f"sudo systemctl restart imagecatalog.service|' {hook_path}"
        )
        print("    Hook updated.")
    else:
        print("    Hook already restarts imagecatalog — skipping.")

    client.close()
    print("\n=== Setup complete! ===")
    print("Image catalog is live at: https://sparks-magic.com/catalog/")
    print("Add IMAGE_ADMIN_KEY to your bot .env to enable /addimage")


if __name__ == "__main__":
    main()
