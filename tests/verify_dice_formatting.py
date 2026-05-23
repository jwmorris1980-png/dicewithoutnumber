import re
import random

# Simplified version of parse_and_roll to test the formatting logic
def parse_and_roll(expression: str):
    expression = expression.replace(" ", "").lower()
    if not expression:
        return 0, "", "Empty expression."

    pattern = re.compile(r'^(\d*)d(\d+)(d)?(?:(kh|kl|k|dl|dh|dr|d)(\d+)?)?(?:([+-])(\d+))?$')
    match = pattern.match(expression)
    
    if not match:
        return 0, "", f"Invalid dice format: {expression}"

    count_str, sides_str, diplomat_flag, kd_type, kd_count_str, sign, mod_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    details = f"[{', '.join(map(str, rolls))}]"
    
    if sign and mod_str:
        mod = int(mod_str)
        if sign == '+':
            total += mod
            details += f" + {mod}"
        else:
            total -= mod
            details += f" - {mod}"

    return total, details, None

def test_roll_formatting():
    # Test cases
    expressions = ["1d20+1", "1d3+1", "2d6", "4d6dl1"]
    
    print("Testing roll formatting logic...")
    for expr in expressions:
        total, details, err = parse_and_roll(expr)
        if err:
            print(f"Error for {expr}: {err}")
            continue
        
        # This simulates the new formatting logic in bot
        msg = f"User 🎲 **{expr}**\n"
        msg += f"**Result:** {details}\n**Total:** {total}"
        
        print("-" * 20)
        print(msg)

if __name__ == "__main__":
    test_roll_formatting()
