import sqlite3
import json

def inspect_db():
    conn = sqlite3.connect("data/bot_database.db")
    cursor = conn.cursor()
    
    guild_id = 1437247431560400928
    cursor.execute("SELECT data FROM trackers WHERE guild_id = ?", (guild_id,))
    row = cursor.fetchone()
    
    if row:
        print(f"Data for guild {guild_id}:")
        print(json.dumps(json.loads(row[0]), indent=2))
    else:
        print(f"No tracker data found for guild {guild_id}")
        
    conn.close()

if __name__ == "__main__":
    inspect_db()
