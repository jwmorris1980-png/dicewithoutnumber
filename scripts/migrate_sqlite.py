import os
import json
import sqlite3
import sys

# Add project root to path
sys.path.insert(0, os.getcwd())

from services.database import DatabaseService

def migrate_characters(db):
    print("Migrating characters...")
    chars_dir = "data/characters"
    if not os.path.exists(chars_dir):
        print("No characters to migrate.")
        return

    count = 0
    for user_id in os.listdir(chars_dir):
        user_path = os.path.join(chars_dir, user_id)
        if not os.path.isdir(user_path):
            continue
        
        active_char_name = None
        # Check for active.txt
        active_file = os.path.join(user_path, "active.txt")
        if os.path.exists(active_file):
            with open(active_file, 'r') as f:
                active_char_name = f.read().strip()

        for filename in os.listdir(user_path):
            if filename.endswith(".json"):
                char_name = filename[:-5]
                with open(os.path.join(user_path, filename), 'r') as f:
                    try:
                        char_data = json.load(f)
                        # System detection (crude)
                        system = char_data.get("system", "WWN")
                        db.save_character(user_id, char_name, system, char_data)
                        
                        # Set active status
                        if char_name == active_char_name:
                            with db._get_connection() as conn:
                                conn.execute('UPDATE characters SET is_active = 1 WHERE user_id = ? AND character_name = ?', (user_id, char_name))
                        
                        count += 1
                    except Exception as e:
                        print(f"Failed to migrate character {char_name} for user {user_id}: {e}")
    print(f"Migrated {count} characters.")

def migrate_trackers(db):
    print("Migrating trackers...")
    trackers_dir = "data/trackers"
    if not os.path.exists(trackers_dir):
        print("No trackers to migrate.")
        return

    count = 0
    for filename in os.listdir(trackers_dir):
        if filename.endswith(".json"):
            guild_id = filename[:-5]
            with open(os.path.join(trackers_dir, filename), 'r') as f:
                try:
                    tracker_data = json.load(f)
                    db.save_tracker(guild_id, tracker_data)
                    count += 1
                except Exception as e:
                    print(f"Failed to migrate tracker for guild {guild_id}: {e}")
    print(f"Migrated {count} trackers.")

def migrate_campaigns(db):
    print("Migrating campaigns...")
    campaigns_dir = "data/campaigns"
    if not os.path.exists(campaigns_dir):
        print("No campaigns to migrate.")
        return

    count = 0
    for filename in os.listdir(campaigns_dir):
        if filename.endswith(".json"):
            guild_id = filename[:-5]
            with open(os.path.join(campaigns_dir, filename), 'r') as f:
                try:
                    campaign_data = json.load(f)
                    with db._get_connection() as conn:
                        conn.execute('INSERT OR REPLACE INTO campaigns (guild_id, data) VALUES (?, ?)', (guild_id, json.dumps(campaign_data)))
                    count += 1
                except Exception as e:
                    print(f"Failed to migrate campaign for guild {guild_id}: {e}")
    print(f"Migrated {count} campaigns.")

if __name__ == "__main__":
    db = DatabaseService()
    migrate_characters(db)
    migrate_trackers(db)
    migrate_campaigns(db)
    print("Migration complete!")
