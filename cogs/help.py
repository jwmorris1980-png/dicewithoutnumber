import logging

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_help(self, ctx_or_interaction):
        try:
            embed = discord.Embed(
                title="DICEwithoutNumber Help",
                description=(
                    "Quick commands for rolls, characters, maps, and voice. "
                    "Use `/help` for the compact guide and `commands.md` for the full list."
                ),
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Character Sheets",
                value=(
                    "`/importsheet <url>` or attach `.csv`/`.txt`/`.json`\\n"
                    "`/importjson <url>` or attach `.json`\\n"
                    "`/sheet`, `/update`, `/sync`, `/bind`"
                ),
                inline=False,
            )

            embed.add_field(
                name="Dice & Combat",
                value=(
                    "`/roll`, `/gmroll`, `/multiroll`\\n"
                    "`/attack`, `/skill`\\n"
                    "Prefix forms also work with `!`"
                ),
                inline=False,
            )

            embed.add_field(
                name="Maps & Tools",
                value=(
                    "`/map`, `/tracker`, `/faction`, `/campaign`\\n"
                    "`/voice` for the voice remote\\n"
                    "`/avatar`, `/rename`, `!sync guild` for admin tasks"
                ),
                inline=False,
            )

            embed.set_footer(text="If you need the full command list, check commands.md or the website.")

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
                "Help is available with `/help` or `!help`.\\n"
                "Character import: `/importsheet <url>` or `!importsheet <url>`.\\n"
                "You can also attach a `.csv` or `.json` file to import a character."
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                target = ctx_or_interaction.followup if ctx_or_interaction.response.is_done() else ctx_or_interaction.response
                await target.send(f"{fallback}\\n\\nError: `{e}`", ephemeral=True)
            else:
                await ctx_or_interaction.send(f"{fallback}\\n\\nError: `{e}`")

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
            value=(
                "Every contribution helps keep the server running and fuels the development of new features for SWN, WWN, and CWN.\\n\\n"
                "🔗 **Leave a Tip:** [**ko-fi.com/loroman1211**](https://ko-fi.com/loroman1211)"
            ),
            inline=False,
        )

        embed.add_field(
            name="🌐 Visit the Website",
            value="Check out the full command list and features at [**dicewithoutnumber.duckdns.org**](http://dicewithoutnumber.duckdns.org/)",
            inline=False,
        )

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)

    @app_commands.command(name="combathelp", description="Show a cheat-sheet for Without Number combat actions.")
    async def combathelp(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚔️ Combat Actions Cheat-Sheet",
            description=(
                "1. Surprise\\n"
                "2. Initiative\\n"
                "3. Setup Tracker\\n"
                "4. Tactical Grid\\n"
                "5. Take Turns\\n"
                "6. Player Attacks\\n"
                "7. Deal Damage\\n\\n"
                "On your turn, you can take One Main Action and One Move Action."
            ),
            color=discord.Color.dark_red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
