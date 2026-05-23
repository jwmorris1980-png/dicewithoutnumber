import discord
from discord import app_commands
from discord.ext import commands
import random

class StorytellerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.plot_hooks = [
            "A sudden mechanical failure threatens the immediate environment.",
            "An unexpected ally (or old acquaintance) appears with vital information.",
            "A secret or betrayal is accidentally revealed through a slipped word or lost data pad.",
            "Local authorities or a rival group arrives at the worst possible moment.",
            "A mysterious signal or message is received that only one PC can understand.",
            "The environment itself becomes hazardous (gas leak, radiation spike, structural collapse).",
            "A powerful entity offers a 'deal you can't refuse'.",
            "An item the PCs are carrying starts acting strangely or attracts unwanted attention.",
            "A target or objective is seen leaving the area in a hurry.",
            "The PCs are mistaken for someone else—someone much more dangerous or important.",
            "A sudden piece of 'good luck' happens, but it clearly comes with strings attached.",
            "A bystander or innocent is caught in the crossfire and needs immediate help.",
            "A piece of tech is discovered that technically shouldn't exist in this sector.",
            "The weather (or local stellar phenomena) changes drastically, cutting off escape.",
            "A rival's plan is much further along than previously thought."
        ]
        
        self.loot_trinkets = [
            "A dented locket with a picture of a world that no longer exists.",
            "A small pouch of crystalline dust that glows faintly in the dark.",
            "A data-chip containing encrypted, low-quality recordings of opera.",
            "A lucky coin from a dead empire, worn smooth by thumbing.",
            "A collection of exotic dried insects pinned to a piece of cork.",
            "A hand-drawn map of a nearby city with one building circled in red.",
            "A miniature holographic projector that only shows a rotating geometric shape.",
            "A scent-canister that smells like home to whoever opens it.",
            "A deck of cards where the faces are all legendary explorers.",
            "A jar of 'real' soil, highly illegal in this star system.",
            "A broken cybernetic finger that still twitches occasionally.",
            "A set of keys for a vehicle that hasn't been made in fifty years.",
            "A small, very angry robotic spider in a glass case (it's harmless).",
            "A pressed flower from a world known for its toxic atmosphere.",
            "A handwritten note that simply says: 'Don't trust the Captain.'"
        ]

    @app_commands.command(name="reaction", description="Roll 2d6 to determine an NPC's reaction to the party.")
    async def reaction(self, interaction: discord.Interaction):
        roll = random.randint(1, 6) + random.randint(1, 6)
        
        if roll <= 2:
            result = "**Hostile** - They are actively antagonistic or will attack if provoked."
            color = discord.Color.dark_red()
        elif roll <= 5:
            result = "**Unfriendly** - They are wary, cold, or seek to make things difficult."
            color = discord.Color.red()
        elif roll <= 8:
            result = "**Neutral** - They are indifferent, purely professional, or wait-and-see."
            color = discord.Color.light_grey()
        elif roll <= 11:
            result = "**Friendly** - They are helpful, open, and predisposed to like the PCs."
            color = discord.Color.green()
        else:
            result = "**Helpful** - They are actively supportive and will go out of their way for the PCs."
            color = discord.Color.gold()
            
        embed = discord.Embed(title="🎲 Reaction Roll", description=f"Result: **{roll}**\n\n{result}", color=color)
        embed.set_footer(text="Standard 2d6 Reaction Table")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="morale", description="Roll 2d6 to check an NPC's morale.")
    @app_commands.describe(target="The NPC's Morale score (usually 6-10)")
    async def morale(self, interaction: discord.Interaction, target: int):
        roll = random.randint(1, 6) + random.randint(1, 6)
        
        if roll <= target:
            result = "**SUCCESS** - They hold their ground and keep fighting."
            color = discord.Color.green()
        else:
            result = "**FAIL** - They break, flee, or surrender!"
            color = discord.Color.red()
            
        embed = discord.Embed(title="🛡️ Morale Check", description=f"Roll: **{roll}** vs Target: **{target}**\n\n{result}", color=color)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="oracle", description="Ask the Oracle a Yes/No question (2d6 weighted response).")
    async def oracle(self, interaction: discord.Interaction):
        roll = random.randint(1, 6) + random.randint(1, 6)
        
        if roll <= 3:
            result = "**NO, AND...** (The worst outcome/additional complication)"
        elif roll <= 5:
            result = "**NO**"
        elif roll <= 6:
            result = "**NO, BUT...** (Small consolation)"
        elif roll <= 8:
            result = "**YES, BUT...** (Small complication)"
        elif roll <= 10:
            result = "**YES**"
        else:
            result = "**YES, AND...** (The best outcome/additional benefit)"
            
        embed = discord.Embed(title="🔮 The Oracle Says...", description=f"Result: **{roll}**\n\n{result}", color=discord.Color.dark_magenta())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="plot", description="Generate a random plot hook or situational idea for the GM.")
    async def plot(self, interaction: discord.Interaction):
        hook = random.choice(self.plot_hooks)
        embed = discord.Embed(title="📝 Plot Hook / Idea Generator", description=f"*{hook}*", color=discord.Color.blue())
        embed.set_footer(text="Use this for inspiration when players are stuck!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="loot", description="Roll for a random piece of flavor loot/trinket in an NPC's pocket.")
    async def loot(self, interaction: discord.Interaction):
        item = random.choice(self.loot_trinkets)
        embed = discord.Embed(title="🎒 Pocket Loot / Trinket", description=f"You find: **{item}**", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="weather", description="Generates random planetary/local weather. (Private)")
    async def weather(self, interaction: discord.Interaction):
        roll = random.randint(1, 6) + random.randint(1, 6)
        table = {
            2: "Severe Storm / Natural Disaster (Hazards active)",
            3: "Heavy Precipitation / Sandstorm (Visibility 10m)",
            4: "Light Precipitation / Fog (Visibility 30m)",
            5: "Overcast / Cloudy",
            6: "Overcast / Cloudy",
            7: "Clear / Perfect Conditions",
            8: "Clear / Perfect Conditions",
            9: "Extremely Hot / Humidity spike",
            10: "High Winds / Minor dust",
            11: "Unnatural/Psychic Phenomenon (Eerie)",
            12: "Perfect/Beautiful (Inspirational)"
        }
        res = table.get(roll, "Clear")
        embed = discord.Embed(title="🌤️ Weather/Environment Check", description=f"Roll: {roll}\nResult: **{res}**", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="encounter", description="Quick check for a random encounter (1 on 1d6). (Private)")
    async def encounter(self, interaction: discord.Interaction):
        roll = random.randint(1, 6)
        res = "⚠️ **RANDOM ENCOUNTER!** Prepare for contact." if roll == 1 else "✅ **All Clear.** No encounter this turn."
        embed = discord.Embed(title="🎲 Random Encounter Check", description=f"Roll: {roll}\nResult: {res}", color=discord.Color.red() if roll == 1 else discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="hazard", description="Generates a random environmental hazard or complication. (Private)")
    async def hazard(self, interaction: discord.Interaction):
        hazards = [
            "Radiation Spike: Take 1d6 damage unless shielded.",
            "Structural Instability: Floor/Wall collapse.",
            "Toxic Leak: Saving throw vs Poison or -2 to all rolls.",
            "Gravity Flux: Random high/low gravity patches.",
            "Sensor Deadzone: Maps and radar are useless.",
            "Electrical Surge: Energy weapons/devices malfunction.",
            "Psychic Echo: Vision of a past or future trauma.",
            "Predatory Wildlife: Local fauna attacks!"
        ]
        res = random.choice(hazards)
        embed = discord.Embed(title="🚧 Environmental Hazard", description=f"**{res}**", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StorytellerCog(bot))
