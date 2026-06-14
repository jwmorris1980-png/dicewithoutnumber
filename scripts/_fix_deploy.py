import paramiko, os
key = os.path.expanduser('~/.dicewithoutnumber/oracle_key.pem')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('129.153.219.159', username='ubuntu', key_filename=key)

cmds = [
    'git --git-dir=/home/ubuntu/bot.git log --oneline -5',
    'git --git-dir=/home/ubuntu/bot.git --work-tree=/home/ubuntu/DICEwithoutNumber ls-files --others --exclude-standard | grep image_server | head -5',
    'git --git-dir=/home/ubuntu/bot.git show HEAD:imagecatalog.service | head -3',
    'sudo git --work-tree=/home/ubuntu/DICEwithoutNumber --git-dir=/home/ubuntu/bot.git checkout -f main 2>&1',
    'ls /home/ubuntu/DICEwithoutNumber/image_server/',
    'ls /home/ubuntu/DICEwithoutNumber/imagecatalog.service',
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
