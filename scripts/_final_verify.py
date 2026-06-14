import paramiko, os
key = os.path.expanduser('~/.dicewithoutnumber/oracle_key.pem')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('129.153.219.159', username='ubuntu', key_filename=key)

def run(cmd):
    _, o, e = c.exec_command(cmd)
    out = o.read().decode().strip()
    err = e.read().decode().strip()
    if out: print(out)
    if err and 'WARNING' not in err: print('ERR:', err)
    return out

print("=== Image Catalog Service Status ===")
run("sudo systemctl is-active imagecatalog.service")
run("sudo systemctl status imagecatalog.service --no-pager -n 5")

print("\n=== Internal API (bot-side) ===")
run("curl -s http://127.0.0.1:8001/ | python3 -c \"import sys,json; d=json.load(sys.stdin); print('Total images:', d['total_images'], '| Types:', d['by_type'])\"")
run("curl -s 'http://127.0.0.1:8001/api/random?type=map' | python3 -c \"import sys,json; d=json.load(sys.stdin); print('Random map:', d['name'], '|', d['artist'])\"")
run("curl -s 'http://127.0.0.1:8001/api/random?type=portrait' | python3 -c \"import sys,json; d=json.load(sys.stdin); print('Random portrait:', d['name'], '|', d['artist'])\"")

print("\n=== Public URL (via nginx) ===")
run("curl -sk 'https://dicewithoutnumber.duckdns.org/catalog/' | python3 -c \"import sys,json; d=json.load(sys.stdin); print('Public catalog OK:', d['total_images'], 'images')\"")

print("\n=== Post-receive hook ===")
run("cat /home/ubuntu/bot.git/hooks/post-receive | grep -E 'restart|echo'")

c.close()
print("\nAll systems go.")
