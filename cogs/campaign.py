import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from services.permissions import is_gm

@app_commands.guild_only()
class CampaignCog(commands.GroupCog, group_name="campaign", description="Track campaign name, GM, and player status."):
    def __init__(self, bot):
        self.bot = bot
        self.campaign_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'campaigns')
        os.makedirs(self.campaign_dir, exist_ok=True)
        
    def get_guild_campaign(self, guild_id: int):
        """Loads a guild's active campaign from the database."""
        data = self.bot.db.get_campaign(guild_id)
        if data:
            return data
        return {
            "name": "Unnamed Campaign",
            "gm_id": None,
            "players": {}
        }
        
    def save_guild_campaign(self, guild_id: int, data: dict):
        """Saves a guild's campaign to the database."""
        self.bot.db.save_campaign(guild_id, data)

    @app_commands.command(name="start", description="Start a new campaign and become the GM.")
    @app_commands.describe(name="Name of your campaign")
    async def start(self, interaction: discord.Interaction, name: str):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_campaign(guild_id)
        
        # Check if campaign already has a GM and if current user is allowed to overwrite
        if data.get("gm_id") and data["gm_id"] != interaction.user.id:
            if not interaction.user.guild_permissions.administrator and not interaction.user.guild_permissions.manage_guild:
                # Check channel role too
                if not is_gm(interaction):
                    await interaction.response.send_message("❌ A campaign is already active. Only the current GM or a Server Admin can restart it.", ephemeral=True)
                    return

        data["name"] = name
        data["gm_id"] = interaction.user.id
        # Optional: clear players on a new start, or let them carry over?
        # Let's keep players for ease of use across arcs, unless manually cleared.
        
        self.save_guild_campaign(guild_id, data)
        await interaction.response.send_message(f"🎉 **{interaction.user.display_name}** has started the campaign: **{name}** as the GM!\nPlayers can now type `/campaign join`!")

    @app_commands.command(name="join", description="Join the active campaign using your active character sheet.")
    async def join(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_campaign(guild_id)
        
        if not data.get("name") or data["name"] == "Unnamed Campaign":
            await interaction.response.send_message("❌ There is no active campaign running on this server. A GM must `/campaign start` one!", ephemeral=True)
            return

        char_data = None
        try:
            cog = self.bot.get_cog("CharacterSheetCog")
            if cog:
                char_data = cog.load_character(interaction.user.id)
        except Exception:
            pass

        if not char_data:
            await interaction.response.send_message("❌ Please `!importsheet` and load a character before joining the campaign!", ephemeral=True)
            return

        user_id_str = str(interaction.user.id)
        hp_max = char_data.get('max_hp', char_data.get('hp', 1))
        
        data["players"][user_id_str] = {
            "char_name": char_data['name'],
            "player_name": interaction.user.display_name,
            "max_hp": hp_max,
            "current_hp": hp_max # Assume healthy, or could track live if needed
        }
        
        self.save_guild_campaign(guild_id, data)
        await interaction.response.send_message(f"✅ **{char_data['name']}** ({interaction.user.display_name}) has joined the campaign **{data['name']}**!")

    @app_commands.command(name="leave", description="Leave the active campaign.")
    async def leave(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_campaign(guild_id)
        
        user_id_str = str(interaction.user.id)
        if user_id_str in data["players"]:
            char_name = data["players"][user_id_str]["char_name"]
            del data["players"][user_id_str]
            self.save_guild_campaign(guild_id, data)
            await interaction.response.send_message(f"👋 **{char_name}** has left the campaign.")
        else:
            await interaction.response.send_message("❌ You are not currently in the campaign.", ephemeral=True)

    @app_commands.command(name="info", description="View the current campaign and player list.")
    async def info(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        data = self.get_guild_campaign(guild_id)
        
        if not data.get("name") or data["name"] == "Unnamed Campaign":
            await interaction.response.send_message("📝 No active campaign running.", ephemeral=True)
            return
            
        gm_user = self.bot.get_user(data["gm_id"])
        gm_name = gm_user.display_name if gm_user else "Unknown GM"
        
        embed = discord.Embed(title=f"🗺️ Campaign: {data['name']}", color=discord.Color.brand_green())
        embed.description = f"**GM:** {gm_name}\n\n**Players:**"
        
        if not data["players"]:
            embed.description += "\n*No players have joined yet.*"
        else:
            for uid, p in data["players"].items():
                embed.description += f"\n• **{p['char_name']}** ({p['player_name']}) - HP: {p['current_hp']}/{p['max_hp']}"
                
        await interaction.response.send_message(embed=embed)

    @commands.group(name="campaign", invoke_without_command=True, help="Manage the campaign. Subcommands: start, join, leave, info.")
    async def campaign_text(self, ctx):
        await ctx.send("Use `!campaign start <name>`, `!campaign join`, `!campaign leave`, or `!campaign info`.")

    @campaign_text.command(name="start", help="Start a new campaign.")
    async def c_start(self, ctx, *, name: str):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_campaign(guild_id)
        data["name"] = name
        data["gm_id"] = ctx.author.id
        self.save_guild_campaign(guild_id, data)
        await ctx.send(f"🎉 **{ctx.author.display_name}** has started the campaign: **{name}** as the GM!\nPlayers can now type `!campaign join`!")

    @campaign_text.command(name="join", help="Join the campaign with your active sheet.")
    async def c_join(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_campaign(guild_id)
        
        if not data.get("name") or data["name"] == "Unnamed Campaign":
            await ctx.send("❌ There is no active campaign running on this server. A GM must `!campaign start` one!")
            return

        char_data = None
        try:
            cog = self.bot.get_cog("CharacterSheetCog")
            if cog:
                char_data = cog.load_character(ctx.author.id)
        except Exception:
            pass

        if not char_data:
            await ctx.send("❌ Please `!importsheet` and load a character before joining the campaign!")
            return

        user_id_str = str(ctx.author.id)
        hp_max = char_data.get('max_hp', char_data.get('hp', 1))
        
        data["players"][user_id_str] = {
            "char_name": char_data['name'],
            "player_name": ctx.author.display_name,
            "max_hp": hp_max,
            "current_hp": hp_max
        }
        self.save_guild_campaign(guild_id, data)
        await ctx.send(f"✅ **{char_data['name']}** ({ctx.author.display_name}) has joined the campaign **{data['name']}**!")

    @campaign_text.command(name="leave", help="Leave the campaign.")
    async def c_leave(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_campaign(guild_id)
        user_id_str = str(ctx.author.id)
        if user_id_str in data["players"]:
            char_name = data["players"][user_id_str]["char_name"]
            del data["players"][user_id_str]
            self.save_guild_campaign(guild_id, data)
            await ctx.send(f"👋 **{char_name}** has left the campaign.")
        else:
            await ctx.send("❌ You are not currently in the campaign.")

    @campaign_text.command(name="info", help="View campaign details.")
    async def c_info(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        data = self.get_guild_campaign(guild_id)
        if not data.get("name") or data["name"] == "Unnamed Campaign":
            await ctx.send("📝 No active campaign running.")
            return
            
        gm_user = self.bot.get_user(data["gm_id"])
        gm_name = gm_user.display_name if gm_user else "Unknown GM"
        embed = discord.Embed(title=f"🗺️ Campaign: {data['name']}", color=discord.Color.brand_green())
        embed.description = f"**GM:** {gm_name}\n\n**Players:**"
        if not data["players"]:
             embed.description += "\n*No players have joined yet.*"
        else:
             for uid, p in data["players"].items():
                 embed.description += f"\n• **{p['char_name']}** ({p['player_name']}) - HP: {p['current_hp']}/{p['max_hp']}"
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CampaignCog(bot))
