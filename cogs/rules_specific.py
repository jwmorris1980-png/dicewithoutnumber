import discord
from discord import app_commands
from discord.ext import commands

class SpecificRulesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_ship_combat_embed(self):
        embed = discord.Embed(
            title="🚀 SWN Starship Combat",
            description="A quick reference for the phases and actions of Ship Combat in Stars Without Number.",
            color=discord.Color.dark_purple()
        )
        
        embed.add_field(name="1. Command Phase", value="The Captain acts. They can grant bonus Command Points (CP) to other departments or take the *Support Department*, *Do Your Duty*, or *Crisis Management* actions.", inline=False)
        embed.add_field(name="2. Engineering Phase", value="The Engineer acts. They can generate CP, repair Hull/systems, or use *Push the Engines* to speed up the ship.", inline=False)
        embed.add_field(name="3. Gunnery Phase", value="The Gunner acts. They fire weapons using CP, or take actions like *Target Systems*, *Evasive Maneuvers*, or *Fire All Guns*.", inline=False)
        embed.add_field(name="4. Communications Phase", value="The Comms Officer acts. They can scramble enemy sensors, slice ship systems, or take the *Sensor Ghost* action.", inline=False)
        embed.add_field(name="5. Pilot Phase", value="The Pilot acts. They maneuver the ship, try to escape combat, or take the *Ramming Speed* action.", inline=False)
        
        embed.set_footer(text="Command Points (CP) reset to 0 at the end of every round. Unused CP cannot be saved.")
        return embed

    def get_hacking_embed(self):
        embed = discord.Embed(
            title="💻 CWN / SWN Hacking Rules",
            description="A quick reference for running cyberspace intrusions.",
            color=discord.Color.brand_green()
        )
        
        prep = (
            "1. **Trace**: The hacker must physically connect or establish a line-of-sight signal to the target.\n"
            "2. **Access**: The hacker attempts to defeat the outer Access Node (usually an Intel/Program or Fix check). Failure alerts the system.\n"
            "3. **Navigation**: Once inside, the hacker moves between isolated 'Nodes' to find what they want."
        )
        embed.add_field(name="Network Infiltration", value=prep, inline=False)
        
        actions = (
            "• **Analyze** (Instant): Figure out what a Node does and what security it has.\n"
            "• **Control** (Main): Force the Node to perform its intended real-world function (e.g., open a door, vent gas).\n"
            "• **Decrypt** (Main): Break into secured files within the Node.\n"
            "• **Mask** (Main): Hide from actively searching security Demons.\n"
            "• **Terminate** (Main): Attempt to crash or delete a specific program or Demon."
        )
        embed.add_field(name="Hacker Verbs", value=actions, inline=False)
        
        embed.set_footer(text="Watch your heat! Every action leaves traces that system admins or Demons will use to hunt you.")
        return embed

    # --- Ship Combat ---
    @app_commands.command(name="ship_combat", description="Show a cheat-sheet for Starship Combat phases")
    async def ship_combat_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.get_ship_combat_embed())

    @commands.command(name="ship_combat", help="Show a cheat-sheet for Starship Combat phases")
    async def ship_combat_text(self, ctx):
        await ctx.send(embed=self.get_ship_combat_embed())

    # --- Hacking ---
    @app_commands.command(name="hack_help", description="Show a cheat-sheet for Hacking rules and actions")
    async def hack_help_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.get_hacking_embed())

    @commands.command(name="hack_help", help="Show a cheat-sheet for Hacking rules and actions")
    async def hack_help_text(self, ctx):
        await ctx.send(embed=self.get_hacking_embed())

async def setup(bot):
    await bot.add_cog(SpecificRulesCog(bot))
