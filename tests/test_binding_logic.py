import unittest
from unittest.mock import MagicMock

# Minimal mock of DatabaseService for testing lookup logic
class MockDatabaseService:
    def __init__(self):
        self.bindings = {} # (user_id, target_id, target_type) -> char_name
        self.chars = {} # (user_id, char_name) -> data
        self.global_active = {} # user_id -> char_name

    def get_binding(self, user_id, target_id, target_type):
        return self.bindings.get((str(user_id), str(target_id), target_type))

    def get_character(self, user_id, char_name):
        return self.chars.get((str(user_id), str(char_name)))

    def get_active_character(self, user_id, channel_id=None, category_id=None):
        user_id = str(user_id)
        # 1. Channel
        if channel_id:
            name = self.get_binding(user_id, channel_id, 'channel')
            if name: return self.get_character(user_id, name)
        # 2. Category
        if category_id:
            name = self.get_binding(user_id, category_id, 'category')
            if name: return self.get_character(user_id, name)
        # 3. Global
        name = self.global_active.get(user_id)
        if name: return self.get_character(user_id, name)
        return None

class TestBindingLogic(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseService()
        self.user_id = "123"
        self.db.chars[(self.user_id, "Valerius")] = {"name": "Valerius", "hp": 10}
        self.db.chars[(self.user_id, "Alt")] = {"name": "Alt", "hp": 5}

    def test_global_fallback(self):
        self.db.global_active[self.user_id] = "Valerius"
        char = self.db.get_active_character(self.user_id, "chan_1", "cat_1")
        self.assertEqual(char["name"], "Valerius")

    def test_category_override(self):
        self.db.global_active[self.user_id] = "Valerius"
        self.db.bindings[(self.user_id, "cat_1", "category")] = "Alt"
        char = self.db.get_active_character(self.user_id, "chan_1", "cat_1")
        self.assertEqual(char["name"], "Alt")

    def test_channel_override(self):
        self.db.global_active[self.user_id] = "Valerius"
        self.db.bindings[(self.user_id, "cat_1", "category")] = "Alt"
        self.db.bindings[(self.user_id, "chan_special", "channel")] = "Valerius"
        
        # Special channel uses Valerius
        char1 = self.db.get_active_character(self.user_id, "chan_special", "cat_1")
        self.assertEqual(char1["name"], "Valerius")
        
        # Other channel in same category uses Alt
        char2 = self.db.get_active_character(self.user_id, "chan_other", "cat_1")
        self.assertEqual(char2["name"], "Alt")

if __name__ == '__main__':
    unittest.main()
