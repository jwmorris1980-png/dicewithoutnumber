import sqlite3
import os
import json
import logging

logger = logging.getLogger('discord')

class DatabaseService:
    def __init__(self, db_path="data/bot_database.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Characters Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    user_id TEXT,
                    character_name TEXT,
                    system TEXT,
                    data TEXT,
                    is_active INTEGER DEFAULT 0,
                    source_url TEXT,
                    PRIMARY KEY (user_id, character_name)
                )
            ''')
            
            # Migration: Add source_url to characters if it doesn't exist
            cursor.execute("PRAGMA table_info(characters)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'source_url' not in columns:
                cursor.execute("ALTER TABLE characters ADD COLUMN source_url TEXT")
            
            # Combat Trackers Table
            # Migration: Add channel_id to trackers if it doesn't exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trackers'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(trackers)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'channel_id' not in columns:
                    # Rename old table and create new one
                    cursor.execute("ALTER TABLE trackers RENAME TO trackers_old")
                    cursor.execute('''
                        CREATE TABLE trackers (
                            guild_id TEXT,
                            channel_id TEXT,
                            data TEXT,
                            PRIMARY KEY (guild_id, channel_id)
                        )
                    ''')
                    # Migrate old data (assume 'default' for old data)
                    cursor.execute("INSERT INTO trackers (guild_id, channel_id, data) SELECT guild_id, 'default', data FROM trackers_old")
                    cursor.execute("DROP TABLE trackers_old")
            else:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trackers (
                        guild_id TEXT,
                        channel_id TEXT,
                        data TEXT,
                        PRIMARY KEY (guild_id, channel_id)
                    )
                ''')
            
            # Campaigns Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaigns (
                    guild_id TEXT PRIMARY KEY,
                    data TEXT
                )
            ''')
            
            # Session Logs Table (for /recap)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_name TEXT,
                    message_content TEXT
                )
            ''')

            # Settings Table (for language, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    target_id TEXT,
                    setting_key TEXT,
                    setting_value TEXT,
                    PRIMARY KEY (target_id, setting_key)
                )
            ''')

            # Character Bindings Table (Scope-aware active character)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_bindings (
                    user_id TEXT,
                    target_id TEXT,
                    target_type TEXT, -- 'channel' or 'category'
                    character_name TEXT,
                    PRIMARY KEY (user_id, target_id, target_type)
                )
            ''')

            # Migration: Update old character_bindings (user_id, channel_id) to (user_id, target_id, target_type)
            cursor.execute("PRAGMA table_info(character_bindings)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'target_type' not in columns:
                # Rename old table and create new one
                cursor.execute("ALTER TABLE character_bindings RENAME TO character_bindings_old")
                cursor.execute('''
                    CREATE TABLE character_bindings (
                        user_id TEXT,
                        target_id TEXT,
                        target_type TEXT,
                        character_name TEXT,
                        PRIMARY KEY (user_id, target_id, target_type)
                    )
                ''')
                # Migrate old channel bindings (assume channel_id is target_id)
                cursor.execute("INSERT INTO character_bindings (user_id, target_id, target_type, character_name) SELECT user_id, channel_id, 'channel', character_name FROM character_bindings_old")
                cursor.execute("DROP TABLE character_bindings_old")

            # Chat History Table (Temporary/Recent only)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    channel_id TEXT,
                    author TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Reaction Roles Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reaction_roles (
                    message_id TEXT,
                    emoji TEXT,
                    role_id TEXT,
                    guild_id TEXT,
                    PRIMARY KEY (message_id, emoji)
                )
            ''')
            
            conn.commit()

    # Reaction Role Operations
    def add_reaction_role(self, guild_id, message_id, emoji, role_id):
        guild_id, message_id, role_id = str(guild_id), str(message_id), str(role_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO reaction_roles (guild_id, message_id, emoji, role_id)
                VALUES (?, ?, ?, ?)
            ''', (guild_id, message_id, emoji, role_id))
            conn.commit()

    def remove_reaction_role(self, message_id, emoji):
        message_id = str(message_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM reaction_roles WHERE message_id = ? AND emoji = ?', (message_id, emoji))
            conn.commit()

    def get_reaction_role(self, message_id, emoji):
        message_id = str(message_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?', (message_id, emoji))
            row = cursor.fetchone()
            return row[0] if row else None

    def list_reaction_roles(self, guild_id):
        guild_id = str(guild_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT message_id, emoji, role_id FROM reaction_roles WHERE guild_id = ?', (guild_id,))
            return [{"message_id": r[0], "emoji": r[1], "role_id": r[2]} for r in cursor.fetchall()]

    # Binding Operations
    def bind_character(self, user_id, target_id, target_type, char_name):
        user_id, target_id = str(user_id), str(target_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if char_name is None:
                cursor.execute('DELETE FROM character_bindings WHERE user_id = ? AND target_id = ? AND target_type = ?', (user_id, target_id, target_type))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO character_bindings (user_id, target_id, target_type, character_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, target_id, target_type, char_name))
            conn.commit()

    def get_binding(self, user_id, target_id, target_type):
        user_id, target_id = str(user_id), str(target_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT character_name FROM character_bindings WHERE user_id = ? AND target_id = ? AND target_type = ?', (user_id, target_id, target_type))
            row = cursor.fetchone()
            return row[0] if row else None

    # Settings Operations
    def set_setting(self, target_id, key, value):
        target_id = str(target_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (target_id, setting_key, setting_value)
                VALUES (?, ?, ?)
            ''', (target_id, key, str(value)))
            conn.commit()

    def get_setting(self, target_id, key, default=None):
        target_id = str(target_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT setting_value FROM settings WHERE target_id = ? AND setting_key = ?', (target_id, key))
            row = cursor.fetchone()
            if row:
                return row[0]
            return default

    # Character Operations
    def save_character(self, user_id, char_name, system, char_data, source_url=None):
        user_id = str(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Set other characters for this user to inactive
            cursor.execute('UPDATE characters SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            # If source_url is NOT provided, try to keep the existing one if it exists
            if source_url is None:
                cursor.execute('SELECT source_url FROM characters WHERE user_id = ? AND character_name = ?', (user_id, char_name))
                row = cursor.fetchone()
                if row:
                    source_url = row[0]

            # Insert or replace character
            cursor.execute('''
                INSERT OR REPLACE INTO characters (user_id, character_name, system, data, is_active, source_url)
                VALUES (?, ?, ?, ?, 1, ?)
            ''', (user_id, char_name, system, json.dumps(char_data), source_url))
            conn.commit()

    def get_active_character(self, user_id, channel_id=None, category_id=None):
        user_id = str(user_id)
        
        # 1. Check direct channel binding
        if channel_id:
            bound_name = self.get_binding(user_id, channel_id, 'channel')
            if bound_name:
                char = self.get_character(user_id, bound_name)
                if char: return char

        # 2. Check parent category binding
        if category_id:
            bound_name = self.get_binding(user_id, category_id, 'category')
            if bound_name:
                char = self.get_character(user_id, bound_name)
                if char: return char

        # 3. Fallback to global active
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data, source_url, system, character_name FROM characters WHERE user_id = ? AND is_active = 1', (user_id,))
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                data["source_url"] = row[1]
                data["system"] = row[2]
                data["name"] = row[3]
                return data
            return None

    def get_character(self, user_id, char_name):
        user_id = str(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data, system, source_url FROM characters WHERE user_id = ? AND character_name = ?', (user_id, char_name))
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                data["name"] = char_name
                data["system"] = row[1]
                data["source_url"] = row[2]
                return data
            return None

    def get_user_characters(self, user_id):
        user_id = str(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT character_name FROM characters WHERE user_id = ?', (user_id,))
            return [row[0] for row in cursor.fetchall()]

    # Starship Operations
    def save_ship(self, user_id, ship_name, ship_data):
        user_id = str(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Set other ships for this user to inactive
            cursor.execute('UPDATE starships SET is_active = 0 WHERE user_id = ?', (user_id,))
            # Insert or replace ship
            cursor.execute('''
                INSERT OR REPLACE INTO starships (user_id, ship_name, data, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (user_id, ship_name, json.dumps(ship_data)))
            conn.commit()

    def get_active_ship(self, user_id):
        user_id = str(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM starships WHERE user_id = ? AND is_active = 1', (user_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

    def get_ships(self, user_id):
        user_id = str(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT ship_name FROM starships WHERE user_id = ?', (user_id,))
            return [row[0] for row in cursor.fetchall()]

    def delete_ship(self, user_id, ship_name):
        user_id = str(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM starships WHERE user_id = ? AND ship_name = ?', (user_id, ship_name))
            conn.commit()

    # Tracker Operations
    def save_tracker(self, guild_id, tracker_data, channel_id="default"):
        guild_id = str(guild_id)
        channel_id = str(channel_id or "default")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO trackers (guild_id, channel_id, data) VALUES (?, ?, ?)', 
                          (guild_id, channel_id, json.dumps(tracker_data)))
            conn.commit()
        return True

    def get_tracker(self, guild_id, channel_id="default"):
        guild_id = str(guild_id)
        channel_id = str(channel_id or "default")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM trackers WHERE guild_id = ? AND channel_id = ?', (guild_id, channel_id))
            row = cursor.fetchone()
            
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except (json.JSONDecodeError, TypeError, ValueError):
                    return None
            return None

    # Campaign Operations
    def save_campaign(self, guild_id, campaign_data):
        guild_id = str(guild_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO campaigns (guild_id, data) VALUES (?, ?)', (guild_id, json.dumps(campaign_data)))
            conn.commit()

    def get_campaign(self, guild_id):
        guild_id = str(guild_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM campaigns WHERE guild_id = ?', (guild_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

    # Logging Operations
    def log_message(self, guild_id, user_name, content):
        guild_id = str(guild_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO session_logs (guild_id, user_name, message_content)
                VALUES (?, ?, ?)
            ''', (guild_id, user_name, content))
            conn.commit()

    def get_recent_logs(self, guild_id, limit=50):
        guild_id = str(guild_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, user_name, message_content 
                FROM session_logs 
                WHERE guild_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (guild_id, limit))
            rows = cursor.fetchall()
            # Return in chronological order
            return rows[::-1]

    def clear_logs(self, guild_id):
        guild_id = str(guild_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM session_logs WHERE guild_id = ?', (guild_id,))
            conn.commit()

    # Chat Support Operations
    def save_chat_message(self, guild_id, channel_id, author, content):
        guild_id, channel_id = str(guild_id), str(channel_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Insert message
            cursor.execute('''
                INSERT INTO chat_messages (guild_id, channel_id, author, content)
                VALUES (?, ?, ?, ?)
            ''', (guild_id, channel_id, author, content))
            
            # Prune old messages for this channel (keep last 50)
            cursor.execute('''
                DELETE FROM chat_messages 
                WHERE id IN (
                    SELECT id FROM chat_messages 
                    WHERE guild_id = ? AND channel_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT -1 OFFSET 50
                )
            ''', (guild_id, channel_id))
            conn.commit()

    def get_recent_chat(self, guild_id, channel_id, limit=50):
        guild_id, channel_id = str(guild_id), str(channel_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT author, content, timestamp 
                FROM chat_messages 
                WHERE guild_id = ? AND channel_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (guild_id, channel_id, limit))
            rows = cursor.fetchall()
            # Map to list of dicts and reverse (chronological)
            return [{"author": r[0], "content": r[1], "timestamp": r[2]} for r in rows][::-1]

    def get_active_channels(self, guild_id):
        guild_id = str(guild_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT channel_id
                FROM chat_messages 
                WHERE guild_id = ?
            ''', (guild_id,))
            return [row[0] for row in cursor.fetchall()]
