import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os

class CharGenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # SWN Revised Data
        self.swn_classes = {
            "Warrior": {"hp_die": 6, "hp_bonus": 2, "description": "Fighters and soldiers. +1 attack bonus every level."},
            "Expert": {"hp_die": 6, "hp_bonus": 0, "description": "Specialists and professionals. Gain an extra skill point per level."},
            "Psychic": {"hp_die": 4, "hp_bonus": 0, "description": "Psionic talent. Choose two psychic disciplines."},
            "Adventurer": {"hp_die": 6, "hp_bonus": 0, "description": "A mix of classes. Choose two partial classes."}
        }
        self.swn_backgrounds = ["Barbarian", "Clergy", "Courtesan", "Criminal", "Dilettante", "Entertainer", "Merchant", "Noble", "Official", "Peasant", "Physician", "Pilot", "Politician", "Scholar", "Soldier", "Spacer", "Technician", "Thug", "Vagabond", "Worker"]
        self.swn_skills = ["Administer", "Connect", "Exert", "Fix", "Heal", "Know", "Lead", "Notice", "Perform", "Pilot", "Program", "Punch", "Shoot", "Sneak", "Stab", "Survive", "Talk", "Trade", "Work"]
        self.swn_weapons = ["Laser Pistol", "Mag Rifle", "Combat Shotgun", "Monoblade", "Stun Baton"]
        self.swn_armor = ["Armored Undersuit", "Woven Body Armor", "Combat Field Uniform", "None"]

        # WWN Data
        self.wwn_classes = {
            "Warrior": {"hp_die": 6, "hp_bonus": 2, "description": "Masters of arms. +1 attack bonus every level, and the Veteran's Luck ability to evade a hit or land a blow."},
            "Expert": {"hp_die": 6, "hp_bonus": 0, "description": "Skill specialists. Gain an extra skill point per level and the Masterful Expertise ability to reroll a failed skill check."},
            "Mage": {"hp_die": 4, "hp_bonus": 0, "description": "Wielders of magic. Choose an arcane tradition (High Mage, Elementalist, Necromancer)."},
            "Adventurer": {"hp_die": 6, "hp_bonus": 0, "description": "A mix of classes. Choose two partial classes."}
        }
        self.wwn_backgrounds = ["Artisan", "Barbarian", "Carter", "Courtesan", "Criminal", "Hunter", "Laborer", "Merchant", "Noble", "Nomad", "Peasant", "Performer", "Physician", "Priest", "Sailor", "Scholar", "Slave", "Soldier", "Thug", "Wanderer"]
        self.wwn_skills = ["Administer", "Connect", "Convince", "Craft", "Exert", "Heal", "Know", "Lead", "Magic", "Notice", "Perform", "Pray", "Punch", "Ride", "Sail", "Shoot", "Sneak", "Stab", "Survive", "Trade", "Work"]
        self.wwn_weapons = ["Longsword", "Spear", "Battle Axe", "Longbow", "Dagger"]
        self.wwn_armor = ["Buff Jacket", "Linothorax", "Mail Shirt", "None"]

        # CWN Data
        self.cwn_classes = {
            "Operator": {"hp_die": 6, "hp_bonus": 2, "description": "Combat specialists. +1 attack bonus per level, access to restricted cyberware."},
            "Hacker": {"hp_die": 6, "hp_bonus": 0, "description": "Digital ghosts. Start with a cyberdeck and high-end programs."},
            "Face": {"hp_die": 6, "hp_bonus": 0, "description": "Social chameleons. Start with extra contacts and social cyberware."},
            "Ganger": {"hp_die": 8, "hp_bonus": 0, "description": "Street survivors. Extra toughness and street-level connections."}
        }
        self.cwn_backgrounds = ["Corp Drone", "Ganger", "Hacker", "Hustler", "Joygirl/boy", "Mercenary", "Nomad", "Reporter", "Rocker", "Smuggler"] # Keeping it brief for the demo
        self.cwn_skills = ["Administer", "Connect", "Drive", "Exert", "Fix", "Hack", "Heal", "Know", "Lead", "Notice", "Perform", "Program", "Punch", "Shoot", "Sneak", "Stab", "Survive", "Talk", "Trade", "Work"]
        self.cwn_weapons = ["Heavy Pistol", "Submachine Gun", "Combat Knife", "Monowhip", "Stun Gun"]
        self.cwn_armor = ["Armored Clothing", "Ballistic Vest", "None"]

        # Load Foci
        self.swn_foci = []
        self.wwn_foci = []
        self.cwn_foci = []
        self._load_foci()

    def _load_foci(self):
        """Loads foci from data/foci.json if it exists"""
        foci_path = os.path.join('data', 'foci.json')
        if os.path.exists(foci_path):
            try:
                with open(foci_path, 'r', encoding='utf-8') as f:
                    all_foci = json.load(f)
                    self.swn_foci = [f for f in all_foci if f.get("source_book") == "Stars WN"]
                    self.wwn_foci = [f for f in all_foci if f.get("source_book") == "Worlds WN"]
                    self.cwn_foci = [f for f in all_foci if f.get("source_book") == "Cities WN"]
            except Exception as e:
                print(f"Error loading foci in CharGenCog: {e}")

    def roll_stat(self):
        """Rolls 3d6"""
        return sum(random.randint(1, 6) for _ in range(3))

    def get_modifier(self, score):
        """Standard B/X / SWN stat modifiers"""
        if score <= 3: return -2
        if score <= 7: return -1
        if score <= 13: return 0
        if score <= 17: return 1
        return 2

    def generate_character(self, system: str, interaction_or_ctx, replace_stat: str = None):
        """Core logic to generate a character for a specific system"""
        # Select matching data dictionaries based on the system
        if system == "SWN":
            classes, backgrounds, skills, weapons, armor = self.swn_classes, self.swn_backgrounds, self.swn_skills, self.swn_weapons, self.swn_armor
            color = discord.Color.blue()
        elif system == "WWN":
            classes, backgrounds, skills, weapons, armor = self.wwn_classes, self.wwn_backgrounds, self.wwn_skills, self.wwn_weapons, self.wwn_armor
            color = discord.Color.dark_red()
        elif system == "CWN":
            classes, backgrounds, skills, weapons, armor = self.cwn_classes, self.cwn_backgrounds, self.cwn_skills, self.cwn_weapons, self.cwn_armor
            color = discord.Color.dark_grey()
        else:
            return None # Fallback

        # Roll Stats (3d6 in order)
        stats = {
            "Strength": self.roll_stat(),
            "Dexterity": self.roll_stat(),
            "Constitution": self.roll_stat(),
            "Intelligence": self.roll_stat(),
            "Wisdom": self.roll_stat(),
            "Charisma": self.roll_stat()
        }
        
        # Rule: One stat can be replaced with 14
        if replace_stat and replace_stat.capitalize() in stats:
            actual_replace = replace_stat.capitalize()
            stats[actual_replace] = 14
            replaced_by_user = True
        else:
            actual_replace = min(stats, key=stats.get)
            stats[actual_replace] = 14
            replaced_by_user = False
        
        # Random Selections
        background = random.choice(backgrounds)
        char_class_name = random.choice(list(classes.keys()))
        char_class = classes[char_class_name]
        
        # Pick 2 random starting skills
        starting_skills = random.sample(skills, 2)
        
        # Calculate HP
        con_mod = self.get_modifier(stats["Constitution"])
        hp = random.randint(1, char_class["hp_die"]) + char_class["hp_bonus"] + con_mod
        hp = max(1, hp) # Minimum 1 HP

        # Pick a random Focus (Level 1)
        focus = None
        if system == "SWN" and self.swn_foci:
            focus = random.choice(self.swn_foci)
        elif system == "WWN" and self.wwn_foci:
            focus = random.choice(self.wwn_foci)
        elif system == "CWN" and self.cwn_foci:
            focus = random.choice(self.cwn_foci)
        
        # Formatting the Embed
        embed = discord.Embed(title=f"{system} Random Character (Level 1)", color=color)
        
        user_name = interaction_or_ctx.user.display_name if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author.display_name
        embed.set_author(name=f"{background} {char_class_name}", icon_url=interaction_or_ctx.user.display_avatar.url if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author.display_avatar.url)
        
        # Format Stats (Compact: 3 per line)
        stat_keys = list(stats.keys())
        stats_text = ""
        for i in range(0, len(stat_keys), 2): # 2 per line for better mobile readability but still compact
            k1, k2 = stat_keys[i], stat_keys[i+1]
            m1, m2 = self.get_modifier(stats[k1]), self.get_modifier(stats[k2])
            ms1 = f"+{m1}" if m1 > 0 else f"{m1}"
            ms2 = f"+{m2}" if m2 > 0 else f"{m2}"
            stats_text += f"**{k1[:3]}**: {stats[k1]} ({ms1}) | **{k2[:3]}**: {stats[k2]} ({ms2})\n"
            
        embed.add_field(name="Attributes", value=stats_text, inline=False)
        
        # Combat Stats (Compact)
        base_attack = "+1" if char_class_name in ["Warrior", "Operator"] else "+0"
        combat_text = f"**HP**: {hp} | **AB**: {base_attack} | **AC**: 10 (base)\n"
        combat_text += f"**Gear**: {random.choice(weapons)}, {random.choice(armor)}"
        
        embed.add_field(name="Combat & Gear", value=combat_text, inline=False)
        
        # Focus & Skills
        if focus:
            focus_text = f"**{focus['name']}**\n{focus['description'][:200]}..." # Truncate long descriptions
            embed.add_field(name="Random Focus", value=focus_text, inline=False)

        embed.add_field(name="Starting Skills", value=", ".join(starting_skills), inline=True)
        embed.add_field(name="Class Feature", value=char_class["description"], inline=True)
        
        footer_msg = f"Rule: Raised {actual_replace} to 14."
        if replaced_by_user:
            footer_msg = f"Rule: Manually raised {actual_replace} to 14."
        embed.set_footer(text=footer_msg)
        
        return embed

    # --- SWN Commands ---
    @app_commands.command(name="swn", description="Generate a random Level 1 Stars Without Number character")
    @app_commands.describe(replace_stat="Choose which attribute to set to 14. If left blank, replaces the lowest.")
    @app_commands.choices(replace_stat=[
        app_commands.Choice(name="Strength", value="Strength"),
        app_commands.Choice(name="Dexterity", value="Dexterity"),
        app_commands.Choice(name="Constitution", value="Constitution"),
        app_commands.Choice(name="Intelligence", value="Intelligence"),
        app_commands.Choice(name="Wisdom", value="Wisdom"),
        app_commands.Choice(name="Charisma", value="Charisma")
    ])
    async def swn(self, interaction: discord.Interaction, replace_stat: str = None):
        embed = self.generate_character("SWN", interaction, replace_stat)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="swn", help="Generate a random Level 1 SWN character. Usage: !swn [Attribute to set to 14]")
    async def swn_text(self, ctx, replace_stat: str = None):
        embed = self.generate_character("SWN", ctx, replace_stat)
        await ctx.send(embed=embed)

    # --- WWN Commands ---
    @app_commands.command(name="wwn", description="Generate a random Level 1 Worlds Without Number character")
    @app_commands.describe(replace_stat="Choose which attribute to set to 14. If left blank, replaces the lowest.")
    @app_commands.choices(replace_stat=[
        app_commands.Choice(name="Strength", value="Strength"),
        app_commands.Choice(name="Dexterity", value="Dexterity"),
        app_commands.Choice(name="Constitution", value="Constitution"),
        app_commands.Choice(name="Intelligence", value="Intelligence"),
        app_commands.Choice(name="Wisdom", value="Wisdom"),
        app_commands.Choice(name="Charisma", value="Charisma")
    ])
    async def wwn(self, interaction: discord.Interaction, replace_stat: str = None):
        embed = self.generate_character("WWN", interaction, replace_stat)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="wwn", help="Generate a random Level 1 WWN character. Usage: !wwn [Attribute to set to 14]")
    async def wwn_text(self, ctx, replace_stat: str = None):
        embed = self.generate_character("WWN", ctx, replace_stat)
        await ctx.send(embed=embed)

    # --- CWN Commands ---
    @app_commands.command(name="cwn", description="Generate a random Level 1 Cities Without Number character")
    @app_commands.describe(replace_stat="Choose which attribute to set to 14. If left blank, replaces the lowest.")
    @app_commands.choices(replace_stat=[
        app_commands.Choice(name="Strength", value="Strength"),
        app_commands.Choice(name="Dexterity", value="Dexterity"),
        app_commands.Choice(name="Constitution", value="Constitution"),
        app_commands.Choice(name="Intelligence", value="Intelligence"),
        app_commands.Choice(name="Wisdom", value="Wisdom"),
        app_commands.Choice(name="Charisma", value="Charisma")
    ])
    async def cwn(self, interaction: discord.Interaction, replace_stat: str = None):
        embed = self.generate_character("CWN", interaction, replace_stat)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="cwn", help="Generate a random Level 1 CWN character. Usage: !cwn [Attribute to set to 14]")
    async def cwn_text(self, ctx, replace_stat: str = None):
        embed = self.generate_character("CWN", ctx, replace_stat)
        await ctx.send(embed=embed)

    # --- Threshold Command ---
    @app_commands.command(name="threshold", description="Roll 3d6 attributes in order (Str, Dex, Con, Int, Wis, Cha)")
    async def threshold(self, interaction: discord.Interaction):
        stats = {
            "Strength": self.roll_stat(),
            "Dexterity": self.roll_stat(),
            "Constitution": self.roll_stat(),
            "Intelligence": self.roll_stat(),
            "Wisdom": self.roll_stat(),
            "Charisma": self.roll_stat()
        }
        
        embed = discord.Embed(title="Attributes (3d6 In Order)", color=discord.Color.purple())
        user_name = interaction.user.display_name
        embed.set_author(name=user_name, icon_url=interaction.user.display_avatar.url)
        
        stats_text = ""
        for name, score in stats.items():
            mod = self.get_modifier(score)
            mod_str = f"+{mod}" if mod > 0 else f"{mod}"
            stats_text += f"**{name[:3]}**:\u00A0{score}\u00A0({mod_str})\n"
            
        embed.add_field(name="Random Stats", value=stats_text, inline=True)
        embed.set_footer(text="Rule: You may replace exactly one attribute with a score of 14.")
        await interaction.response.send_message(embed=embed)

    @commands.command(name="threshold", help="Roll 3d6 attributes in order (Str, Dex, Con, Int, Wis, Cha)")
    async def threshold_text(self, ctx):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send("*(I tried to delete your command, but I lack the 'Manage Messages' permission!)*")
        except discord.HTTPException:
            pass
            
        stats = {
            "Strength": self.roll_stat(),
            "Dexterity": self.roll_stat(),
            "Constitution": self.roll_stat(),
            "Intelligence": self.roll_stat(),
            "Wisdom": self.roll_stat(),
            "Charisma": self.roll_stat()
        }
        
        embed = discord.Embed(title="Attributes (3d6 In Order)", color=discord.Color.purple())
        user_name = ctx.author.display_name
        embed.set_author(name=user_name, icon_url=ctx.author.display_avatar.url)
        
        stats_text = ""
        for name, score in stats.items():
            mod = self.get_modifier(score)
            mod_str = f"+{mod}" if mod > 0 else f"{mod}"
            stats_text += f"**{name[:3]}**:\u00A0{score}\u00A0({mod_str})\n"
            
        embed.add_field(name="Random Stats", value=stats_text, inline=True)
        embed.set_footer(text="Rule: You may replace exactly one attribute with a score of 14.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CharGenCog(bot))
