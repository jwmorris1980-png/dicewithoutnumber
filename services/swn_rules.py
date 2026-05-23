import random

# Stars Without Number Rules

SWN_SKILLS = [
    "Administer", "Connect", "Exert", "Fix", "Heal", "Know", "Lead", "Notice",
    "Perform", "Pilot", "Program", "Punch", "Shoot", "Sneak", "Stab", "Survive",
    "Talk", "Trade", "Work"
]

SWN_BACKGROUNDS = {
    "Barbarian": {"skills": ["Exert", "Survive"], "description": "You come from a primitive world or a desolate frontier, where survival is a daily struggle."},
    "Clergy": {"skills": ["Connect", "Talk"], "description": "You were a member of a religious order, a spiritual guide, or a cultist."},
    "Courtesan": {"skills": ["Connect", "Perform"], "description": "You were a professional companion, an entertainer, or a spy who used social graces to survive."},
    "Criminal": {"skills": ["Connect", "Sneak"], "description": "You have a past as a thief, a gangster, or a con artist."},
    "Dilettante": {"skills": ["Connect", "Trade"], "description": "You were born into wealth and privilege, and you've dabbled in many fields."},
    "Entertainer": {"skills": ["Perform", "Talk"], "description": "You were a musician, an actor, or another kind of performer."},
    "Explorer": {"skills": ["Pilot", "Survive"], "description": "You have a passion for discovering new places, whether new worlds or forgotten ruins."},
    "Merchant": {"skills": ["Trade", "Talk"], "description": "You are a trader, a shopkeeper, or a smuggler who knows how to make a deal."},
    "Noble": {"skills": ["Lead", "Connect"], "description": "You are from a noble family, with a background of power and influence."},
    "Official": {"skills": ["Administer", "Connect"], "description": "You were a bureaucrat, a corporate functionary, or a government agent."},
    "Peasant": {"skills": ["Exert", "Work"], "description": "You come from a humble background, a farmer, a laborer, or a serf."},
    "Physician": {"skills": ["Heal", "Know"], "description": "You are a doctor, a medic, or a scientist specializing in biology."},
    "Pilot": {"skills": ["Pilot", "Fix"], "description": "You are a skilled starship pilot, a racer, or a freighter captain."},
    "Politician": {"skills": ["Lead", "Talk"], "description": "You were a political leader, a diplomat, or a revolutionary."},
    "Scholar": {"skills": ["Know", "Administer"], "description": "You are an academic, a researcher, or a librarian."},
    "Soldier": {"skills": ["Shoot", "Exert"], "description": "You were a professional soldier, a mercenary, or a militia member."},
    "Spacer": {"skills": ["Pilot", "Fix"], "description": "You grew up on a starship or a space station."},
    "Technician": {"skills": ["Fix", "Know"], "description": "You are an engineer, a mechanic, or a computer specialist."},
    "Thug": {"skills": ["Punch", "Exert"], "description": "You are a brawler, an enforcer, or a bodyguard."},
    "Vagabond": {"skills": ["Sneak", "Survive"], "description": "You have lived on the streets, a wanderer with no home."}
}

SWN_FOCI = {
    "Alert": "You can't be surprised. You can choose to go first in the first round of combat.",
    "Armsman": "You are proficient with melee weapons. You can add your Stab or Punch skill to your damage roll.",
    "Assassin": "When you successfully ambush a target, you do an extra 1d6 damage.",
    "Authority": "You have a natural air of command. You can use your Lead skill in place of your Talk skill to persuade.",
    "Connected": "You have a wide network of contacts. Once per session, you can find a contact in a new location.",
    "Die Hard": "You are tough to kill. You can get up with 1 HP the first time you are reduced to 0 HP.",
    "Gunslinger": "You are an expert with ranged weapons. You can add your Shoot skill to your damage roll.",
    "Hacker": "You are a skilled computer programmer. You can use your Program skill to bypass security systems.",
    "Healer": "You are a skilled medic. You can use your Heal skill to stabilize a dying character without a medkit.",
    "Henchkeeper": "You have a loyal follower. You can recruit a henchman who will work for you.",
    "Ironhide": "You have a naturally tough hide. You have a natural Armor Class of 2.",
    "Psychic": "You have psychic abilities. Choose one psychic discipline.",
    "Scrounger": "You are good at finding things. Once per session, you can find a useful piece of equipment.",
    "Sneak": "You are good at moving unseen. You can use your Sneak skill to become invisible for a short time.",
    "Starfarer": "You are an expert pilot. You can use your Pilot skill to perform difficult maneuvers with a starship.",
    "Tinker": "You are good at fixing things. You can use your Fix skill to repair a broken piece of equipment without tools."
}

def get_swn_rules():
    return "Stars Without Number rules loaded."

def roll_initiative():
    """Rolls initiative for SWN."""
    return random.randint(1, 8)

def roll_4d6_drop_lowest():
    rolls = [random.randint(1, 6) for _ in range(4)]
    return sum(sorted(rolls)[1:])

def create_swn_character(player_name, class_choice=None):
    """Creates a new SWN character."""
    
    attributes = {
        "strength": roll_4d6_drop_lowest(),
        "dexterity": roll_4d6_drop_lowest(),
        "constitution": roll_4d6_drop_lowest(),
        "intelligence": roll_4d6_drop_lowest(),
        "wisdom": roll_4d6_drop_lowest(),
        "charisma": roll_4d6_drop_lowest(),
    }

    background_name = random.choice(list(SWN_BACKGROUNDS.keys()))
    background_info = SWN_BACKGROUNDS[background_name]
    
    skills = {skill: 0 for skill in SWN_SKILLS}
    for skill in background_info["skills"]:
        skills[skill] = 1

    focus_name = random.choice(list(SWN_FOCI.keys()))
    
    hp = random.randint(1, 6) + max(0, (attributes["constitution"] - 10) // 2)
    ac = 10 + max(0, (attributes["dexterity"] - 10) // 2)

    character = {
        "name": player_name,
        "class": class_choice or "Adventurer",
        "level": 1,
        "attributes": attributes,
        "background": background_name,
        "skills": skills,
        "focus": focus_name,
        "hp": max(hp, 1),
        "ac": ac,
        "equipment": {
            "armor": "Lined Vacsuit (AC 3)",
            "weapons": ["Combat Knife", "Laser Pistol"],
            "gear": ["Survival Kit", "Backpack", "Compad"],
            "credits": random.randint(50, 100),
        },
    }
    
    return character, attributes
