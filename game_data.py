"""
Hardcoded valid character creation options for all game systems.
Extracted from official rulebooks to prevent AI hallucination.
Prevents characters from having fake Foci, Edges, Classes, or Wyrds.

LICENSING COMPLIANCE (Voluntary Tip Model):
============================================================
This file contains ONLY:
1. Tag/Option names (e.g., "Gunslinger", "Alert", "Hacker")
2. Game mechanic constants (e.g., "foci_count": 2)
3. System identifiers and classification data

NOT included:
- Verbatim rulebook descriptions or text
- Creative content from source materials
- Copyrighted game mechanics or rules prose

Tag names are explicitly allowed under Sine Nomine's commercial policy
for voluntary tip-based products. They are considered "non-creative" mechanical terms.

Character descriptions, narrative text, and scenario generation are 
created fresh by the AI model and do not reproduce rulebook content.

Rulebooks referenced:
- Worlds Without Number (by Kevin Crawford)
- Cities Without Number (by Kevin Crawford)
- Stars Without Number (by Kevin Crawford)
- Wolves of God (by Kevin Crawford)

Under Sine Nomine's policy: voluntary tips/donations do not constitute
commercial monetization, so all free product text can be used verbatim.
"""

import re

# ============================================================================
# WORLDS WITHOUT NUMBER (WWN)
# ============================================================================
WWN_CLASSES = ["Warrior", "Mage", "Expert", "Adventurer"]

WWN_FOCI = [
    "Alert", "Armored Magic", "Armsmaster", "Artisan", "Assassin", "Authority",
    "Close Combatant", "Connected", "Cultured", "Die Hard", "Deadeye",
    "Dealmaker", "Developed Attribute", "Diplomatic Grace", "Gifted Chirurgeon",
    "Henchkeeper", "Impervious Defense", "Impostor", "Lucky", "Nullifier",
    "Poisoner", "Polymath", "Rider", "Shocking Assault", "Sniper's Eye",
    "Specialist", "Spirit Familiar", "Trapmaster", "Unarmed Combatant",
    "Unique Gift", "Valiant Defender", "Well Met", "Whirlwind Assault",
    "Xenoblooded", "Dwarves", "Elves, Civilized", "Elves, Half-Elves",
    "Elves, Forest", "Halflings", "Gnomes", "Goblins, Tinker",
    "Goblins, Savage", "Lizardmen", "Orcs", "Origin Focus: Dwarf"
]

WWN_BACKGROUNDS = [
    "Artisan", "Barbarian", "Carter", "Courtesan", "Criminal", "Hunter",
    "Laborer", "Merchant", "Noble", "Nomad", "Peasant", "Performer",
    "Physician", "Priest", "Sailor", "Scholar", "Slave", "Soldier",
    "Thug", "Vanderer"
]

# ============================================================================
# CITIES WITHOUT NUMBER (CWN)
# ============================================================================
CWN_EDGES = [
    "Educated", "Face", "Focused", "Ghost", "Hacker", "Hard to Kill",
    "Killing Blow", "Masterful Expertise", "On Target", "Prodigy",
    "Operator's Fortune", "Veteran's Luck", "Voice of the People", "Wired"
]

CWN_FOCI = [
    "Ace Driver", "Alert", "All Natural", "Armsmaster", "Assassin", "Authority",
    "Close Combatant", "Cyberdoc", "Deadeye", "Diplomat", "Drone Pilot",
    "Expert Programmer", "Healer", "Henchkeeper", "Many Faces", "Pop Idol",
    "Roamer", "Safe Haven", "Shocking Assault", "Sniper's Eye", "Specialist",
    "Tinker", "Unarmed Combatant", "Unique Gift", "Unregistered",
    "Whirlwind Assault"
]

CWN_BACKGROUNDS = [
    "Academ", "Artist", "Assassin", "Criminal", "Drifter", "Enforcer",
    "Fixer", "Gutter-Blood", "Hacker", "High-Flier", "Investigator",
    "Laborer", "Military", "Muscle", "Outlier", "Professional",
    "Religious", "Scholar", "Street-Rat", "Technician", "Traveler", "Worker"
]

# ============================================================================
# STARS WITHOUT NUMBER (SWN)
# ============================================================================
SWN_CLASSES = ["Warrior", "Expert", "Psychic", "Adventurer"]

# All valid SWN skills
SWN_SKILLS = [
    "Administer", "Connect", "Exert", "Fix", "Heal", "Lead", "Notice", "Perform",
    "Pilot", "Program", "Punch", "Shoot", "Sneak", "Stab", "Survive", "Talk", "Trade", "Work"
]

# Psychic-only skills (restricted to Psychic class)
SWN_PSYCHIC_SKILLS = [
    "Biopsionics", "Metapsionics", "Precognition", "Telekinesis", "Telepathy", "Teleportation"
]

# Combat skills
SWN_COMBAT_SKILLS = ["Punch", "Shoot", "Stab"]

# Non-combat skills (everything except combat)
SWN_NONCOMBAT_SKILLS = [s for s in SWN_SKILLS if s not in SWN_COMBAT_SKILLS]

SWN_BACKGROUNDS = [
    "Barbarian", "Clergy", "Courtesan", "Criminal", "Dilettante", "Entertainer",
    "Merchant", "Noble", "Official", "Peasant", "Physician", "Pilot", "Politician",
    "Scholar", "Soldier", "Spacer", "Technician", "Thug", "Vagabond", "Worker"
]

SWN_FOCI = [
    "Alert", "Armsman", "Assassin", "Authority", "Close Combatant", "Connected",
    "Die Hard", "Diplomat", "Gunslinger", "Hacker", "Healer", "Henchkeeper",
    "Ironhide", "Psychic Training", "Savage Fray", "Shocking Assault", "Sniper",
    "Specialist", "Star Captain", "Starfarer", "Tinker", "Unarmed Combatant",
    "Unique Gift", "Wanderer", "Wild Psychic Talent", "Armored Technique",
    "Cross-Disciplinary Study", "Imprinted Spell", "Initiate of Healing",
    "Limited Study", "Petty Sorceries", "Psychic Synergy", "Savage Sorcery",
    "Vast Erudition", "War Caster"
]

# ============================================================================
# SWN CHARACTER CREATION - CLASS BENEFITS
# ============================================================================

SWN_CLASS_BENEFITS = {
    "Warrior": {
        "hp_formula": "1d6 + 2 + CON",
        "focus_type": "combat",
        "combat_ability": "Lucky: Once per session, negate a successful attack against you OR turn a missed attack into a hit",
        "attack_bonus": "+1",
        "class_skill": "Warrior gets +2 maximum HP at each character level"
    },
    "Expert": {
        "hp_formula": "1d6 + CON",
        "focus_type": "non-combat",
        "combat_ability": "Specialist: Once per session, reroll a failed skill check",
        "attack_bonus": "+0",
        "class_skill": "Gain bonus skill point to spend on non-combat skills"
    },
    "Psychic": {
        "hp_formula": "1d6 + CON",
        "focus_type": "none (choose 2 psychic skills instead)",
        "combat_ability": "Choose any 2 psychic skills as bonus skills",
        "attack_bonus": "+0",
        "class_skill": "Max Effort = 1 + highest psychic skill + best of (WIS or CON)"
    },
    "Adventurer": {
        "hp_formula": "Varies by Partial choices",
        "focus_type": "Varies (see Partial options)",
        "combat_ability": "Varies by choice of Partial Expert/Warrior/Psychic",
        "attack_bonus": "+0 (or +1 if Partial Warrior)",
        "class_skill": "See Partial options below"
    }
}

SWN_ADVENTURER_PARTIALS = {
    "Partial Expert": {
        "hp_formula": "1d6 + CON",
        "focus_type": "non-combat",
        "benefit": "Bonus skill point every level (non-combat/non-psychic)"
    },
    "Partial Warrior": {
        "hp_formula": "1d6 + 2 + CON",
        "focus_type": "combat",
        "benefit": "+1 attack bonus at levels 1 and 5; +2 max HP per level"
    },
    "Partial Psychic": {
        "hp_formula": "1d6 + CON",
        "focus_type": "none",
        "benefit": "Pick 1 psychic skill; can improve it but no other psychic skills allowed"
    }
}
# Standard Growth table (applies to all backgrounds)
SWN_GROWTH_TABLE = [
    "+1 Any Stat",
    "+2 Mental Stats",
    "+1 Physical Stat",
    "+2 Physical Stats",
    "Any Non-Combat Skill",
    "Any Combat Skill"
]

# Background definitions: Free skill + Learning table options
SWN_BACKGROUND_DATA = {
    "Barbarian": {
        "free_skill": "Survive",
        "learning": ["Any Combat", "Connect", "Exert", "Lead", "Notice", "Punch", "Sneak", "Survive"]
    },
    "Clergy": {
        "free_skill": "Talk",
        "learning": ["Administer", "Connect", "Know", "Lead", "Notice", "Perform", "Talk", "Heal"]
    },
    "Courtesan": {
        "free_skill": "Perform",
        "learning": ["Any Combat", "Connect", "Exert", "Notice", "Perform", "Survive", "Talk", "Trade"]
    },
    "Criminal": {
        "free_skill": "Sneak",
        "learning": ["Administer", "Any Combat", "Connect", "Notice", "Program", "Sneak", "Talk", "Trade"]
    },
    "Dilettante": {
        "free_skill": "Connect",
        "learning": ["Any Skill", "Any Skill", "Connect", "Know", "Perform", "Pilot", "Talk", "Trade"]
    },
    "Entertainer": {
        "free_skill": "Perform",
        "learning": ["Any Combat", "Connect", "Exert", "Notice", "Perform", "Perform", "Sneak", "Talk"]
    },
    "Merchant": {
        "free_skill": "Trade",
        "learning": ["Administer", "Connect", "Know", "Lead", "Notice", "Pilot", "Talk", "Trade"]
    },
    "Noble": {
        "free_skill": "Lead",
        "learning": ["Administer", "Connect", "Know", "Lead", "Notice", "Perform", "Talk", "Any Skill"]
    },
    "Official": {
        "free_skill": "Administer",
        "learning": ["Any Combat", "Administer", "Connect", "Know", "Lead", "Notice", "Talk", "Any Skill"]
    },
    "Peasant": {
        "free_skill": "Work",
        "learning": ["Any Combat", "Connect", "Exert", "Fix", "Know", "Notice", "Survive", "Work"]
    },
    "Physician": {
        "free_skill": "Heal",
        "learning": ["Administer", "Connect", "Know", "Heal", "Heal", "Notice", "Perform", "Talk"]
    },
    "Pilot": {
        "free_skill": "Pilot",
        "learning": ["Any Combat", "Exert", "Fix", "Notice", "Perform", "Pilot", "Pilot", "Program"]
    },
    "Politician": {
        "free_skill": "Lead",
        "learning": ["Administer", "Connect", "Know", "Lead", "Notice", "Perform", "Talk", "Trade"]
    },
    "Scholar": {
        "free_skill": "Know",
        "learning": ["Administer", "Know", "Know", "Stab", "Shoot", "Any Non-Combat", "Any Combat", "Connect"]
    },
    "Soldier": {
        "free_skill": "Shoot",
        "learning": ["Administer", "Any Combat", "Connect", "Exert", "Fix", "Lead", "Notice", "Survive"]
    },
    "Spacer": {
        "free_skill": "Pilot",
        "learning": ["Any Combat", "Connect", "Exert", "Fix", "Notice", "Pilot", "Shoot", "Survive"]
    },
    "Technician": {
        "free_skill": "Fix",
        "learning": ["Any Combat", "Administer", "Connect", "Fix", "Know", "Program", "Sneak", "Stab"]
    },
    "Thug": {
        "free_skill": "Punch",
        "learning": ["Any Combat", "Connect", "Exert", "Intimidate", "Notice", "Punch", "Sneak", "Survive"]
    },
    "Vagabond": {
        "free_skill": "Survive",
        "learning": ["Any Combat", "Connect", "Exert", "Notice", "Perform", "Sneak", "Survive", "Talk"]
    },
    "Worker": {
        "free_skill": "Work",
        "learning": ["Connect", "Exert", "Fix", "Know", "Notice", "Program", "Survive", "Work"]
    }
}

# ============================================================================
# WOLVES OF GOD (WOG)
# ============================================================================
WOG_CLASSES = ["Godvernor", "Saint", "Warrior", "Adventurer"]

WOG_WYRDS_NOBLE = [
    "An angel guards me from above.",
    "False words do not deceive me.",
    "I am a scourge to Hell's sons.",
    "God loves my piety.",
    "Hearts are lifted by my words.",
    "I am a bane of monsters.",
    "Men follow my lead.",
    "Relentless in battle.",
    "Skillful in Speech."
]

WOG_WYRDS_IGNOBLE = [
    "Anger blinds me to good sense.",
    "I abandon my own.",
    "I aid strangers before my own people.",
    "I am a coward at moments of peril.",
    "I pray to the old pagan gods.",
    "I seduce the women of other men.",
    "Quick to Anger."
]

WOG_WYRDS = WOG_WYRDS_NOBLE + WOG_WYRDS_IGNOBLE

WOG_SKILLS = [
    "Administer", "Build", "Connect", "Craft", "Exert", "Fix", "Heal",
    "Know", "Lead", "Notice", "Perform", "Pilot", "Pray", "Punch",
    "Shoot", "Sneak", "Stab", "Survive", "Talk", "Trade", "Work"
]

# ============================================================================
# SYSTEM SPECS FOR CHARACTER GENERATION
# ============================================================================
SYSTEM_SPECS = {
    "wwn": {
        "name": "Worlds Without Number",
        "classes": WWN_CLASSES,
        "backgrounds": WWN_BACKGROUNDS,
        "foci": WWN_FOCI,
        "foci_count": 2,
    },
    "cwn": {
        "name": "Cities Without Number",
        "classes": ["Operator"],
        "backgrounds": CWN_BACKGROUNDS,
        "edges": CWN_EDGES,
        "foci": CWN_FOCI,
        "edges_count": 2,
        "foci_count": 1,
    },
    "swn": {
        "name": "Stars Without Number",
        "classes": SWN_CLASSES,
        "backgrounds": SWN_BACKGROUNDS,
        "foci": SWN_FOCI,
        "foci_count": 1,
    },
    "wog": {
        "name": "Wolves of God",
        "classes": WOG_CLASSES,
        "wyrds": WOG_WYRDS,
        "wyrds_count": 3,  # 2 Noble, 1 Ignoble
        "skills": WOG_SKILLS,
    }
}

# VALIDATION FUNCTIONS

def find_closest_focus(text, valid_foci=None):
    """
    Attempts to match a Foci name in text to a valid Foci from the rulebook.
    Returns the valid Foci name if found, or None if not.
    Case-insensitive matching with fuzzy tolerance.
    """
    if valid_foci is None:
        valid_foci = WWN_FOCI
    
    text_lower = text.lower().strip()
    
    # Exact match first
    for focus in valid_foci:
        if focus.lower() == text_lower:
            return focus
    
    # Partial/fuzzy match (if AI writes "Unarmed Combat" instead of "Unarmed Combatant")
    for focus in valid_foci:
        if focus.lower() in text_lower or text_lower in focus.lower():
            # Only accept if it's a strong partial match
            words = text_lower.split()
            focus_words = focus.lower().split()
            overlap = sum(1 for w in words if w in focus.lower())
            if overlap >= len(focus_words) - 1:  # Allow 1 word mismatch
                return focus
    
    return None

def validate_foci_list(character_sheet, system="wwn"):
    """
    Extracts Foci from a character sheet and returns:
    (valid_foci, invalid_foci, original_text)
    
    This helps identify if AI hallucinated invalid Foci.
    """
    valid_foci = SYSTEM_SPECS[system].get("foci", [])
    
    # Look for common patterns in character sheet
    # Pattern: "Focus: Name", "Focus 1: Name", "Foci: Name1, Name2"
    foci_pattern = r'(?:Focus|Foci)[^:]*:\s*([^.\n]+)'
    matches = re.findall(foci_pattern, character_sheet, re.IGNORECASE)
    
    found_foci = []
    invalid_foci = []
    
    for match in matches:
        # Split on commas for multiple foci
        individual_foci = [f.strip() for f in match.split(',')]
        for foci_name in individual_foci:
            closest = find_closest_focus(foci_name, valid_foci)
            if closest:
                found_foci.append(closest)
            else:
                invalid_foci.append(foci_name)
    
    return found_foci, invalid_foci, matches

def create_foci_validation_prompt(system="wwn"):
    """
    Returns a strict validation prompt to include in character generation.
    Forces AI to use ONLY valid Foci.
    """
    valid_foci = SYSTEM_SPECS[system].get("foci", [])
    foci_list = ", ".join(valid_foci)
    
    return (
        f"\n\n[VALID FOCI FOR {system.upper()}]\n"
        f"You MUST choose Foci ONLY from this list:\n"
        f"{foci_list}\n"
        f"DO NOT use any Foci names not on this list.\n"
        f"If you cannot find a good match from this list, use 'Unique Gift' as a catch-all.\n"
        f"FORBIDDEN: Do NOT invent Foci like 'Deceptive', 'Hacking', 'Connected', 'Intrusion', 'Slick', 'Fearsome'.\n"
    )

def get_swn_background_info(background):
    """
    Returns background info: free skill + learning table.
    """
    if background not in SWN_BACKGROUND_DATA:
        return None
    return SWN_BACKGROUND_DATA[background]

def create_swn_character_sequence_prompt(player_concept=""):
    """
    Generates a complete, step-by-step SWN character creation prompt following the official sequence.
    """
    
    prompt = f"""
STARS WITHOUT NUMBER CHARACTER CREATION - OFFICIAL SEQUENCE

This prompt will guide you through creating a proper SWN level 1 character.
Follow these steps IN ORDER:

{'='*80}
STEP 1: ROLL OR ASSIGN ATTRIBUTES
{'='*80}
Roll 3d6 six times, assigning results in order to: STR, DEX, CON, INT, WIS, CHA
OR assign this array in any order: 14, 12, 11, 10, 9, 7

You may replace ONE roll with 14 if desired.

Calculate modifiers:
3 = -2 | 4-7 = -1 | 8-13 = +0 | 14-17 = +1 | 18 = +2

Record all 6 attributes with their modifiers.

{'='*80}
STEP 2: CHOOSE YOUR CLASS
{'='*80}
Pick ONE:
- WARRIOR: Combat expert with luck ability (1d6+2+CON HP)
- EXPERT: Specialist with reroll ability (1d6+CON HP)
- PSYCHIC: Master of psychic powers (1d6+CON HP, choose 2 psychic skills)
- ADVENTURER: Choose one or more Partials:
  * Partial Expert: non-combat Focus + skill points (1d6+CON HP)
  * Partial Warrior: combat Focus + attack bonus (1d6+2+CON HP)
  * Partial Psychic: 1 psychic skill only (1d6+CON HP)

{'='*80}
STEP 3: CHOOSE YOUR BACKGROUND
{'='*80}
Pick ONE from these 20 backgrounds:
Barbarian, Clergy, Courtesan, Criminal, Dilettante, Entertainer,
Merchant, Noble, Official, Peasant, Physician, Pilot, Politician,
Scholar, Soldier, Spacer, Technician, Thug, Vagabond, Worker

Your background gives you:
- FREE SKILL: You automatically get this skill at level 0
- LEARNING TABLE: 8 skill options you can choose from

{'='*80}
STEP 4: ACQUIRE SKILLS (3 TOTAL)
{'='*80}
You start with:
1. FREE SKILL from your background (level 0) - AUTOMATIC

2-3. CHOOSE 2 MORE SKILLS using ONE method:

METHOD A - PICK DIRECTLY (pick 2 from background's Learning table):
Choose exactly which 2 skills you want. You may pick the same
skill twice to raise it from level 0 to level 1.

METHOD B - ROLL 3 TIMES (distribute between Growth and Learning):
Roll 3d6 and allocate rolls to either:
- GROWTH TABLE: +1 Stat, +2 Mental, +1 Physical, +2 Physical, or Any Skill
- LEARNING TABLE: Skill from background's learning options

You can split 3 rolls as: 3 Growth, 2G+1L, 1G+2L, or 3 Learning.

IMPORTANT: All skills must come from SWN's official list:
Administer, Connect, Exert, Fix, Heal, Lead, Notice, Perform, Pilot, 
Program, Punch, Shoot, Sneak, Stab, Survive, Talk, Trade, Work

(Psychic skills are Biopsionics, Metapsionics, Precognition, Telekinesis, 
Telepathy, Teleportation - available only to Psychics)

{'='*80}
STEP 5: CHOOSE FOCUS(ES)
{'='*80}
Pick based on your CLASS:

WARRIOR: 1 combat-related Focus (from background list)
EXPERT: 1 non-combat Focus (from background list)
PSYCHIC: Skip this - you chose 2 psychic skills in Step 2
ADVENTURER: 
  - Partial Expert: 1 non-combat Focus
  - Partial Warrior: 1 combat Focus
  - Partial Psychic: No Focus

VALID SWN FOCI (pick ONE unless you're pure Psychic):
Alert, Ironsman, Assassin, Authority, Close Combatant, Connected, Diehard,
Diplomat, Gunslinger, Hacker, Healer, Pinch Keeper, Ironhide, Psychic Training,
Saboteur, Shocking Assault, Sniper, Specialist, Star Captain, Starfarer, Tinker,
Unarmed Combat, Yin Gift, Wanderer, Wild Psychic Talent

{'='*80}
STEP 6: CALCULATE DERIVED STATS
{'='*80}

HIT POINTS (based on class):
- Warrior: 1d6 + 2 + CON modifier (minimum 1)
- Expert: 1d6 + CON modifier (minimum 1)
- Psychic: 1d6 + CON modifier (minimum 1)
- Adventurer: See your Partial options above

ARMOR CLASS:
- Base: 10 (no armor)
- Add DEX modifier
- Add armor bonus if wearing armor

ATTACK BONUS:
- Warrior: +1
- Expert: +0
- Psychic: +0
- Adventurer: +0 (or +1 if Partial Warrior)

SAVING THROWS (all start at 15):
- Physical: 15 - level - [best of STR or CON modifier]
- Evasion: 15 - level - [best of DEX or INT modifier]
- Mental: 15 - level - [best of WIS or CHA modifier]

PSYCHIC EFFORT (if Psychic class):
- Maximum = 1 + highest psychic skill level + [best of WIS or CON modifier]

{'='*80}
STEP 7: SELECT EQUIPMENT
{'='*80}
Choose an equipment package appropriate for your background and class,
OR roll 2d6 x 100 for starting credits to buy equipment.

{'='*80}
STEP 8: NAME YOUR CHARACTER
{'='*80}
Choose a name and give a brief description of who they are.

{'='*80}
FINAL CHARACTER SHEET FORMAT
{'='*80}

NAME: [character name]
LEVEL: 1
CLASS: [Warrior/Expert/Psychic/Adventurer + Partials if applicable]
BACKGROUND: [background name]

ATTRIBUTES (score / modifier):
STR: [score] / [mod]
DEX: [score] / [mod]
CON: [score] / [mod]
INT: [score] / [mod]
WIS: [score] / [mod]
CHA: [score] / [mod]

SKILLS: [list 3 acquired skills with levels]
- [Skill]-0
- [Skill]-0 (or -1 if picked twice)
- [Skill]-0 (or -1 if picked twice)

FOCUS: [1 Focus name OR 2 Psychic skills if Psychic]

HIT POINTS: [rolled HP] / [rolled HP]
ARMOR CLASS: [AC]
ATTACK BONUS: [bonus]

SAVING THROWS:
Physical: [15 - level - modifier]
Evasion: [15 - level - modifier]
Mental: [15 - level - modifier]

CLASS ABILITY: [describe once per session ability]

EQUIPMENT: [list starting equipment]

DESCRIPTION: [brief character description]

{'='*80}
CRITICAL RULES
{'='*80}
1. Do NOT make up skills - all 3 skills must come from the official SWN skill list
2. Do NOT make up Focus names - must choose from the 25 valid Foci (or psychic skills if Psychic)
3. Do NOT forget HP, AC, Saving Throws
4. Do NOT auto-assign skills based on background alone - player must choose which 2 extras
5. Do NOT include made-up abilities or stats
6. Combat skills are: Punch, Shoot, Stab
7. Non-combat skills are: all others

{'='*80}
END OF CHARACTER CREATION SEQUENCE
{'='*80}

Now create a complete, properly-formatted SWN level 1 character following this sequence.
Player concept: {player_concept if player_concept else 'Any concept'}
"""
    
    return prompt

def create_swn_character_background_prompt(background):
    """
    Formats a prompt for SWN character creation based on selected background.
    Includes the free skill, learning options, and character creation rules.
    """
    bg_data = get_swn_background_info(background)
    if not bg_data:
        return f"Unknown background: {background}"
    
    free_skill = bg_data["free_skill"]
    learning_options = ", ".join(bg_data["learning"])
    combat_skills = ", ".join(SWN_COMBAT_SKILLS)
    noncombat_skills = ", ".join(SWN_NONCOMBAT_SKILLS)
    
    prompt = f"""
CHARACTER CREATION RULES FOR STARS WITHOUT NUMBER:

BACKGROUND: {background}
FREE SKILL: {free_skill} (level 0 - automatic)

SKILL SELECTION:
You now choose 2 more skills using ONE of these methods:

METHOD A - PICK 2 SKILLS:
Choose any 2 skills from this background's Learning table:
{learning_options}

METHOD B - ROLL 3 TIMES:
Roll 3 times and distribute between Growth and Learning tables.
You can do: 3 Growth, 2 Growth+1 Learning, 1 Growth+2 Learning, or 3 Learning.

GROWTH TABLE OPTIONS (roll or pick one):
1. +1 to any Stat (STR, DEX, CON, INT, WIS, or CHA)
2. +2 to Mental Stats (INT, WIS, CHA - pick which 2)
3. +1 to Physical Stat (STR, DEX, or CON)
4. +2 to Physical Stats (STR, DEX, or CON - pick which 2)
5. Any non-combat skill
6. Any combat skill (Stab, Shoot, or Punch)

LEARNING TABLE OPTIONS (profession-specific skills for {background}):
{', '.join([f"{i+1}. {skill}" for i, skill in enumerate(bg_data['learning'])])}

REQUIRED CHARACTER SHEET FORMAT:
Name: [character name]
Level: 1
Class: [Warrior/Expert/Psychic/Adventurer]
Background: {background}

ATTRIBUTES (with modifiers):
Strength: [score] ([modifier])
Dexterity: [score] ([modifier])
Constitution: [score] ([modifier])
Intelligence: [score] ([modifier])
Wisdom: [score] ([modifier])
Charisma: [score] ([modifier])

SKILLS (list acquired skills only):
- {free_skill}-0 (from background)
- [Additional 2 skills from METHOD A or METHOD B, with their levels]
Valid skills ONLY: {', '.join(SWN_SKILLS)}

HIT POINTS AND COMBAT:
- HP: For Warriors: (1d6 + CON modifier) × Level = total HP
  For Experts: (1d4 + CON modifier) × Level = total HP  
  For Psychics: (1d4 + CON modifier) × Level = total HP
  For Adventurers: (1d6 + CON modifier) × Level = total HP
- Armor Class: 10 + DEX modifier (no armor) OR armor value + DEX modifier if wearing armor
- Attack Bonus: +0 for most classes, +1 for Warriors

FOCUS: MUST CHOOSE 1 VALID SWN FOCUS:
Alert, Ironsman, Assassin, Authority, Close Combatant, Connected, Diehard, Diplomat, Gunslinger, Hacker, Healer, Pinch Keeper, Ironhide, Psychic Training, Saboteur, Shocking Assault, Sniper, Specialist, Star Captain, Starfarer, Tinker, Unarmed Combat, Yin Gift, Wanderer, Wild Psychic Talent

EQUIPMENT: Appropriate for background and class

SAVING THROWS (all at 15 - level - best modifier):
- Physical: 15 - [Strength or Constitution modifier]
- Evasion: 15 - [Dexterity or Intelligence modifier]  
- Mental: 15 - [Wisdom or Charisma modifier]

CRITICAL RULES:
1. Do NOT make up skills - use ONLY: {', '.join(SWN_SKILLS)}
2. Combat skills are: {combat_skills}
3. Non-combat skills are: {noncombat_skills}
4. Do NOT include "Combat/[Type]" or other made-up skill names
5. Do NOT use Psychic skills (Biopsionics, Telepathy, etc.) unless character is Psychic class
6. Do NOT forget HP, AC, Saving Throws
7. Do NOT forget to assign 1 Focus
8. Do NOT invent Focus names

OUTPUT: Create a complete, properly formatted SWN level 1 character sheet.
"""
    return prompt


# ============================================================================
# SWN CHARACTER VALIDATION & AUTO-CORRECTION
# ============================================================================

import random

def find_closest_valid(value, valid_list):
    """
    Find closest match in valid list, or pick random if no match.
    """
    if not value:
        return random.choice(valid_list)
    
    value_lower = value.lower().strip()
    
    # Exact match
    for item in valid_list:
        if item.lower() == value_lower:
            return item
    
    # Partial match
    for item in valid_list:
        if value_lower in item.lower() or item.lower() in value_lower:
            return item
    
    # No match - return random
    return random.choice(valid_list)

def calculate_hp(class_name, con_modifier):
    """
    Calculate HP based on class and CON modifier for level 1.
    """
    if class_name == "Warrior":
        return max(1, random.randint(1, 6) + 2 + con_modifier)
    elif class_name == "Expert":
        return max(1, random.randint(1, 6) + con_modifier)
    elif class_name == "Psychic":
        return max(1, random.randint(1, 6) + con_modifier)
    elif class_name == "Adventurer":
        return max(1, random.randint(1, 6) + con_modifier)
    else:
        return max(1, random.randint(1, 6) + con_modifier)

def calculate_ac(dex_modifier, armor_bonus=0):
    """
    Calculate AC: 10 + DEX + armor
    """
    return 10 + dex_modifier + armor_bonus

def calculate_save(save_type, level, modifier):
    """
    Calculate saving throw: 15 - level - modifier
    """
    return max(3, 15 - level - modifier)

def validate_swn_character(character_data, auto_fix=True):
    """
    Validates and auto-corrects a SWN character sheet.
    
    Args:
        character_data: dict or text with character info
        auto_fix: if True, fixes invalid options; if False, just reports issues
    
    Returns:
        Tuple: (cleaned_character_dict, issues_found_list)
    """
    issues = []
    char = {}
    
    # Extract basic info
    char['name'] = character_data.get('name', 'Unknown') if isinstance(character_data, dict) else 'Unknown'
    char['level'] = 1
    
    # Validate Class
    raw_class = character_data.get('class', '').strip() if isinstance(character_data, dict) else ''
    if raw_class not in SWN_CLASSES:
        issues.append(f"Invalid class '{raw_class}'")
        if auto_fix:
            char['class'] = random.choice(SWN_CLASSES)
            issues.append(f"  → Fixed to: {char['class']}")
        else:
            char['class'] = raw_class
    else:
        char['class'] = raw_class
    
    # Validate Background
    raw_background = character_data.get('background', '').strip() if isinstance(character_data, dict) else ''
    if raw_background not in SWN_BACKGROUNDS:
        issues.append(f"Invalid background '{raw_background}'")
        if auto_fix:
            char['background'] = random.choice(SWN_BACKGROUNDS)
            issues.append(f"  → Fixed to: {char['background']}")
        else:
            char['background'] = raw_background
    else:
        char['background'] = raw_background
    
    # Get background info for free skill
    bg_info = get_swn_background_info(char['background'])
    char['free_skill'] = bg_info['free_skill'] if bg_info else 'Survive'
    
    # Validate Skills
    raw_skills = character_data.get('skills', []) if isinstance(character_data, dict) else []
    char['skills'] = []
    for skill in raw_skills:
        if skill not in SWN_SKILLS and skill not in SWN_PSYCHIC_SKILLS:
            issues.append(f"Invalid skill '{skill}'")
            if auto_fix:
                valid_skill = random.choice(SWN_SKILLS)
                char['skills'].append(valid_skill)
                issues.append(f"  → Replaced with: {valid_skill}")
            else:
                char['skills'].append(skill)
        else:
            char['skills'].append(skill)
    
    # Validate Focus
    raw_focus = character_data.get('focus', '').strip() if isinstance(character_data, dict) else ''
    if raw_focus not in SWN_FOCI:
        issues.append(f"Invalid focus '{raw_focus}'")
        if auto_fix:
            char['focus'] = random.choice(SWN_FOCI)
            issues.append(f"  → Fixed to: {char['focus']}")
        else:
            char['focus'] = raw_focus
    else:
        char['focus'] = raw_focus
    
    # Validate/Calculate Attributes
    attributes = character_data.get('attributes', {}) if isinstance(character_data, dict) else {}
    char['attributes'] = {}
    attr_mods = {}
    
    for attr_name in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
        attr_val = attributes.get(attr_name, random.randint(3, 18))
        if attr_val < 3 or attr_val > 18:
            issues.append(f"{attr_name} out of range: {attr_val}")
            if auto_fix:
                attr_val = random.randint(8, 16)
        
        # Calculate modifier
        if attr_val in range(3, 4):
            mod = -2
        elif attr_val in range(4, 8):
            mod = -1
        elif attr_val in range(8, 14):
            mod = 0
        elif attr_val in range(14, 18):
            mod = 1
        else:  # 18
            mod = 2
        
        char['attributes'][attr_name] = attr_val
        attr_mods[attr_name] = mod
    
    char['attr_mods'] = attr_mods
    
    # Calculate derived stats
    con_mod = attr_mods['constitution']
    dex_mod = attr_mods['dexterity']
    str_mod = attr_mods['strength']
    int_mod = attr_mods['intelligence']
    wis_mod = attr_mods['wisdom']
    cha_mod = attr_mods['charisma']
    
    # HP
    char['hp'] = calculate_hp(char['class'], con_mod)
    
    # AC
    armor_bonus = character_data.get('armor_bonus', 0) if isinstance(character_data, dict) else 0
    char['ac'] = calculate_ac(dex_mod, armor_bonus)
    
    # Attack Bonus
    if char['class'] == 'Warrior':
        char['attack_bonus'] = 1
    else:
        char['attack_bonus'] = 0
    
    # Saving Throws
    char['saves'] = {
        'physical': calculate_save('physical', 1, max(str_mod, con_mod)),
        'evasion': calculate_save('evasion', 1, max(dex_mod, int_mod)),
        'mental': calculate_save('mental', 1, max(wis_mod, cha_mod))
    }
    
    return char, issues


def format_swn_character_sheet(char_dict):
    """
    Formats a validated character dict into a nice character sheet string.
    """
    sheet = f"""
{'='*70}
STARS WITHOUT NUMBER - CHARACTER SHEET
{'='*70}

NAME: {char_dict['name']} | LEVEL: {char_dict['level']}
CLASS: {char_dict['class']} | BACKGROUND: {char_dict['background']}

{'─'*70}
ATTRIBUTES (Score / Modifier)
{'─'*70}
Strength:     {char_dict['attributes']['strength']:2d} / {char_dict['attr_mods']['strength']:+2d}
Dexterity:    {char_dict['attributes']['dexterity']:2d} / {char_dict['attr_mods']['dexterity']:+2d}
Constitution: {char_dict['attributes']['constitution']:2d} / {char_dict['attr_mods']['constitution']:+2d}
Intelligence: {char_dict['attributes']['intelligence']:2d} / {char_dict['attr_mods']['intelligence']:+2d}
Wisdom:       {char_dict['attributes']['wisdom']:2d} / {char_dict['attr_mods']['wisdom']:+2d}
Charisma:     {char_dict['attributes']['charisma']:2d} / {char_dict['attr_mods']['charisma']:+2d}

{'─'*70}
COMBAT STATS
{'─'*70}
Hit Points:   {char_dict['hp']}
Armor Class:  {char_dict['ac']}
Attack Bonus: {char_dict['attack_bonus']:+d}

{'─'*70}
SKILLS ({char_dict['free_skill']}-0 from background)
{'─'*70}
{', '.join(char_dict['skills'])}

FOCUS: {char_dict['focus']}

{'─'*70}
SAVING THROWS
{'─'*70}
Physical (STR/CON): {char_dict['saves']['physical']}+
Evasion (DEX/INT):  {char_dict['saves']['evasion']}+
Mental (WIS/CHA):   {char_dict['saves']['mental']}+

{'='*70}
"""
    return sheet


def create_portrait_prompt(char_dict):
    """
    Creates a vivid portrait description prompt from character data.
    Used to generate AI artwork of the character.
    """
    class_name = char_dict.get('class', 'Adventurer')
    background = char_dict.get('background', 'Unknown')
    focus = ', '.join(char_dict.get('focus', ['Unknown']))  # Format focus as a readable string
    name = char_dict.get('name', 'Stranger')
    
    # Build personality from attributes
    str_mod = char_dict['attr_mods']['strength']
    dex_mod = char_dict['attr_mods']['dexterity']
    con_mod = char_dict['attr_mods']['constitution']
    int_mod = char_dict['attr_mods']['intelligence']
    wis_mod = char_dict['attr_mods']['wisdom']
    cha_mod = char_dict['attr_mods']['charisma']
    
    # Describe physical appearance based on attributes
    build = "muscular and imposing" if str_mod > 0 else ("lean and nimble" if dex_mod > 0 else "sturdy")
    demeanor = "intelligent and sharp-eyed" if int_mod > 0 else ("confident and charismatic" if cha_mod > 0 else "weathered and battle-worn")
    
    # Class-based description
    class_desc = {
        'Warrior': 'combat-hardened, with scars and battle-worn gear',
        'Expert': 'skilled and professional, carrying tools of their trade',
        'Psychic': 'mysterious and intense, with an otherworldly presence',
        'Adventurer': 'adaptable, bearing signs of their varied background'
    }
    
    # Build the prompt
    prompt = f"""
A portrait of {name}, a {class_name.lower()} with a {background.lower()} background.

Physical:
- {build}
- {demeanor}
- {class_desc.get(class_name, 'capable and determined')}

Class & Focus:
- **{class_name}** specializing in {focus}
- Carries equipment fitting a {background.lower()}'s profession

Setting: Against a sci-fi background, showing their character and experience. 
Style: Cinematic character portrait, detailed and atmospheric, digital art.
    """
    return prompt.strip()
