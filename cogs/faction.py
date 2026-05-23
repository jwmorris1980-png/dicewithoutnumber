import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
from services.permissions import is_gm_check

@app_commands.guild_only()
class FactionCog(commands.GroupCog, group_name="faction", description="Manage global campaign factions and their assets."):
    def __init__(self, bot):
        self.bot = bot
        self.faction_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'factions')
        os.makedirs(self.faction_dir, exist_ok=True)
        
    def get_guild_factions(self, guild_id: int):
        file_path = os.path.join(self.faction_dir, f"{guild_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
        
    def save_guild_factions(self, guild_id: int, data: dict):
        file_path = os.path.join(self.faction_dir, f"{guild_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    @app_commands.command(name="create", description="Track a new Faction.")
    @app_commands.describe(name="Name of faction", hp="Hit points", wealth="Wealth rating", bases="Bases rating")
    @is_gm_check()
    async def create(self, interaction: discord.Interaction, name: str, hp: int = 10, wealth: int = 0, bases: int = 0):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_factions(guild_id)
        
        name_lower = name.lower()
        if name_lower in data:
            await interaction.response.send_message(f"❌ Faction '{name}' already exists.")
            return
            
        data[name_lower] = {
            "name": name,
            "hp": hp,
            "wealth": wealth,
            "bases": bases
        }
        
        self.save_guild_factions(guild_id, data)
        await interaction.response.send_message(f"✅ Created Faction **{name}** (HP: {hp}, Wealth: {wealth}, Bases: {bases})")

    @app_commands.command(name="list", description="List all tracked factions.")
    async def list_factions(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_factions(guild_id)
        
        if not data:
            await interaction.response.send_message("No factions are currently tracked. Use `/faction create`.")
            return
            
        embed = discord.Embed(title="🌐 Faction Tracker", color=discord.Color.dark_grey())
        desc = ""
        for k, f in data.items():
            desc += f"**{f['name']}** - HP: {f['hp']} | Wealth: {f['wealth']} | Bases: {f['bases']}\n"
            
        embed.description = desc
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="edit", description="Modify a faction's attributes.")
    @app_commands.choices(stat=[
        app_commands.Choice(name="HP", value="hp"),
        app_commands.Choice(name="Wealth", value="wealth"),
        app_commands.Choice(name="Bases", value="bases")
    ])
    @is_gm_check()
    async def edit(self, interaction: discord.Interaction, name: str, stat: str, value: int):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_factions(guild_id)
        
        name_lower = name.lower()
        if name_lower not in data:
            await interaction.response.send_message(f"❌ Faction '{name}' not found.")
            return
            
        data[name_lower][stat] = value
        self.save_guild_factions(guild_id, data)
        await interaction.response.send_message(f"✅ Set **{data[name_lower]['name']}**'s {stat.upper()} to {value}.")

    @app_commands.command(name="attack", description="Roll a fast asset attack (1d10 + stat vs 1d10 + stat).")
    async def attack(self, interaction: discord.Interaction, attacker_stat: int, defender_stat: int):
        atk_roll = random.randint(1, 10)
        def_roll = random.randint(1, 10)
        
        atk_total = atk_roll + attacker_stat
        def_total = def_roll + defender_stat
        
        embed = discord.Embed(title="💥 Faction Attack", color=discord.Color.red())
        
        if atk_total >= def_total:
            embed.color = discord.Color.green()
            result = "The Attack **SUCCEEDS!** The defending asset is destroyed or damaged."
        else:
            embed.color = discord.Color.light_grey()
            result = "The Attack **FAILS!** The defender holds their ground. Attacker asset takes damage/destroyed counterattack."
            
        embed.add_field(name="Attacker", value=f"Roll: {atk_roll}\nStat: {attacker_stat}\n**Total: {atk_total}**", inline=True)
        embed.add_field(name="Defender", value=f"Roll: {def_roll}\nStat: {defender_stat}\n**Total: {def_total}**", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @commands.group(name="faction", invoke_without_command=True, help="Manage Factions. Subcommands: create, list, edit, attack.")
    async def faction_text(self, ctx):
        await ctx.send("Use `!faction create`, `!faction list`, `!faction edit`, or `!faction attack`.")

    @faction_text.command(name="create")
    async def f_create(self, ctx, name: str, hp: int = 10, wealth: int = 0, bases: int = 0):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_factions(guild_id)
        
        if name.lower() in data:
            await ctx.send(f"❌ Faction '{name}' already exists.")
            return
            
        data[name.lower()] = {"name": name, "hp": hp, "wealth": wealth, "bases": bases}
        self.save_guild_factions(guild_id, data)
        await ctx.send(f"✅ Created Faction **{name}** (HP: {hp}, Wealth: {wealth}, Bases: {bases})")

    @faction_text.command(name="list")
    async def f_list(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_factions(guild_id)
        if not data:
            await ctx.send("No factions are currently tracked. Use `!faction create`.")
            return
        embed = discord.Embed(title="🌐 Faction Tracker", color=discord.Color.dark_grey())
        embed.description = "".join([f"**{f['name']}** - HP: {f['hp']} | Wealth: {f['wealth']} | Bases: {f['bases']}\n" for f in data.values()])
        await ctx.send(embed=embed)

    @faction_text.command(name="edit")
    async def f_edit(self, ctx, name: str, stat: str, value: int):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_factions(guild_id)
        
        if name.lower() not in data:
            await ctx.send(f"❌ Faction '{name}' not found.")
            return
        if stat.lower() not in ['hp', 'wealth', 'bases']:
            await ctx.send("❌ Stat must be 'hp', 'wealth', or 'bases'.")
            return
            
        data[name.lower()][stat.lower()] = value
        self.save_guild_factions(guild_id, data)
        await ctx.send(f"✅ Set **{data[name.lower()]['name']}**'s {stat.upper()} to {value}.")

    @faction_text.command(name="attack")
    async def f_attack(self, ctx, attacker_stat: int, defender_stat: int):
        atk_roll = random.randint(1, 10)
        def_roll = random.randint(1, 10)
        atk_total = atk_roll + attacker_stat
        def_total = def_roll + defender_stat
        
        embed = discord.Embed(title="💥 Faction Attack", color=discord.Color.red())
        if atk_total >= def_total:
            embed.color = discord.Color.green()
            result = "The Attack **SUCCEEDS!** The defending asset is destroyed or damaged."
        else:
            embed.color = discord.Color.light_grey()
            result = "The Attack **FAILS!** The defender holds their ground. Attacker asset takes damage/destroyed counterattack."
            
        embed.add_field(name="Attacker", value=f"Roll: {atk_roll}\nStat: {attacker_stat}\n**Total: {atk_total}**", inline=True)
        embed.add_field(name="Defender", value=f"Roll: {def_roll}\nStat: {defender_stat}\n**Total: {def_total}**", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FactionCog(bot))
