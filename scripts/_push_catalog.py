"""Push the local catalog.json to the server's persistent disk path, then restart the service."""
import paramiko, os
from pathlib import Path

key = os.path.expanduser('~/.dicewithoutnumber/oracle_key.pem')
local_catalog = Path(__file__).parent.parent / 'image_server' / 'catalog.json'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('129.153.219.159', username='ubuntu', key_filename=key)

def run(cmd):
    _, o, e = c.exec_command(cmd)
    out = o.read().decode().strip()
    err = e.read().decode().strip()
    if out: print(' ', out)
    if err and 'WARNING' not in err: print('  ERR:', err)
    return out

# Find where the catalog is actually being read from
print("[1] Checking catalog path on server...")
run("ls -la /var/data/catalog.json 2>/dev/null || echo 'no /var/data'")
run("ls -la /home/ubuntu/DICEwithoutNumber/image_server/catalog.json 2>/dev/null || echo 'no local'")

# Upload the new catalog to both locations
print("[2] Uploading catalog.json...")
sftp = c.open_sftp()
sftp.put(str(local_catalog), '/home/ubuntu/DICEwithoutNumber/image_server/catalog.json')
print("  Uploaded to /home/ubuntu/DICEwithoutNumber/image_server/catalog.json")

# Also copy to /var/data if it exists
try:
    sftp.stat('/var/data')
    sftp.put(str(local_catalog), '/var/data/catalog.json')
    print("  Uploaded to /var/data/catalog.json")
except FileNotFoundError:
    print("  /var/data not mounted (expected on Oracle free tier)")
sftp.close()

# Restart the catalog service to reload
print("[3] Restarting imagecatalog.service...")
run("sudo systemctl restart imagecatalog.service")

import time; time.sleep(2)

print("[4] Verifying...")
run("curl -s http://127.0.0.1:8001/ 2>/dev/null | head -c 200")

c.close()
print("\nDone.")
