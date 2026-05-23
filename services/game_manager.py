# GameManager to dynamically load game rules

from services.wwn_rules import roll_initiative as wwn_initiative, get_rules as wwn_rules
from services.swn_rules import roll_initiative as swn_initiative, get_swn_rules as swn_rules
from services.cwn_rules import roll_initiative as cwn_initiative, get_rules as cwn_rules
from services.wog_rules import roll_initiative as wog_initiative, get_rules as wog_rules

class GameManager:
    def __init__(self):
        self.active_game = "WWN"  # Default to Worlds Without Number
        self.rules = {
            "WWN": {
                "initiative": wwn_initiative,
                "rules": wwn_rules,
                "name": "Worlds Without Number",
                "description": "Worlds Without Number (WWN) - Medieval fantasy campaign using WWN rules."
            },
            "SWN": {
                "initiative": swn_initiative,
                "rules": swn_rules,
                "name": "Stars Without Number",
                "description": "Stars Without Number (SWN) - Science fiction campaign using SWN rules."
            },
            "CWN": {
                "initiative": cwn_initiative,
                "rules": cwn_rules,
                "name": "Cities Without Number",
                "description": "Cities Without Number (CWN) - Urban fantasy campaign using CWN rules."
            },
            "WOG": {
                "initiative": wog_initiative,
                "rules": wog_rules,
                "name": "Wolves of God",
                "description": "Wolves of God (WOG) - Dark Ages medieval campaign using WOG rules."
            },
        }

    def set_game(self, game_name):
        game_name = game_name.upper()
        if game_name in self.rules:
            self.active_game = game_name
            return f"✅ Game set to **{self.rules[game_name]['name']}**. Let's play!"
        return f"❌ Game not recognized. Valid options: WWN, SWN, CWN, WOG"

    def detect_and_set_game(self, user_input):
        """
        Automatically detect game system mentions in user input.
        Recognizes: WWN, SWN, CWN, WOG, and full names.
        Returns: (game_detected, game_name) tuple
        """
        user_input_lower = user_input.lower()
        
        # Check for game acronyms and full names
        game_triggers = {
            "WWN": ["wwn", "worlds without number", "world without number"],
            "SWN": ["swn", "stars without number", "star without number"],
            "CWN": ["cwn", "cities without number", "city without number"],
            "WOG": ["wog", "wolves of god", "wolf of god"],
        }
        
        for game_code, triggers in game_triggers.items():
            for trigger in triggers:
                if trigger in user_input_lower:
                    # Found a trigger, set the game
                    self.set_game(game_code)
                    return (True, self.get_active_game_name())
        
        return (False, None)

    def get_active_game(self):
        return self.active_game

    def get_active_game_name(self):
        return self.rules[self.active_game]["name"]

    def get_game_description(self):
        return self.rules[self.active_game]["description"]

    def roll_initiative(self):
        return self.rules[self.active_game]["initiative"]()

    def get_rules(self):
        return self.rules[self.active_game]["rules"]()