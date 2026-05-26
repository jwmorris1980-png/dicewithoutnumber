import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_help(self, ctx_or_interaction):
        try:
            user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
            locale = self.bot.db.get_setting(user_id, "language", "en")
            loc = self.bot.localizer

            embed = discord.Embed(
                title=loc.translate("help.title", locale),
                description=loc.translate("help.description", locale),
                color=discord.Color.blue()
            )

            sections = [
                ("help.char_imports_title", "help.char_imports_body"),
                ("help.char_mgmt_title", "help.char_mgmt_body"),
                ("help.rolling_title", "help.rolling_body"),
                ("help.tools_title", "help.tools_body"),
                ("help.sandbox_title", "help.sandbox_body"),
                ("help.tracker_title", "help.tracker_body"),
                ("help.faction_title", "help.faction_body"),
                ("help.storyteller_title", "help.storyteller_body"),
                ("help.party_title", "help.party_body"),
                ("help.campaign_title", "help.campaign_body"),
                ("help.voice_title", "help.voice_body"),
                ("help.channel_role_title", "help.channel_role_body"),
            ]

            for title_key, body_key in sections:
                embed.add_field(
                    name=loc.translate(title_key, locale),
                    value=loc.translate(body_key, locale),
                    inline=False,
                )

            embed.add_field(
                name="Server Admin",
                value=(
                    "`/avatar` - Change the bot's picture. Type `/avatar`, click image, upload a file.\n"
                    "`!avatar` - Same thing via prefix: attach image to the `!avatar` message.\n"
                    "`/rename <server_id> <name>` - Change bot display name for this server.\n"
                    "`!sync guild` - Re-sync slash commands after any update."
                ),
                inline=False,
            )

            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                try:
                    await ctx_or_interaction.author.send(embed=embed)
                    if ctx_or_interaction.guild:
                        await ctx_or_interaction.send("I've sent the help menu to your DMs!")
                except discord.Forbidden:
                    await ctx_or_interaction.send("I couldn't DM you the help menu. Please open your DMs or use `/help`.")
        except Exception as e:
            logger.exception("Help command failed")
            fallback = (
                "Help is available with `/help` or `!help`.\n"
                "Character import: `/importsheet <url>` or `!importsheet <url>`.\n"
                "You can also attach a `.csv` or `.json` file to import a character."
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                target = ctx_or_interaction.followup if ctx_or_interaction.response.is_done() else ctx_or_interaction.response
                await target.send(f"{fallback}\n\nError: `{e}`", ephemeral=True)
            else:
                await ctx_or_interaction.send(f"{fallback}\n\nError: `{e}`")

    @app_commands.command(name="help", description="Show how to use the Without Number bot.")
    async def help_slash(self, interaction: discord.Interaction):
        await self._send_help(interaction)

    @commands.command(name="help", aliases=["wnhelp"], help="Show how to use the Without Number bot.")
    async def help_text(self, ctx):
        await self._send_help(ctx)

    @app_commands.command(name="pro", description="View premium features and support the bot.")
    async def pro_slash(self, interaction: discord.Interaction):
        await self._send_pro(interaction)

    @commands.group(invoke_without_command=True, help="Support the bot and unlock premium features.")
    async def pro(self, ctx):
        await self._send_pro(ctx)

    async def _send_pro(self, ctx_or_interaction):
        # Determine locale
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        locale = self.bot.db.get_setting(user_id, "language", "en")
        
        app_name = getattr(self.bot.web_service, 'settings', {}).get('app_name', 'DICEwithoutNumber')
        embed = discord.Embed(
            title=f"💖 Support {app_name}",
            description=f"{app_name} is free and built for the community. If you enjoy using it, consider supporting development with a tip!",
            color=discord.Color.from_rgb(88, 101, 242)
        )
        
        embed.set_thumbnail(url="http://dicewithoutnumber.duckdns.org/static/hero_premium.png")
        
        embed.add_field(
            name="☕ Support the Creator",
            value="Every contribution helps keep the server running and fuels the development of new features for SWN, WWN, and CWN.\n\n"
                  "🔗 **Leave a Tip:** [**ko-fi.com/loroman1211**](https://ko-fi.com/loroman1211)",
            inline=False
        )
        
        embed.add_field(
            name="🌐 Visit the Website",
            value="Check out the full command list and features at [**dicewithoutnumber.duckdns.org**](http://dicewithoutnumber.duckdns.org/)",
            inline=False
        )
        
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)

    @app_commands.command(name="combathelp", description="Show a cheat-sheet for Without Number combat actions.")
    async def combathelp(self, interaction: discord.Interaction):
        # We could localize this too
        embed = discord.Embed(
            title="⚔️ Combat Actions Cheat-Sheet", 
            description="**Order of Combat:**\n"
                        "1. **Surprise:** Determine if any side is surprised (they lose their first turn).\n"
                        "2. **Initiative:** Roll Initiative (`/initiative`). Ties go to the PCs.\n"
                        "3. **Setup Tracker:** GM adds enemies via `/tracker add Goblin 10 12 5` (Adds 5 goblins).\n"
                        "4. **Tactical Grid:** Use `/tracker controller` for a native button-based interactive map!\n"
                        "5. **Take Turns:** Order goes highest to lowest. GM uses `/tracker next`.\n"
                        "6. **Player Attacks:** Player types `/attack` to roll 1d20 + Attack Bonus (+ Damage if hit!).\n"
                        "7. **Deal Damage:** GM types `/tracker damage <id> <amount>`.\n\n"
                        "On your turn, you can take **One Main Action** and **One Move Action**. You can also take any number of On Turn actions.",
            color=discord.Color.dark_red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
