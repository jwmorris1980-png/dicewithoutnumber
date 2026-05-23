import random
import re
import logging

logger = logging.getLogger(__name__)

class DiceService:
    def __init__(self):
        # Configuration limits
        self.MAX_DICE = 100
        self.MAX_SIDES = 1000000
        self.MAX_TOTAL_DICE = 500

    def roll(self, expression):
        """Backward-compatible wrapper."""
        return self.roll_dice(expression)

    def _convert_word_numbers(self, text: str):
        words_to_digits = {
            "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
            "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
        }
        for word, digit in words_to_digits.items():
            text = re.sub(rf'\b{word}\b', digit, text, flags=re.IGNORECASE)
        return text

    def parse_and_roll(self, expression: str):
        """
        Comprehensive dice parser. 
        Supports:
        - Multiple pools: 2d6 + 1d4 + 2
        - Subtraction: 2d6 - 1d4
        - Keep/Drop: 4d6kh3, 2d10dl1
        - Repetitions: 3x 1d20+5
        - Fuzzy parsing: '26' -> 2d6
        
        Returns: (total, details_string, error_message, repeats)
        """
        if not expression:
            return 0, "", "Empty expression.", 1

        expression = str(expression).lower().strip()
        
        # Forgiving replacements
        expression = expression.replace("million", "000000")
        replacements = {
            "keephighest": "kh", "keephigh": "kh", "keep": "kh",
            "droplowest": "dl", "droplow": "dl", "drop": "dl",
            "drophighest": "dh", "drophigh": "dh",
            "keeplowest": "kl", "keeplow": "kl"
        }
        for full, short in replacements.items():
            expression = expression.replace(full, short)

        # 1. Handle Repetitions (3x ... or 2# ...)
        repeats = 1
        rep_match = re.match(r'^(\d+)\s*[x#]\s*(.*)$', expression)
        if rep_match:
            try:
                repeats = int(rep_match.group(1))
                expression = rep_match.group(2).strip()
                if repeats > 20:
                    return 0, "", "Max 20 repetitions in a single command.", 1
            except:
                pass
        
        # 2. Fuzzy Parsing for simple numbers
        # Only do this if it's a clear 2-digit number and NO other text/spaces
        # This prevents "!wnroll 26" from becoming 2d6 if it was meant to be a literal 26,
        # but keeps it for people who want the shortcut.
        # We also skip this if it looks like a long Discord ID.
        if expression.isdigit() and len(expression) == 2:
            logger.info(f"Fuzzy parsing digit string: {expression}")
            expression = f"{expression[0]}d{expression[1:]}"

        # 3. Typos and Word conversion
        expression = expression.replace(" ", "")
        expression = re.sub(r'(?<=\d)[vfs](?=\d)', 'd', expression)
        expression = self._convert_word_numbers(expression)
        
        # 4. Find all terms and track where the dice expression ends
        # Support k/d as well as kh/dl/etc.
        term_pattern = re.compile(r'([+-]?)\s*(?:(\d*)d(\d+)(kh|kl|dl|dh|dr|k|d)?(\d+)?|(\d+))')
        
        matches = list(term_pattern.finditer(expression))
        if not matches:
             # Check if it was just a constant
             if expression.strip().isdigit() or (expression.strip().startswith('-') and expression.strip()[1:].isdigit()):
                val = int(expression.strip())
                return val, str(val), None, repeats, len(expression)
             return 0, "", f"Invalid dice format: `{expression}`", repeats, 0

        total_sum = 0
        details_parts = []
        dice_count_total = 0
        last_match_end = 0

        for match in matches:
            sign_str, count_str, sides_str, kd_type, kd_count_str, const_str = match.groups()
            last_match_end = match.end()
            
            multiplier = -1 if sign_str == '-' else 1
            
            if const_str:
                val = int(const_str)
                # Safety: If it looks like a Discord ID (very long), it's probably not a dice constant.
                if len(const_str) > 15:
                    return 0, "", f"Value `{const_str[:5]}...` is too large for a dice constant. Did you mean to use `!role`?", repeats, 0
                
                total_sum += val * multiplier
                details_parts.append(f"{sign_str if sign_str else '+'}{val}" if details_parts else str(val * multiplier))
            else:
                count = int(count_str) if count_str else 1
                sides = int(sides_str)
                
                dice_count_total += count
                if count > self.MAX_DICE or sides > self.MAX_SIDES or dice_count_total > self.MAX_TOTAL_DICE:
                    return 0, "", "Too many dice or sides!", repeats, 0
                
                rolls = [random.randint(1, sides) for _ in range(count)]
                
                dropped_indices = []
                if kd_type:
                    # Map k -> kh, d -> dl
                    if kd_type == 'k': kd_type = 'kh'
                    if kd_type == 'd' or kd_type == 'dr': kd_type = 'dl'
                    
                    # SPECIAL CASE: Stars Without Number Specialist (3d6 keep 2 / drop 1)
                    if not kd_count_str and count == 3 and sides == 6:
                        if kd_type == 'kh':
                            kd_count = 2
                            logger.info("Specialist detected (3d6kh): defaulting to keep 2")
                        elif kd_type == 'dl':
                            kd_count = 1
                            logger.info("Specialist detected (3d6dl): defaulting to drop 1")
                        else:
                            kd_count = int(kd_count_str) if kd_count_str else 1
                    else:
                        kd_count = int(kd_count_str) if kd_count_str else 1

                    if kd_count >= count:
                        kd_count = count - 1 # Prevent dropping everything
                        
                    indexed_rolls = list(enumerate(rolls))
                    if kd_type == 'dl': 
                        to_drop = sorted(indexed_rolls, key=lambda x: x[1])[:kd_count]
                    elif kd_type == 'dh':
                        to_drop = sorted(indexed_rolls, key=lambda x: x[1], reverse=True)[:kd_count]
                    elif kd_type == 'kh':
                        to_drop = sorted(indexed_rolls, key=lambda x: x[1])[:count-kd_count]
                    elif kd_type == 'kl':
                        to_drop = sorted(indexed_rolls, key=lambda x: x[1], reverse=True)[:count-kd_count]
                    else:
                        to_drop = []
                    
                    dropped_indices = [x[0] for x in to_drop]

                pool_sum = sum(rolls[i] for i in range(count) if i not in dropped_indices)
                total_sum += pool_sum * multiplier
                
                rolls_fmt = []
                for i, r in enumerate(rolls):
                    if i in dropped_indices:
                        rolls_fmt.append(f"~~{r}~~")
                    else:
                        rolls_fmt.append(str(r))
                
                # Format with sign
                pool_str = f"({', '.join(rolls_fmt)})"
                if sign_str:
                    details_parts.append(f"{sign_str}{pool_str}")
                else:
                    details_parts.append(pool_str if not details_parts else f"+{pool_str}")

        details = " ".join(details_parts)
        return total_sum, details, None, repeats, last_match_end

    def roll_dice(self, expression, target_ac=None):
        total, details, err, repeats, _ = self.parse_and_roll(expression)
        if err:
            return err, 0
        
        if repeats > 1:
            return f"Repetition {repeats}x: Use /wn-multiroll for detailed separate lines.", total
            
        result_msg = f"Rolling {expression}: {details} = **{total}**"
        return result_msg, total
