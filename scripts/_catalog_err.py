import paramiko, os
key = os.path.expanduser('~/.dicewithoutnumber/oracle_key.pem')
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('129.153.219.159', username='ubuntu', key_filename=key)
def run(cmd):
    _, o, e = c.exec_command(cmd)
    out = o.read().decode().strip(); err = e.read().decode().strip()
    if out: print(out)
    if err: print('ERR:', err)

run("tail -30 /home/ubuntu/DICEwithoutNumber/catalog.log")
print("---")
run("curl -sv http://127.0.0.1:8001/ 2>&1 | tail -20")
print("---")
run("python3 -c \"import json; d=json.load(open('/home/ubuntu/DICEwithoutNumber/image_server/catalog.json')); print(len(d['images']), 'entries OK')\"")
c.close()
