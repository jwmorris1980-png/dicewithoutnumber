import sys
import os

# Add parent directory to path to import dice_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dice_service import DiceService

def test_dice_parser():
    service = DiceService()
    
    test_cases = [
        "1d20",
        "2d6+2",
        "1d20+1d4+5",
        "4d6kh3 + 1d20",
        "2d6 - 1d4",
        "3x 1d20+5",
        "2#1d6",
        "10+5 - 2",
        "26", # Fuzzy 2d6
        "120", # Fuzzy 1d20
    ]
    
    print("Testing Dice Parser...")
    for case in test_cases:
        print(f"\n--- Testing: {case} ---")
        try:
            # We'll need a new method for structured results or just use roll_dice
            # For now, let's see what the current roll_dice does (it should probably fail on multiple pools)
            result_msg, total = service.roll_dice(case)
            print(f"Result: {result_msg}")
            print(f"Total: {total}")
        except Exception as e:
            print(f"ERROR: {case} failed with {e}")

if __name__ == "__main__":
    test_dice_parser()
