import discord
from discord import app_commands
from discord.ext import commands
import random

class SandboxCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.world_tags = [
            "Abandoned Colony", "Alien Ruins", "Altered Climate", "Area 51", "Badlands World", 
            "Battleground", "Beastmasters", "Bubble City", "Civil War", "Cold War", 
            "Coronal World", "Cyber-Communism", "Cyborgs", "Cyclical Doom", "Desert World", 
            "Dictatorship", "Dying Race", "Eugenic Cult", "Flying Cities", "Forbidden Tech", 
            "Freak Geology", "Friendly Foe", "Gold Rush", "Heavy Industry", "Hive World", 
            "Holy War", "Hostile Biosphere", "Hostile Space", "Immortals", "Local Tech", 
            "Major Shipyard", "Maneaters", "Mantle World", "Megacorporate", "Mercenaries", 
            "Minimal Contact", "Misplaced World", "Night World", "Oceanic World", "Out of Contact", 
            "Outpost World", "Perimeter Agency", "Pilgrimage Site", "Pleasure World", "Police State", 
            "Post-Scarcity", "Preceptor Archive", "Pre-Tech Cultists", "Primitive Aliens", "Prison Planet", 
            "Psionics Academy", "Psyscape", "Quarantined World", "Radioactive World", "Refugees", 
            "Regional Hegemon", "Restrictive Laws", "Revanchists", "Revolutionaries", "Rigid Culture", 
            "Robot Servants", "Ruined Environment", "Scavenger World", "Sectarians", "Seismic Instability", 
            "Shackled World", "Sinister Secret", "Slumbering Menace", "Taboo Weaponry", "Theocracy", 
            "Tomb World", "Trade Hub", "Tyranny", "Unbraked AI", "Urbanized Surface", "Utopia?", 
            "Venomous World", "Warlords", "Water World", "Xenophiles", "Xenophobes", "Zombies"
        ]
        
        self.npc_backgrounds = ["Academic", "Aristocrat", "Clergy", "Commuter", "Corpo", "Criminal", "Entertainer", "Ganger", "Laborer", "Law Enforcement", "Mercenary", "Merchant", "Nomad", "Official", "Peasant", "Pilot", "Politician", "Scholar", "Soldier", "Technician", "Vagabond", "Worker"]
        self.npc_quirks = ["Always wearing shades", "Speaks too quietly", "Constantly checks their watch", "Has a nervous tick", "Overly familiar", "Suspicious of technology", "Has a cybernetic limb", "Missing an eye", "Covered in tattoos", "Carries a mysterious token", "Coughs frequently", "Flirts shamelessly", "Smells like ozone or cheap synth-cigar", "Has a pet drone", "Uses outdated slang"]
        self.npc_desires = ["To get off this rock", "To find a missing relative", "To settle a score", "To make a quick buck", "To secure a steady job", "To uncover a conspiracy", "To hide from the law", "To start a new life", "To acquire rare tech", "To earn respect"]

        self.corp_businesses = ["Aeronautics", "Agriculture", "Arms", "Biotech", "Cybernetics", "Entertainment", "Finance", "Heavy Industry", "Information", "Logistics", "Media", "Mining", "Pharmaceuticals", "Robotics", "Security", "Software", "Spacedock", "Transportation"]
        self.corp_reputations = ["Ruthless", "Innovative", "Corrupt", "Benevolent", "Struggling", "Monopolistic", "Secretive", "Aggressive", "Stagnant", "Reliable"]
        
        self.alien_forms = ["Amphibian", "Arachnid", "Avian", "Blob", "Crustacean", "Energy", "Fungal", "Humanoid", "Insectoid", "Mammalian", "Mechanoid", "Molluscoid", "Plant", "Reptilian"]
        self.alien_traits = ["Telepathic", "Acidic Blood", "Multiple Arms", "Armored Carapace", "Flight", "Water-breathing", "Camouflage", "Rapid Regeneration", "Symbiotic", "Hive Mind", "Silicon-based", "Empathic"]
        
    def generate_planet(self):
        tags = random.sample(self.world_tags, 2)
        atmosphere = random.choice(["Corrosive", "Inert", "Airless", "Thin", "Breathable", "Thick", "Invasive"])
        temperature = random.choice(["Frozen", "Cold", "Variable", "Temperate", "Warm", "Boiling"])
        biosphere = random.choice(["Remnant", "Microbial", "No native life", "Human-miscible", "Immiscible", "Engineered"])
        population = random.choice(["Failed", "Tens of thousands", "Hundreds of thousands", "Millions", "Billions", "Alien inhabitants"])
        tech_level = random.choice(["TL0 (Stone Age)", "TL1 (Medieval)", "TL2 (19th Century)", "TL3 (20th Century)", "TL4 (Modern/Postitech)", "TL5 (Pretech)"])
        
        embed = discord.Embed(title="🪐 Generated Planet", color=discord.Color.blue())
        embed.add_field(name="World Tags", value=f"**{tags[0]}** & **{tags[1]}**", inline=False)
        embed.add_field(name="Atmosphere", value=atmosphere, inline=True)
        embed.add_field(name="Temperature", value=temperature, inline=True)
        embed.add_field(name="Biosphere", value=biosphere, inline=True)
        embed.add_field(name="Population", value=population, inline=True)
        embed.add_field(name="Tech Level", value=tech_level, inline=True)
        return embed

    def generate_npc(self):
        bg = random.choice(self.npc_backgrounds)
        quirk = random.choice(self.npc_quirks)
        desire = random.choice(self.npc_desires)
        
        # Combat Stats
        hd = random.choice(["1", "1", "2", "3", "4"])
        ac = random.randint(10, 16)
        atk = int(hd) if hd.isdigit() else 1
        skill = random.randint(0, 2)
        
        embed = discord.Embed(title="👤 Generated NPC", color=discord.Color.purple())
        embed.add_field(name="Background", value=bg, inline=True)
        embed.add_field(name="Quirk", value=quirk, inline=True)
        embed.add_field(name="Deep Desire", value=desire, inline=False)
        embed.add_field(name="Stats", value=f"**HD:** {hd}  |  **AC:** {ac}  |  **Attack:** +{atk}  |  **Skill:** +{skill}", inline=False)
        return embed

    def generate_corp(self):
        biz = random.choice(self.corp_businesses)
        rep = random.choice(self.corp_reputations)
        
        # Simple name generation
        prefix = random.choice(["Omni", "Aero", "Stellar", "Nova", "Cyber", "Bio", "Quantum", "Macro", "Exo", "Terra"])
        suffix = random.choice(["Corp", "Systems", "Dynamics", "Industries", "Enterprises", "Solutions", "Technologies", "Group", "Consortium", "Network"])
        name = f"{prefix} {biz} {suffix}"
        
        embed = discord.Embed(title=f"🏢 Corporation: {name}", color=discord.Color.dark_grey())
        embed.add_field(name="Primary Business", value=biz, inline=True)
        embed.add_field(name="Reputation", value=rep, inline=True)
        return embed

    def generate_alien(self):
        form = random.choice(self.alien_forms)
        trait = random.choice(self.alien_traits)
        
        # Combat Stats
        hd = random.choice(["1", "2", "3", "5", "8"])
        ac = random.randint(12, 18)
        atk = int(hd) if hd.isdigit() else 2
        skill = random.randint(1, 4)
        
        embed = discord.Embed(title="👽 Generated Alien Species", color=discord.Color.green())
        embed.add_field(name="Body Form", value=form, inline=True)
        embed.add_field(name="Special Trait", value=trait, inline=True)
        embed.add_field(name="Stats", value=f"**HD:** {hd}  |  **AC:** {ac}  |  **Attack:** +{atk}  |  **Skill:** +{skill}", inline=False)
        return embed

    @app_commands.command(name="gen", description="Sandbox generation: Create a planet, NPC, corp, or alien.")
    @app_commands.describe(subject="What do you want to generate?")
    @app_commands.choices(subject=[
        app_commands.Choice(name="Planet", value="planet"),
        app_commands.Choice(name="NPC", value="npc"),
        app_commands.Choice(name="Corporation", value="corp"),
        app_commands.Choice(name="Alien Species", value="alien")
    ])
    async def gen(self, interaction: discord.Interaction, subject: str):
        if subject == "planet":
            embed = self.generate_planet()
        elif subject == "npc":
            embed = self.generate_npc()
        elif subject == "corp":
            embed = self.generate_corp()
        elif subject == "alien":
            embed = self.generate_alien()
            
        await interaction.response.send_message(embed=embed)

    @commands.command(name="gen", help="Generate a random entity: !gen <planet|npc|corp|alien>")
    async def gen_text(self, ctx, subject: str = None):
        valid = ["planet", "npc", "corp", "alien", "corporation"]
        
        if not subject or subject.lower() not in valid:
            await ctx.send("Please specify what to generate: `!gen planet`, `!gen npc`, `!gen corp`, or `!gen alien`.")
            return
            
        subject = subject.lower()
        if subject == "planet":
            embed = self.generate_planet()
        elif subject == "npc":
            embed = self.generate_npc()
        elif subject in ["corp", "corporation"]:
            embed = self.generate_corp()
        elif subject == "alien":
            embed = self.generate_alien()
            
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SandboxCog(bot))
