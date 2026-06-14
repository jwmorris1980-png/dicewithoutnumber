"""
find_test_guild.py
SSH to the Oracle server, read the bot's DB/logs to list all guilds it's in,
then print the ID for "Games Without Number" so you can paste it into .env.

Run:  python scripts/find_test_guild.py
"""
import os
import paramiko
from pathlib import Path

KEY = os.path.expanduser("~/.dicewithoutnumber/oracle_key.pem")
SERVER = "129.153.219.159"
USER = "ubuntu"


def run(c, cmd):
    _, o, e = c.exec_command(cmd)
    out = o.read().decode().strip()
    err = e.read().decode().strip()
    return out, err


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SERVER, username=USER, key_filename=KEY)

    print("=== Guilds the bot is currently in (from bot logs) ===\n")

    # Method 1: grep the bot log for guild names on_ready / join events
    out, _ = run(c, "grep -i 'guild\\|server' /home/ubuntu/DICEwithoutNumber/bot_new.log 2>/dev/null | grep -i 'games without number\\|joined\\|guild name' | tail -30")
    if out:
        print(out)

    print("\n=== Guild IDs from database ===\n")

    # Method 2: query the SQLite database for all guild IDs with any stored data
    out, err = run(c, r"""python3 - <<'EOF'
import sqlite3, os, json
db_path = '/home/ubuntu/DICEwithoutNumber/data/bot.db'
if not os.path.exists(db_path):
    # Try to find any .db file
    import glob
    dbs = glob.glob('/home/ubuntu/DICEwithoutNumber/data/*.db')
    db_path = dbs[0] if dbs else None

if db_path:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # List all tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print(f"Tables: {tables}")
    # Try to find guild IDs in any table with a guild_id column
    for table in tables:
        try:
            c.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in c.fetchall()]
            if 'guild_id' in cols:
                c.execute(f"SELECT DISTINCT guild_id FROM {table} WHERE guild_id IS NOT NULL LIMIT 50")
                rows = c.fetchall()
                if rows:
                    print(f"  {table}: {[r[0] for r in rows]}")
        except Exception as e:
            pass
    conn.close()
else:
    print("No database found — bot may store data differently")
EOF
""")
    if out:
        print(out)
    if err:
        print("ERR:", err)

    print("\n=== Recent guild activity from logs ===\n")
    out, _ = run(c, "grep -i 'guild\\|server' /home/ubuntu/DICEwithoutNumber/bot_new.log 2>/dev/null | tail -50")
    if out:
        # Filter for lines that look like guild join/info
        for line in out.splitlines():
            low = line.lower()
            if any(k in low for k in ["guild", "server", "games", "without", "number"]):
                print(line)

    print("\n=== Tip ===")
    print("Find 'Games Without Number' in the list above.")
    print("Then add this to your .dicewithoutnumber/.env file:")
    print("  TEST_GUILD_ID=<the guild ID>")
    print("")
    print("Or run !testguildid in any channel in that server to have the bot print it.")

    c.close()


if __name__ == "__main__":
    main()
