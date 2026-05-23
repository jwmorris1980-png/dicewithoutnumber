"""
Strict Combat Service for Worlds Without Number rules
Prevents AI hallucination by enforcing rigid combat structure:
1. Initiative (higher roll goes first)
2. Attacker's turn: roll attack vs AC
3. If hit, roll damage
4. Defender's turn
5. Repeat
"""

class Combatant:
    def __init__(self, name, ac, hp):
        self.name = name
        self.ac = ac
        self.hp = hp
        self.max_hp = hp
        self.initiative_roll = 0

    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)
        return self.hp

    def is_alive(self):
        return self.hp > 0

    def set_initiative(self, roll):
        self.initiative_roll = roll


class CombatState:
    """Manages strict turn-based combat flow"""
    
    PHASE_INITIATIVE = "initiative"
    PHASE_ATTACKER_ROLL = "attacker_roll"
    PHASE_DAMAGE = "damage"
    PHASE_DEFENDER_TURN = "defender_turn"
    PHASE_COMBAT_END = "combat_end"

    def __init__(self):
        self.in_combat = False
        self.combatants = {}  # {name: Combatant}
        self.initiative_order = []  # [name, name, ...] in turn order
        self.current_turn_index = 0
        self.current_phase = self.PHASE_INITIATIVE
        self.current_attack_roll = None
        self.attack_beaten_ac = False

    def start_combat(self, combatant1_name, combatant1_ac, combatant1_hp,
                     combatant2_name, combatant2_ac, combatant2_hp):
        """Initialize combat with two combatants"""
        self.in_combat = True
        self.combatants = {
            combatant1_name: Combatant(combatant1_name, combatant1_ac, combatant1_hp),
            combatant2_name: Combatant(combatant2_name, combatant2_ac, combatant2_hp),
        }
        self.current_phase = self.PHASE_INITIATIVE
        self.current_turn_index = 0
        return (f"⚔️ **COMBAT STARTED!**\n\n"
                f"{combatant1_name} (AC {combatant1_ac}, HP {combatant1_hp}) vs {combatant2_name} (AC {combatant2_ac}, HP {combatant2_hp})\n\n"
                f"**NEXT STEPS:**\n"
                f"1️⃣ Both fighters roll 1d8 for initiative\n"
                f"2️⃣ Highest goes first\n"
                f"3️⃣ Attacker rolls 1d20 (+ modifiers) vs AC\n"
                f"4️⃣ If hit: roll damage\n\n"
                f"Use `!initiative <Name> <Roll>` to submit initiative rolls")

    def set_initiative(self, combatant_name, roll):
        """Set initiative roll for a combatant"""
        if combatant_name not in self.combatants:
            return f"Error: {combatant_name} not in combat."
        self.combatants[combatant_name].set_initiative(roll)
        
        # If both combatants have rolled, determine order
        if all(c.initiative_roll > 0 for c in self.combatants.values()):
            sorted_combatants = sorted(self.combatants.values(), key=lambda c: c.initiative_roll, reverse=True)
            self.initiative_order = [c.name for c in sorted_combatants]
            self.current_turn_index = 0
            self.current_phase = self.PHASE_ATTACKER_ROLL
            
            msg = f"\n**INITIATIVE ORDER:**\n"
            for i, name in enumerate(self.initiative_order, 1):
                roll = self.combatants[name].initiative_roll
                msg += f"{i}. {name} (rolled {roll})\n"
            msg += f"\n{self._get_current_combatant()} attacks first!"
            return msg
        
        return f"{combatant_name} rolled initiative: {roll}"

    def _get_current_combatant(self):
        """Get the name of whose turn it is"""
        if self.initiative_order:
            return self.initiative_order[self.current_turn_index % len(self.initiative_order)]
        return None

    def _get_other_combatant(self):
        """Get the other combatant's name"""
        current = self._get_current_combatant()
        for name in self.combatants:
            if name != current:
                return name
        return None

    def resolve_attack(self, attack_roll):
        """
        Resolve an attack roll vs defender's AC.
        Returns whether it hits and waits for damage roll if hit.
        CRITICAL: attack_roll must be 1d20 + modifiers, compared directly to AC.
        """
        if not self.in_combat:
            return "No combat in progress."
        
        if self.current_phase != self.PHASE_ATTACKER_ROLL:
            return f"Error: Current phase is {self.current_phase}, not attack phase."

        attacker = self._get_current_combatant()
        defender = self._get_other_combatant()
        defender_ac = self.combatants[defender].ac

        self.current_attack_roll = attack_roll

        # Attack hits if roll >= AC
        if attack_roll >= defender_ac:
            self.attack_beaten_ac = True
            self.current_phase = self.PHASE_DAMAGE
            return f"✅ **HIT!** {attacker} rolled {attack_roll} vs {defender}'s AC {defender_ac}.\n\n**Now: `!damage <roll>` (roll weapon damage)**"
        else:
            self.attack_beaten_ac = False
            self._advance_turn()
            return f"❌ **MISS!** {attacker} rolled {attack_roll} vs {defender}'s AC {defender_ac}.\n\n{self._end_turn_message()}"

    def resolve_damage(self, damage_roll):
        """
        Apply damage and advance to next turn.
        damage_roll: Total damage (e.g., 1d6+2 result)
        """
        if not self.in_combat:
            return "No combat in progress."
        
        if self.current_phase != self.PHASE_DAMAGE:
            return f"Error: Not in damage phase. Current phase: {self.current_phase}"

        if not self.attack_beaten_ac:
            return "Error: Can't roll damage, attack missed."

        attacker = self._get_current_combatant()
        defender = self._get_other_combatant()
        
        defender_obj = self.combatants[defender]
        remaining_hp = defender_obj.take_damage(damage_roll)

        msg = f"💥 {attacker} deals **{damage_roll} damage**!\n"
        msg += f"❤️ {defender} HP: **{defender_obj.hp} / {defender_obj.max_hp}**\n\n"

        if remaining_hp <= 0:
            self.current_phase = self.PHASE_COMBAT_END
            self.in_combat = False
            msg += f"🎭 **{defender} is defeated!**\n"
            msg += f"🏆 **{attacker} WINS!**"
            return msg

        self._advance_turn()
        msg += self._end_turn_message()
        return msg

    def _advance_turn(self):
        """Move to next combatant's turn"""
        self.current_turn_index += 1
        self.current_phase = self.PHASE_ATTACKER_ROLL
        self.current_attack_roll = None
        self.attack_beaten_ac = False

    def _end_turn_message(self):
        """Get message for end of turn"""
        next_attacker = self._get_current_combatant()
        defender = self._get_other_combatant()
        
        defender_stats = self.combatants[defender]
        return f"\n**{next_attacker}'s turn!**\nRoll to attack {defender} (AC {defender_stats.ac})"

    def get_combat_status(self):
        """Return current combat status"""
        if not self.in_combat and not self.combatants:
            return "No combat in progress."
        
        msg = "**COMBAT STATUS:**\n"
        for name, combatant in self.combatants.items():
            status = "🟢 Alive" if combatant.is_alive() else "💀 Dead"
            msg += f"{name}: {combatant.hp}/{combatant.max_hp} HP {status}\n"
        
        if self.in_combat:
            msg += f"\n**Current Phase:** {self.current_phase}\n"
            msg += f"**Current Turn:** {self._get_current_combatant()}\n"
        
        return msg

    def end_combat(self):
        """End combat and reset"""
        self.in_combat = False
        self.combatants = {}
        self.initiative_order = []
        self.current_turn_index = 0
        self.current_phase = self.PHASE_INITIATIVE
        return "Combat ended."
