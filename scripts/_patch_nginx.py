"""Patch nginx dicewithoutnumber config to add /catalog/ proxy and update the post-receive hook."""
import paramiko, os

key = os.path.expanduser('~/.dicewithoutnumber/oracle_key.pem')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('129.153.219.159', username='ubuntu', key_filename=key)

def run(cmd):
    _, o, e = c.exec_command(cmd)
    out = o.read().decode().strip()
    err = e.read().decode().strip()
    if out: print(' ', out)
    if err: print('  ERR:', err)
    return out

# 1. Read current nginx config
print("[1] Reading nginx config...")
_, o, _ = c.exec_command("sudo cat /etc/nginx/sites-enabled/dicewithoutnumber")
nginx_conf = o.read().decode()
print(nginx_conf[:300])
print("---")

# 2. Add /catalog/ location block if not present
if '/catalog/' in nginx_conf:
    print("[2] /catalog/ already in nginx config — skipping")
else:
    print("[2] Patching nginx config...")
    # Write a Python patch script to the server and run it
    patch_script = r"""
import re, pathlib
p = pathlib.Path('/etc/nginx/sites-enabled/dicewithoutnumber')
txt = p.read_text()
block = '''
    # Image Catalog proxy — added automatically
    location /catalog/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
'''
# Insert before the first "location /" block
txt2 = re.sub(r'(\s+location\s+/\s*\{)', block + r'\1', txt, count=1)
p.write_text(txt2)
print("Patched.")
"""
    sftp = c.open_sftp()
    with sftp.file('/tmp/patch_nginx.py', 'w') as f:
        f.write(patch_script)
    sftp.close()
    run("sudo python3 /tmp/patch_nginx.py")
    run("sudo nginx -t && sudo systemctl reload nginx")
    print("  nginx reloaded")

# 3. Update post-receive hook
print("[3] Updating post-receive hook...")
_, o, _ = c.exec_command("cat /home/ubuntu/bot.git/hooks/post-receive")
hook = o.read().decode()
if 'imagecatalog' in hook:
    print("  Hook already has imagecatalog — skipping")
else:
    new_hook = hook.replace(
        'echo "Service restarted."',
        'echo "Bot service restarted."\nsudo systemctl restart imagecatalog.service\necho "Image catalog service restarted."'
    )
    sftp = c.open_sftp()
    with sftp.file('/tmp/new_hook', 'w') as f:
        f.write(new_hook)
    sftp.close()
    run("sudo cp /tmp/new_hook /home/ubuntu/bot.git/hooks/post-receive")
    run("sudo chmod +x /home/ubuntu/bot.git/hooks/post-receive")
    print("  Hook updated")

# 4. Verify
print("[4] Verifying...")
run("curl -s http://localhost:8001/api/random?type=map | python3 -c \"import sys,json; d=json.load(sys.stdin); print('CATALOG OK:', d.get('name','?'))\"")
run("curl -s http://localhost/catalog/api/random?type=map | python3 -c \"import sys,json; d=json.load(sys.stdin); print('NGINX PROXY OK:', d.get('name','?'))\"")

c.close()
print("\nAll done.")
