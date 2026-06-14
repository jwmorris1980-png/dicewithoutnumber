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
    if err: print('ERR:', err)
    return out

print("=== nginx config ===")
run("sudo cat /etc/nginx/sites-enabled/dicewithoutnumber")
print()
print("=== curl https test ===")
run("curl -sk https://localhost/catalog/ | head -100")
print()
print("=== sparks-magic.com/catalog test ===")
run("curl -sk https://sparks-magic.com/catalog/ | head -100")
c.close()
