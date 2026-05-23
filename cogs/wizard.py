import discord
from discord import app_commands
from discord.ext import commands
import random
from cogs.chargen import CharGenCog

class StatReplaceView(discord.ui.View):
    def __init__(self, interaction, stats, user_id):
        super().__init__(timeout=300)
        self.stats = stats
        self.user_id = user_id
        self.interaction = interaction

    @discord.ui.select(
        placeholder="Choose an attribute to replace with 14",
        min_values=1, max_values=1,
        options=[
            discord.SelectOption(label="Strength", description="Replace Str with 14"),
            discord.SelectOption(label="Dexterity", description="Replace Dex with 14"),
            discord.SelectOption(label="Constitution", description="Replace Con with 14"),
            discord.SelectOption(label="Intelligence", description="Replace Int with 14"),
            discord.SelectOption(label="Wisdom", description="Replace Wis with 14"),
            discord.SelectOption(label="Charisma", description="Replace Cha with 14")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your character wizard!", ephemeral=True)
            return

        choice = select.values[0]
        self.stats[choice] = 14
        
        system_view = SystemSelectView(interaction, self.stats, self.user_id)
        embed = discord.Embed(
            title="Step 2: Game System", 
            description="Which system are you rolling this character for?",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=system_view)


class SystemSelectView(discord.ui.View):
    def __init__(self, interaction, stats, user_id):
        super().__init__(timeout=300)
        self.stats = stats
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Select your Without Number Game",
        min_values=1, max_values=1,
        options=[
            discord.SelectOption(label="Stars Without Number", description="Sci-Fi setting", value="SWN", emoji="🛸"),
            discord.SelectOption(label="Worlds Without Number", description="Fantasy setting", value="WWN", emoji="⚔️"),
            discord.SelectOption(label="Cities Without Number", description="Cyberpunk setting", value="CWN", emoji="🏙️")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your character wizard!", ephemeral=True)
            return

        system = select.values[0]
        class_view = ClassSelectView(interaction, self.stats, self.user_id, system)
        
        embed = discord.Embed(
            title=f"Step 3: Choose Class ({system})", 
            description="Select a class for your character based on this system.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=class_view)


class ClassSelectView(discord.ui.View):
    def __init__(self, interaction, stats, user_id, system):
        super().__init__(timeout=300)
        self.stats = stats
        self.user_id = user_id
        self.system = system
        self.cog_data = CharGenCog(None)  # Temporary instance just to access data dicts
        
        options = []
        if system == "SWN":
            classes = self.cog_data.swn_classes
        elif system == "WWN":
            classes = self.cog_data.wwn_classes
        else:
            classes = self.cog_data.cwn_classes
            
        for c in classes.keys():
            options.append(discord.SelectOption(label=c, description=classes[c]["description"]))
            
        select = discord.ui.Select(placeholder="Select your Class", min_values=1, max_values=1, options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        select = self.children[0]
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your character wizard!", ephemeral=True)
            return

        char_class = select.values[0]
        bg_view = BackgroundSelectView(interaction, self.stats, self.user_id, self.system, char_class)
        
        embed = discord.Embed(
            title=f"Step 4: Choose Background/Package", 
            description="Select your starting background to formulate growth, skills, and HP.",
            color=discord.Color.gold()
        )
        await interaction.response.edit_message(embed=embed, view=bg_view)


class BackgroundSelectView(discord.ui.View):
    def __init__(self, interaction, stats, user_id, system, char_class):
        super().__init__(timeout=300)
        self.stats = stats
        self.user_id = user_id
        self.system = system
        self.char_class = char_class
        self.cog_data = CharGenCog(None)
        
        options = []
        if system == "SWN":
            bgs = self.cog_data.swn_backgrounds[:25] # Limit to avoid 25 cap issues on SelectMenu
        elif system == "WWN":
            bgs = self.cog_data.wwn_backgrounds[:25]
        else:
            bgs = self.cog_data.cwn_backgrounds[:25]
            
        for b in bgs:
            options.append(discord.SelectOption(label=b))
            
        select = discord.ui.Select(placeholder="Select your Background", min_values=1, max_values=1, options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        select = self.children[0]
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your character wizard!", ephemeral=True)
            return

        background = select.values[0]
        await self.finalize_character(interaction, background)
        
    async def finalize_character(self, interaction, background):
        # Auto-roll HP, pick universal lightweight growth, and gear
        if self.system == "SWN":
            classes, skills, weapons, armor = self.cog_data.swn_classes, self.cog_data.swn_skills, self.cog_data.swn_weapons, self.cog_data.swn_armor
            color = discord.Color.blue()
        elif self.system == "WWN":
            classes, skills, weapons, armor = self.cog_data.wwn_classes, self.cog_data.wwn_skills, self.cog_data.wwn_weapons, self.cog_data.wwn_armor
            color = discord.Color.dark_red()
        else:
            classes, skills, weapons, armor = self.cog_data.cwn_classes, self.cog_data.cwn_skills, self.cog_data.cwn_weapons, self.cog_data.cwn_armor
            color = discord.Color.dark_grey()
            
        c_data = classes[self.char_class]
        
        # Calculate HP
        con_mod = self.cog_data.get_modifier(self.stats["Constitution"])
        hp = max(1, random.randint(1, c_data["hp_die"]) + c_data["hp_bonus"] + con_mod)
        
        # Growth: 2 random skills, +1 random stat boost
        starting_skills = random.sample(skills, 2)
        boosted_stat = random.choice(list(self.stats.keys()))
        if self.stats[boosted_stat] < 18:
            self.stats[boosted_stat] += 1
            
        base_attack = "+1" if self.char_class in ["Warrior", "Operator"] else "+0"
        
        embed = discord.Embed(title=f"🎲 Final {self.system} Character", color=color)
        user_name = interaction.user.display_name
        embed.set_author(name=f"{background} {self.char_class} ({user_name})", icon_url=interaction.user.display_avatar.url)
        
        stats_text = ""
        for name, score in self.stats.items():
            mod = self.cog_data.get_modifier(score)
            mod_str = f"+{mod}" if mod > 0 else f"{mod}"
            if name == boosted_stat:
                stats_text += f"**{name[:3]}**:\u00A0{score}*\u00A0({mod_str})\n" # Mark boosted
            else:
                stats_text += f"**{name[:3]}**:\u00A0{score}\u00A0({mod_str})\n"
                
        embed.add_field(name="Attributes", value=stats_text, inline=True)
        
        combat_text = f"**HP**: {hp} (1d{c_data['hp_die']}{'+' + str(c_data['hp_bonus']) if c_data['hp_bonus'] else ''})\n"
        combat_text += f"**Attack Bonus**: {base_attack}\n"
        combat_text += f"**AC**: 10 (base)\n\n"
        combat_text += f"**Weapon**: {random.choice(weapons)}\n"
        combat_text += f"**Armor**: {random.choice(armor)}\n"
        combat_text += f"*(Lightweight Gear Package applied)*"
        
        embed.add_field(name="Combat & Gear", value=combat_text, inline=True)
        embed.add_field(name="Growth & Background Skills", value=", ".join(starting_skills), inline=False)
        embed.add_field(name="Class Feature", value=c_data["description"], inline=False)
        
        embed.set_footer(text=f"Growth: Randomly learned 2 skills and boosted {boosted_stat} by +1.")
        await interaction.response.edit_message(embed=embed, view=None)


class WizardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cg = CharGenCog(bot)

    @app_commands.command(name="threshold_wizard", description="Start the interactive step-by-step character generator!")
    async def threshold_wizard(self, interaction: discord.Interaction):
        stats = {
            "Strength": self.cg.roll_stat(),
            "Dexterity": self.cg.roll_stat(),
            "Constitution": self.cg.roll_stat(),
            "Intelligence": self.cg.roll_stat(),
            "Wisdom": self.cg.roll_stat(),
            "Charisma": self.cg.roll_stat()
        }
        
        embed = discord.Embed(
            title="Step 1: Rolled 3d6 Attributes", 
            description="Here are your raw stats in order. Which one do you want to replace with 14?",
            color=discord.Color.purple()
        )
        stats_text = ""
        for name, score in stats.items():
            mod = self.cg.get_modifier(score)
            mod_str = f"+{mod}" if mod > 0 else f"{mod}"
            stats_text += f"**{name[:3]}**:\u00A0{score}\u00A0({mod_str})\n"
            
        embed.add_field(name="Raw Stats", value=stats_text)
        
        view = StatReplaceView(interaction, stats, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(WizardCog(bot))
