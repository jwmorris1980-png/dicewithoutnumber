import unittest
import random
import re

# We'll mock a minimal DiceCog for testing the parser
class MockDiceCog:
    def _convert_word_numbers(self, text: str):
        words_to_digits = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5"}
        for word, digit in words_to_digits.items():
            text = re.sub(rf'\b{word}\b', digit, text, flags=re.IGNORECASE)
        return text

    def parse_and_roll(self, expression: str):
        if not expression: return 0, "", "Empty expression."
        expression = self._convert_word_numbers(expression).lower().replace(" ", "")
        pattern = re.compile(r'^(\d*)d(\d+)(?:(kh|kl|dl|dh|dr|d)(\d+)?)?(?:([+-])(\d+))?$')
        match = pattern.match(expression)
        if not match: return 0, "", "Invalid format"

        count_str, sides_str, kd_type, kd_count_str, sign, mod_str = match.groups()
        count = int(count_str) if count_str else 1
        sides = int(sides_str)
        mod = int(mod_str) if mod_str else 0
        if sign == '-': mod = -mod
        
        # Fixing a seed for deterministic testing
        random.seed(42) 
        rolls = [random.randint(1, sides) for _ in range(count)]
        
        dropped = []
        if kd_type:
            kd_count = int(kd_count_str) if kd_count_str else 1
            sorted_rolls = sorted(rolls)
            if kd_type in ['dl', 'd', 'dr']: dropped = sorted_rolls[:kd_count]
            elif kd_type == 'dh': dropped = sorted_rolls[-kd_count:]
            elif kd_type == 'kh': dropped = sorted_rolls[:-kd_count]
            elif kd_type == 'kl': dropped = sorted_rolls[kd_count:]
            
        total = sum(rolls) - sum(dropped)
        return total + mod, str(rolls), None

class TestDiceLogic(unittest.TestCase):
    def setUp(self):
        self.cog = MockDiceCog()

    def test_basic_rolls(self):
        # 1d20 with seed 42: random.randint(1, 20) -> 4
        total, _, err = self.cog.parse_and_roll("1d20")
        self.assertIsNone(err)
        self.assertEqual(total, 4)

    def test_word_numbers(self):
        total, _, err = self.cog.parse_and_roll("two d20")
        self.assertIsNone(err)
        # 2d20 with seed 42 -> 4, 1
        self.assertEqual(total, 5)

    def test_modifiers(self):
        total, _, err = self.cog.parse_and_roll("1d20+5")
        self.assertEqual(total, 9) # 4 + 5

    def test_keep_high(self):
        # 4d6kh3 with seed 42 -> [6, 1, 1, 6]
        # kh3 -> drop smallest (1) -> [6, 1, 6] -> 13
        total, _, err = self.cog.parse_and_roll("4d6kh3")
        self.assertEqual(total, 13)

    def test_drop_low(self):
        # 2d20dl1 with seed 42 -> [4, 1]
        # dl1 -> drop 1 -> [4] -> 4
        total, _, err = self.cog.parse_and_roll("2d20dl1")
        self.assertEqual(total, 4)

if __name__ == '__main__':
    unittest.main()
