import google.generativeai as genai
import os
import sys
sys.path.insert(0, 'd:\\Discord bot')
from game_data import SYSTEM_SPECS, create_foci_validation_prompt, get_swn_background_info, create_swn_character_sequence_prompt
from services.secret_loader import load_project_env

load_project_env()

class NarrativeService:
    def __init__(self):
        # Load providers from env
        self.provider = os.getenv("AI_PROVIDER", "gemini").lower()
        self.gemini_key = os.getenv("GOOGLE_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        
        self.gemini_chat = None
        self.groq_client = None
        
        # System instructions
        self.system_instruction = (
            "You are the Game Master (GM) for a tabletop roleplaying game campaign. "
            "Your role is to describe the world, react to player actions, and play all NPCs. "
            "Use the provided rule PDFs to adjudicate checks, combat, and other game mechanics. "
            "Be descriptive, fair, and engaging. "
            "Identify the player speaking by their name provided in the prompt. "
            "You will be told which game system to use (WWN, SWN, CWN, or WOG). Use ONLY that system's rules. Do not mix rule systems."
            "\n"
            "COMBAT RULES (STRICT - DO NOT DEVIATE):\n"
            "1. The bot has a strict combat system using commands: !startcombat, !initiative, !attack, !damage, !combatstatus, !endcombat\n"
            "2. DO NOT decide combat outcomes in narrative responses. Combat is handled by command inputs only.\n"
            "3. Interpret combatant actions ONLY as requests for combat commands if in active combat.\n"
            "4. Turn order: Highest initiative goes first. Attacker rolls attack. If hit (roll >= AC), attacker rolls damage. Then other combatant's turn.\n"
            "5. Do NOT narrate multiple turns or combat results. Let the players use commands for each action.\n"
            "6. During combat, respond with ONLY descriptive flavor text (1-2 sentences) about the action. Do NOT roll dice or calculate results yourself.\n"
            "\n"
            "VISUALS: If you describe a new location, scene, or battle map, specifically include the keyword [GENERATE_MAP] at the very end of your response. "
            "Do NOT use [GENERATE_MAP] for character close-ups or simple items, only for environmental scenes or maps. "
            "Never claim you cannot show maps or images; this bot can trigger visual generation. "
            "If the user asks to see/show/map/picture a location, give a short in-world description and end with [GENERATE_MAP]."
        )

        # Initialize Gemini if key exists
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                self.gemini_model = genai.GenerativeModel(
                    model_name='gemini-2.0-flash',
                    system_instruction=self.system_instruction
                )
                self.gemini_chat = self.gemini_model.start_chat(history=[])
                print("Gemini Engine initialized.")
            except Exception as e:
                print(f"Gemini initialization failed: {e}")
        
        # Initialize Groq if key exists
        if self.groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)
                self.groq_model = "llama-3.3-70b-versatile"
                self.groq_history = []
                print("Groq Engine initialized.")
            except ImportError:
                print("Groq library not installed. Please install 'groq' package.")
            except Exception as e:
                print(f"Groq initialization failed: {e}")

        # Rules data
        self.rules = {}

        if not self.gemini_chat and not self.groq_client:
            print("Warning: No AI providers configured (Gemini or Groq). Narrative Engine will fail.")

    def _get_game_lock_instruction(self, active_game):
        """
        Returns STRICT game-specific instructions to force AI to stay in system.
        MUST be forceful and explicit to prevent rule mixing.
        """
        game_locks = {
            "WWN": "[🔒 MANDATORY GAME LOCK - ENFORCE STRICTLY 🔒]\n"
                   "ACTIVE SYSTEM: Worlds Without Number (WWN) ONLY\n"
                   "SETTING: Medieval fantasy world with swords, magic, castles, forests, dungeons.\n"
                   "RULES: Use ONLY Worlds Without Number mechanics. IGNORE all SWN, CWN, WOG rules.\n"
                   "CHARACTER TYPES: Medieval fantasy classes - Fighter, Rogue, Mage, Cleric, etc.\n"
                   "IF PLAYER ASKS FOR NON-MEDIEVAL ELEMENTS: Adapt the idea to WWN flavor instead of refusing.\n"
                   "Never respond with capability refusals such as 'I cannot show maps'.\n",
            
            "SWN": "[🔒 MANDATORY GAME LOCK - ENFORCE STRICTLY 🔒]\n"
                   "ACTIVE SYSTEM: Stars Without Number (SWN) ONLY\n"
                   "SETTING: Science fiction universe with space exploration, advanced technology, alien worlds, starships.\n"
                   "RULES: Use ONLY Stars Without Number mechanics. IGNORE all WWN, CWN, WOG rules.\n"
                   "CHARACTER TYPES: Sci-fi classes - Gunslinger, Pilot, Hacker, Psionicist, Trader, Warrior, etc.\n"
                     "IF PLAYER ASKS FOR FANTASY ELEMENTS: Reinterpret them as sci-fi equivalents; do not hard-refuse.\n"
                     "Never respond with capability refusals such as 'I cannot show maps'.\n"
                   "EXAMPLE ACCEPT: 'Gunslinger for hire in SWN' - CREATE THIS CHARACTER\n"
                     "EXAMPLE ADAPT: 'Gunslinger in medieval setting' - reinterpret as frontier blaster specialist in SWN\n",
            
            "CWN": "[🔒 MANDATORY GAME LOCK - ENFORCE STRICTLY 🔒]\n"
                   "ACTIVE SYSTEM: Cities Without Number (CWN) ONLY\n"
                   "SETTING: Modern urban environments with hidden supernatural elements.\n"
                   "RULES: Use ONLY Cities Without Number mechanics. IGNORE all WWN, SWN, WOG rules.\n"
                   "CHARACTER TYPES: Urban fantasy classes - Street Mage, Detective, Urban Warrior, Fixer, etc.\n"
                     "Adapt requests to urban framing; avoid hard refusals.\n",
            
            "WOG": "[🔒 MANDATORY GAME LOCK - ENFORCE STRICTLY 🔒]\n"
                   "ACTIVE SYSTEM: Wolves of God (WOG) ONLY\n"
                   "SETTING: Dark Ages medieval world with Christian themes and historical realism.\n"
                   "RULES: Use ONLY Wolves of God mechanics. IGNORE all WWN, SWN, CWN rules.\n"
                   "CHARACTER TYPES: Dark Ages classes fitting Christian medieval setting.\n"
                     "Adapt modern/sci-fi asks to WOG flavor; avoid hard refusals.\n",
        }
        return game_locks.get(active_game, game_locks["WWN"])

    def generate_response(self, player_name, player_input, rules_context=None, sheet_context=None, memory_context=None, active_game="WWN"):
        """
        Generates a response using the preferred provider, with fallback support.
        """
        # Build Context Stack
        context_blocks = []
        
        # CRITICAL: Lock AI to specific rulebook
        game_lock = self._get_game_lock_instruction(active_game)
        context_blocks.append(game_lock)
        
        if memory_context:
            context_blocks.append(f"[REMEMBER / HOUSE RULES]:\n{memory_context}")
        
        if rules_context:
            context_blocks.append(f"[System Rule Check]:\n{rules_context}")
        
        if sheet_context:
            context_blocks.append(f"[Character Sheet Data]:\n{sheet_context}")

        # Contextualize input
        base_prompt = f"Player '{player_name}' says: {player_input}"
        full_prompt = "\n\n".join(context_blocks + [base_prompt])

        # Try Groq if it's the preferred provider or if Gemini is unavailable
        if (self.provider == "groq" or not self.gemini_chat) and self.groq_client:
            try:
                messages = [
                    {"role": "system", "content": self.system_instruction},
                ]
                for msg in self.groq_history:
                    messages.append(msg)
                
                messages.append({"role": "user", "content": full_prompt})
                
                chat_completion = self.groq_client.chat.completions.create(
                    messages=messages,
                    model=self.groq_model,
                    temperature=0.7,
                    max_tokens=1024,
                )
                response_text = chat_completion.choices[0].message.content
                
                # Update history (keep it brief)
                self.groq_history.append({"role": "user", "content": player_input})
                self.groq_history.append({"role": "assistant", "content": response_text})
                if len(self.groq_history) > 10:
                    self.groq_history = self.groq_history[-10:]
                
                return response_text
            except Exception as e:
                print(f"Groq request failed: {e}")
                if not self.gemini_chat:
                    return f"Narrative Engine Error (Groq): {e}"
                # Fallback to Gemini if request failed and Gemini is available

        # Fallback to or Priority Gemini
        if self.gemini_chat:
            try:
                response = self.gemini_chat.send_message(full_prompt)
                return response.text
            except Exception as e:
                return f"Narrative Engine Error (Gemini): {e}"

        return "Narrative Engine Offline. No providers responsive."

    def generate_character(self, player_name, description, rules_context=None, active_game="WWN"):
        """
        Generates a new character sheet based on description.
        active_game: The current game system to use for character creation.
        NOTE: Uses a FRESH session/model instance to avoid previous system context leaking.
        """
        game_lock = self._get_game_lock_instruction(active_game)
        
        # Build system-specific instructions
        if active_game == "WWN":
            system_info = (
                "WORLDS WITHOUT NUMBER CHARACTER RULES:\n"
                "- Choose 2 Foci at Level 1\n"
                "- Foci MUST be from the included WWN rulebook PDF\n"
                "- Do NOT invent or use Foci not in the official rulebook\n"
            )
            options_note = "- Foci: MUST be from the rulebook. Choose exactly 2 and list them as they appear in the PDF.\n"
            foci_validation = create_foci_validation_prompt("wwn")
        elif active_game == "CWN":
            system_info = (
                "CITIES WITHOUT NUMBER CHARACTER RULES:\n"
                "- Choose valid Edges from the CWN rulebook\n"
                "- Edges MUST be from the official CWN rulebook PDF\n"
            )
            options_note = "- Edges: MUST be from the rulebook. List them exactly as they appear in the PDF.\n"
            foci_validation = ""
        elif active_game == "SWN":
            system_info = (
                "STARS WITHOUT NUMBER - OFFICIAL CHARACTER CREATION\n"
                "Follow the 8-step sequence provided below.\n"
                "All skills, focuses, classes, and attributes MUST come from official SWN rulebook.\n"
            )
            char_sequence = create_swn_character_sequence_prompt(description)
            options_note = char_sequence
            foci_validation = ""
        elif active_game == "WOG":
            system_info = (
                "WOLVES OF GOD CHARACTER RULES:\n"
                "- Use valid character options from the WOG rulebook\n"
            )
            options_note = "- Character options: MUST be from the rulebook. List them exactly as they appear in the PDF.\n"
            foci_validation = ""
        else:
            system_info = f"Creating a {active_game} character using official rulebook options only.\n"
            options_note = ""
            foci_validation = ""
        
        prompt = (
            f"{game_lock}\n\n"
            f"TASK: Create a level 1 character for '{player_name}' based on this concept: '{description}'.\n"
            f"SYSTEM: {active_game}\n"
            f"{system_info}\n"
            f"RULES CONTEXT (from official rulebook):\n{rules_context if rules_context else 'Standard ' + active_game + ' Rules'}\n\n"
            f"{foci_validation}"
            f"OUTPUT FORMAT: Provide a clear Markdown-formatted character sheet for {active_game}.\n"
            f"Include:\n- Name, Class (from rulebook ONLY), Background (from rulebook ONLY)\n- Attributes/Stats (from {active_game} system)\n- HP, AC\n"
            f"{options_note}"
            f"- Skills: ONLY use skills that appear in the {active_game} rulebook. DO NOT make up skills.\n"
            f"- Equipment (from rulebook)\n- A brief backstory.\n\n"
            f"CRITICAL RULES - FOLLOW EXACTLY:\n1. Use ONLY {active_game} rules and mechanics\n2. All character options must come DIRECTLY from the official rulebook\n"
            f"3. All skills must come from the rulebook\n4. All classes must come from the rulebook\n5. Do NOT use rules from other systems\n"
        )
        
        # Try Groq if preferred
        if self.provider == "groq" and self.groq_client:
            try:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.groq_model,
                    temperature=0.7,
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                print(f"Groq character generation failed: {e}")

        # Default to Gemini
        if self.gemini_key:
            try:
                fresh_model = genai.GenerativeModel(
                    model_name='gemini-2.0-flash',
                    system_instruction=self.system_instruction
                )
                response = fresh_model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Gemini character generation failed: {e}"

        return "No AI provider available for character generation."
    
    def reset_campaign(self):
        """
        Resets the conversation history.
        """
        self.groq_history = []
        if self.gemini_chat:
            self.gemini_chat = self.gemini_model.start_chat(history=[])
            return "Campaign memory wiped. Starting fresh."
        return "Campaign history cleared."

    def load_all_necessary_rules(self, game_name):
        self.rules = {}
        if game_name == "SWN":
            self.rules["swn"] = self.load_rules_from_file("SWN_rules.py")
        elif game_name == "Worlds Without Number":
            self.rules["worlds_without_number"] = self.load_rules_from_file("Worlds_Without_Number.py")
        elif game_name == "CWN":
            self.rules["cwn"] = self.load_rules_from_file("CWN_rules.py")
        elif game_name == "WOG":
            self.rules["wog"] = self.load_rules_from_file("WOG_rules.py")

    def load_rules_from_file(self, filename):
        # Placeholder for the actual file loading logic
        return f"Rules from {filename} loaded."
