import discord
from discord import app_commands
from discord.ext import commands

class MapCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="map", description="Get the link to the tactical map for this server.")
    async def map_slash(self, interaction: discord.Interaction):
        """Slash command to get the map link."""
        guild_id = interaction.guild_id
        if not guild_id:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
            
        # The base URL for the map
        base_url = "https://dicewithoutnumber.duckdns.org/map"
        full_url = f"{base_url}?guild_id={guild_id}"
        
        embed = discord.Embed(
            title="🗺️ Tactical Map Link",
            description=f"Click the button below to open the tactical grid for **{interaction.guild.name}**.",
            color=discord.Color.blue()
        )
        
        view = discord.ui.View()
        button = discord.ui.Button(label="Open Map", url=full_url, style=discord.ButtonStyle.link)
        view.add_item(button)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.command(name="map", help="Get the link to the tactical map for this server.")
    async def map_prefix(self, ctx):
        """Prefix command to get the map link."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
            
        base_url = "https://dicewithoutnumber.duckdns.org/map"
        full_url = f"{base_url}?guild_id={ctx.guild.id}"
        
        embed = discord.Embed(
            title="🗺️ Tactical Map Link",
            description=f"Click the button below to open the tactical grid for **{ctx.guild.name}**.",
            color=discord.Color.blue()
        )
        
        view = discord.ui.View()
        button = discord.ui.Button(label="Open Map", url=full_url, style=discord.ButtonStyle.link)
        view.add_item(button)
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(MapCommands(bot))
