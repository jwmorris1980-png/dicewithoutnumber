import urllib.request
import json
import ssl
import time
import os

token = os.getenv("DIGITALOCEAN_TOKEN") or os.getenv("DO_API_TOKEN")
if not token:
    raise SystemExit("Missing DIGITALOCEAN_TOKEN (or DO_API_TOKEN) in your private env file.")
pub_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINuoVUEoy9YCVXigG4a8N/dpxrUdzrHiii1t8r6zWEVF john.morris@digitalocean"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Add SSH Key to DO
keys_url = "https://api.digitalocean.com/v2/account/keys"
key_data = json.dumps({"name": "Desktop Key", "public_key": pub_key}).encode('utf-8')
key_req = urllib.request.Request(keys_url, data=key_data, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, method='POST')

try:
    key_resp = urllib.request.urlopen(key_req, context=ctx)
    key_info = json.loads(key_resp.read())
    ssh_key_id = key_info['ssh_key']['id']
    print(f"Added SSH Key (ID: {ssh_key_id})")
except urllib.error.HTTPError as e:
    if e.code == 422: # Unprocessable Entity (usually means key already exists)
        print("Key already exists. Fetching keys...")
        get_keys_req = urllib.request.Request(keys_url, headers={'Authorization': f'Bearer {token}'})
        get_keys_resp = urllib.request.urlopen(get_keys_req, context=ctx)
        keys = json.loads(get_keys_resp.read())['ssh_keys']
        ssh_key_id = next(k['id'] for k in keys if k['public_key'].strip() == pub_key.strip())
        print(f"Found existing key (ID: {ssh_key_id})")
    else:
        print(f"Error adding key: {e.read()}")
        exit(1)

# 2. Delete Existing Droplets (for clean slate)
droplets_url = "https://api.digitalocean.com/v2/droplets"
get_drops_req = urllib.request.Request(droplets_url, headers={'Authorization': f'Bearer {token}'})
get_drops_resp = urllib.request.urlopen(get_drops_req, context=ctx)
droplets = json.loads(get_drops_resp.read()).get('droplets', [])

for droplet in droplets:
    d_id = droplet['id']
    print(f"Deleting Droplet {d_id}...")
    del_req = urllib.request.Request(f"{droplets_url}/{d_id}", headers={'Authorization': f'Bearer {token}'}, method='DELETE')
    urllib.request.urlopen(del_req, context=ctx)

if droplets:
    print("Waiting 10 seconds for deletion...")
    time.sleep(10)

# 3. Create New Droplet
create_data = json.dumps({
    "name": "dicewithoutnumber-bot",
    "region": "sfo3",
    "size": "s-1vcpu-1gb",
    "image": "ubuntu-22-04-x64",
    "ssh_keys": [ssh_key_id],
    "backups": False,
    "ipv6": False
}).encode('utf-8')

create_req = urllib.request.Request(droplets_url, data=create_data, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, method='POST')
print("Creating new Droplet...")
try:
    create_resp = urllib.request.urlopen(create_req, context=ctx)
    new_drop = json.loads(create_resp.read())['droplet']
    new_id = new_drop['id']
    print(f"Droplet created (ID: {new_id}). Waiting for IP address assignment...")
    
    # Poll for IP
    ip = None
    for _ in range(20):
        time.sleep(10)
        check_req = urllib.request.Request(f"{droplets_url}/{new_id}", headers={'Authorization': f'Bearer {token}'})
        check_resp = urllib.request.urlopen(check_req, context=ctx)
        drop_data = json.loads(check_resp.read())['droplet']
        networks = drop_data.get('networks', {}).get('v4', [])
        for net in networks:
            if net.get('type') == 'public':
                ip = net.get('ip_address')
                break
        if ip:
            break
            
    print(f"Droplet ready at IP: {ip}")
    
    # Save IP to a file so we can read it in subsequent commands
    with open("do_ip.txt", "w") as f:
        f.write(ip)
        
except Exception as e:
    print(f"Error creating droplet: {e}")
    if hasattr(e, 'read'): print(e.read())
