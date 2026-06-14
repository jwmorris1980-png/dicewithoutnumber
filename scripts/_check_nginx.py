import paramiko, os
key = os.path.expanduser('~/.dicewithoutnumber/oracle_key.pem')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('129.153.219.159', username='ubuntu', key_filename=key)

cmds = [
    'sudo cat /etc/nginx/nginx.conf',
    'sudo find /etc/nginx -type f | sort',
    'curl -s http://localhost:8001/ | head -5',
]
for cmd in cmds:
    _, o, e = c.exec_command(cmd)
    print('CMD:', cmd)
    print(o.read().decode())
    err = e.read().decode()
    if err:
        print('ERR:', err)
    print('---')
c.close()
