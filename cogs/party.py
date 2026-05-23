import discord
from discord import app_commands
from discord.ext import commands
import json
import os

@app_commands.guild_only()
class PartyCog(commands.GroupCog, group_name="party", description="Track shared credits, ship debt, and hull points."):
    def __init__(self, bot):
        self.bot = bot
        self.party_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'party')
        os.makedirs(self.party_dir, exist_ok=True)
        
    def get_guild_party(self, guild_id: int):
        file_path = os.path.join(self.party_dir, f"{guild_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "credits": 0,
            "debt": 0,
            "maintenance": 0,
            "hull": 0
        }
        
    def save_guild_party(self, guild_id: int, data: dict):
        file_path = os.path.join(self.party_dir, f"{guild_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    @app_commands.command(name="info", description="View shared party tracking info.")
    async def info(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_party(guild_id)
        
        embed = discord.Embed(title="🚀 Party & Ship Tracker", color=discord.Color.gold())
        embed.add_field(name="💰 Shared Credits", value=f"{data['credits']:,.2f} Cr", inline=False)
        embed.add_field(name="📉 Ship Debt", value=f"{data['debt']:,.2f} Cr", inline=True)
        embed.add_field(name="🔧 Maintenance", value=f"{data['maintenance']:,.2f} Cr", inline=True)
        embed.add_field(name="🛡️ Hull Points", value=f"{data['hull']}", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set", description="Set a specific party tracking field.")
    @app_commands.choices(field=[
        app_commands.Choice(name="Credits", value="credits"),
        app_commands.Choice(name="Ship Debt", value="debt"),
        app_commands.Choice(name="Maintenance", value="maintenance"),
        app_commands.Choice(name="Hull Points", value="hull")
    ])
    async def set_field(self, interaction: discord.Interaction, field: str, value: int):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_party(guild_id)
        
        data[field] = value
        self.save_guild_party(guild_id, data)
        await interaction.response.send_message(f"✅ Set Party/Ship **{field.capitalize()}** to {value}.")

    @app_commands.command(name="add", description="Add or subtract from a party tracking field.")
    @app_commands.choices(field=[
        app_commands.Choice(name="Credits", value="credits"),
        app_commands.Choice(name="Ship Debt", value="debt"),
        app_commands.Choice(name="Maintenance", value="maintenance"),
        app_commands.Choice(name="Hull Points", value="hull")
    ])
    async def add_field(self, interaction: discord.Interaction, field: str, amount: int):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_party(guild_id)
        
        data[field] += amount
        self.save_guild_party(guild_id, data)
        action = "Added" if amount >= 0 else "Subtracted"
        await interaction.response.send_message(f"✅ {action} **{abs(amount)}** to {field.capitalize()}. New total: {data[field]}.")

    @app_commands.command(name="split", description="Split a credit payout evenly among players.")
    async def split(self, interaction: discord.Interaction, amount: int, players: int = 4):
        split = amount / players
        await interaction.response.send_message(f"💸 Loot split! A **{amount:,.2f} Cr** payout split among {players} players equals **{split:,.2f} Cr** each.")

    @commands.group(name="party", invoke_without_command=True, help="Manage party stats. Subcommands: info, set, add, split.")
    async def party_text(self, ctx):
        await ctx.send("Use `!party info`, `!party set`, `!party add`, or `!party split`.")

    @party_text.command(name="info", help="View shared ship and party credits.")
    async def p_info(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_party(guild_id)
        embed = discord.Embed(title="🚀 Party & Ship Tracker", color=discord.Color.gold())
        embed.add_field(name="💰 Shared Credits", value=f"{data['credits']:,} Cr", inline=False)
        embed.add_field(name="📉 Ship Debt", value=f"{data['debt']:,} Cr", inline=True)
        embed.add_field(name="🔧 Maintenance", value=f"{data['maintenance']:,} Cr", inline=True)
        embed.add_field(name="🛡️ Hull Points", value=f"{data['hull']}", inline=True)
        await ctx.send(embed=embed)

    @party_text.command(name="set", help="Set a stat. Usage: !party set <credits|debt|maintenance|hull> <value>")
    async def p_set(self, ctx, field: str, value: int):
        valid = ['credits', 'debt', 'maintenance', 'hull']
        if field.lower() not in valid:
            await ctx.send("❌ Valid fields are: credits, debt, maintenance, hull.")
            return
            
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_party(guild_id)
        data[field.lower()] = value
        self.save_guild_party(guild_id, data)
        await ctx.send(f"✅ Set Party/Ship **{field.capitalize()}** to {value}.")

    @party_text.command(name="add", help="Add to stat. Usage: !party add <credits|debt|maintenance|hull> <amount>")
    async def p_add(self, ctx, field: str, amount: int):
        valid = ['credits', 'debt', 'maintenance', 'hull']
        if field.lower() not in valid:
            await ctx.send("❌ Valid fields are: credits, debt, maintenance, hull.")
            return
            
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_party(guild_id)
        data[field.lower()] += amount
        self.save_guild_party(guild_id, data)
        
        action = "Added" if amount >= 0 else "Subtracted"
        await ctx.send(f"✅ {action} **{abs(amount)}** to {field.capitalize()}. New total: {data[field.lower()]}.")

    @party_text.command(name="split", help="Split payout. Usage: !party split <amount> [players(default: 4)]")
    async def p_split(self, ctx, amount: int, players: int = 4):
        if players <= 0:
            await ctx.send("❌ You need at least 1 player to split loot with!")
            return
            
        split = amount / players
        await ctx.send(f"💸 Loot split! A **{amount:,.2f} Cr** payout split among {players} players equals **{split:,.2f} Cr** each.")

async def setup(bot):
    await bot.add_cog(PartyCog(bot))
