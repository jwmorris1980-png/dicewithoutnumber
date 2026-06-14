import paramiko, os
key = os.path.expanduser('~/.dicewithoutnumber/oracle_key.pem')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('129.153.219.159', username='ubuntu', key_filename=key)
cmds = [
    'ls /home/ubuntu/DICEwithoutNumber/',
    'ls /root/DICEwithoutNumber/ 2>/dev/null || echo NO_ROOT',
    'sudo find /etc/nginx -name "*.conf" 2>/dev/null',
    'cat /home/ubuntu/bot.git/hooks/post-receive',
    'ls /home/ubuntu/.local/bin/uvicorn && echo uvicorn_found',
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
