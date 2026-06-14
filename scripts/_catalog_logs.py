import paramiko, os
key = os.path.expanduser('~/.dicewithoutnumber/oracle_key.pem')
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('129.153.219.159', username='ubuntu', key_filename=key)
def run(cmd):
    _, o, e = c.exec_command(cmd)
    out = o.read().decode().strip(); err = e.read().decode().strip()
    if out: print(out)
    if err: print('ERR:', err)
    return out
run("sudo journalctl -u imagecatalog.service -n 20 --no-pager")
c.close()
