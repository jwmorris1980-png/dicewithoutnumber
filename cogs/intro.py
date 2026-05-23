import discord
from discord import app_commands
from discord.ext import commands

class IntroCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_intro(self, ctx_or_interaction, system_code: str):
        # Determine locale
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        locale = self.bot.db.get_setting(user_id, "language", "en")
        
        system_code = system_code.lower()
        if system_code not in ["swn", "wwn", "cwn"]:
            system_code = "swn" # Fallback

        loc = self.bot.localizer
        
        embed = discord.Embed(
            title=loc.translate(f"intro.{system_code}.title", locale),
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url="http://147.182.248.196:8080/hero.png")

        embed.add_field(
            name=loc.translate(f"intro.{system_code}.step1_title", locale),
            value=loc.translate(f"intro.{system_code}.step1_desc", locale),
            inline=False
        )
        embed.add_field(
            name=loc.translate(f"intro.{system_code}.step2_title", locale),
            value=loc.translate(f"intro.{system_code}.step2_desc", locale),
            inline=False
        )
        embed.add_field(
            name=loc.translate(f"intro.{system_code}.step3_title", locale),
            value=loc.translate(f"intro.{system_code}.step3_desc", locale),
            inline=False
        )

        embed.set_footer(text=loc.translate("intro.footer", locale))

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)

    @app_commands.command(name="starthere", description="Quick start guide for SWN, WWN, or CWN.")
    @app_commands.choices(system=[
        app_commands.Choice(name="SWN", value="SWN"),
        app_commands.Choice(name="WWN", value="WWN"),
        app_commands.Choice(name="CWN", value="CWN")
    ])
    async def starthere_slash(self, interaction: discord.Interaction, system: str):
        await self._send_intro(interaction, system)

    # Shorthand aliases for slash commands
    @app_commands.command(name="swnhelp", description="Quick start guide for Stars Without Number.")
    async def swnhelp_slash(self, interaction: discord.Interaction):
        await self._send_intro(interaction, "SWN")

    @app_commands.command(name="wwnhelp", description="Quick start guide for Worlds Without Number.")
    async def wwnhelp_slash(self, interaction: discord.Interaction):
        await self._send_intro(interaction, "WWN")

    @app_commands.command(name="cwnhelp", description="Quick start guide for Cities Without Number.")
    async def cwnhelp_slash(self, interaction: discord.Interaction):
        await self._send_intro(interaction, "CWN")

    @app_commands.command(name="starthereswn", description="Quick start guide for Stars Without Number.")
    async def starthereswn_slash(self, interaction: discord.Interaction):
        await self._send_intro(interaction, "SWN")

    @app_commands.command(name="startherewwn", description="Quick start guide for Worlds Without Number.")
    async def startherewwn_slash(self, interaction: discord.Interaction):
        await self._send_intro(interaction, "WWN")

    @app_commands.command(name="startherecwn", description="Quick start guide for Cities Without Number.")
    async def startherecwn_slash(self, interaction: discord.Interaction):
        await self._send_intro(interaction, "CWN")

    # Prefix aliases
    @commands.command(name="starthere", aliases=["swnhelp", "wwnhelp", "cwnhelp", "sintro", "wintro", "cintro", "starthereswn", "startherewwn", "startherecwn"], help="Get a quick start guide. Usage: !starthere [SWN|WWN|CWN] or !swnhelp, !wwnhelp, etc.")
    async def starthere_text(self, ctx, system: str = None):
        if system is None:
            # Try to detect system from command alias
            invoked_with = ctx.invoked_with.upper()
            if "SWN" in invoked_with or invoked_with.startswith("S"):
                system = "SWN"
            elif "WWN" in invoked_with or invoked_with.startswith("W"):
                system = "WWN"
            elif "CWN" in invoked_with or invoked_with.startswith("C"):
                system = "CWN"
            else:
                system = "SWN" # Default
        
        if system.upper() not in ["SWN", "WWN", "CWN"]:
            await ctx.send("⚠️ Please specify a system: SWN, WWN, or CWN. (e.g. `!starthere WWN`)")
            return
        await self._send_intro(ctx, system)

async def setup(bot):
    await bot.add_cog(IntroCog(bot))
