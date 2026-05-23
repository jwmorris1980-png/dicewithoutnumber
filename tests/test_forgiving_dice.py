import sys
import os
import re

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.dice_service import DiceService

def test_forgiving_dice():
    ds = DiceService()
    
    test_cases = [
        "1d20+5",
        "1 d20 + 5",
        "one d20 + five",
        "3 d6 kh 2",
        "3d6 keep highest 2",
        "4d6 drop lowest 2",
        "2d6 + 3",
        "ten d10",
        "one d8 - 1"
    ]
    
    print("Testing Forgiving Dice Parsing...")
    print("-" * 30)
    
    for tc in test_cases:
        result_msg, total = ds.roll_dice(tc)
        print(f"Input:  '{tc}'")
        print(f"Output: {result_msg}")
        print(f"Total:  {total}")
        print("-" * 30)

if __name__ == "__main__":
    test_forgiving_dice()
