import logging

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)

HELP_MESSAGES = (
(
    "**DICEwithoutNumber Command Directory**\n"
    "**Sheets & Characters**\n"
    "`/importsheet` `!importsheet` `!uploadsheet` - Import from URL or attached CSV/TXT/JSON\n"
    "`/importjson` `!importjson` `!uploadjson` - Import JSON from URL or attachment\n"
    "`/sheet` `!sheet` `!s` `!sc` `!sf` - Show active sheet\n"
    "`/update` `!update` `!up` - Refresh active sheet\n"
    "`/sync` `!sync` - Sync active character source\n"
    "`/bind` `!bind` - Bind character to current channel\n"
    "`/portrait` `!portrait` - Set character portrait\n"
    "`/ship` `!ship` `/shiplist` `!shiplist` - Starship sheets\n"
    "`/threshold_wizard` `/swn` `/wwn` `/cwn` `/threshold` - Character generation\n\n"
    "**Dice & Combat**\n"
    "`/roll` `!roll` `!r` - Roll dice, like `1d20+5` or `3x 2d6`\n"
    "`target N` - Add a success check, like `!roll d20 target 13`\n"
    "`/gmroll` `!gmroll` `!gr` - Hidden/private roll\n"
    "`/multiroll` `!multiroll` - Roll one expression multiple times\n"
    "`/skill` `!skill` - Skill check from active sheet\n"
    "`/attack` `!attack` - Weapon attack from active sheet\n"
    "`/combathelp` `/ship_combat` `!ship_combat` `/hack_help` `!hack_help` - Rule helpers\n\n"
    "**Tracker & Map**\n"
    "`/tracker add` `!tracker add` - Add enemies\n"
    "`/tracker list` `!tracker list` - Show tracker\n"
    "`/tracker damage` `!tracker damage` - Apply damage\n"
    "`/tracker move` `!tracker move` - Move token\n"
    "`/tracker next` `!tracker next` - Advance turn\n"
    "`/tracker clear` `!tracker clear` - Clear tracker\n"
    "`/tracker map` `!tracker map` `/tracker controller` `!tracker controller` - Tactical map\n"
    "`/tracker ac/hide/condition/distance/grid/party` - More tracker tools\n"
    "`/importmap` `/map` `!map` - Map upload/link\n\n"
),
(
    "**World, Rules & Gear**\n"
    "`/weapon` `!weapon` `/armor` `!armor` `/gear` `!gear` - Equipment lookup\n"
    "`/shipinfo` `!shipinfo` `!si` `/foci` `!foci` `!focus` - Reference lookup\n"
    "`/rule` `!rule` - Search rules\n"
    "`/gen` `!gen` - Generate planet/NPC/corp/alien\n"
    "`/reaction` `/morale` `/oracle` `/plot` `/loot` `/weather` `/encounter` `/hazard` - GM tools\n\n"
    "**Campaign, Factions & Party**\n"
    "`/campaign start/join/leave/info` `!campaign start/join/leave/info`\n"
    "`/party info/set/add/split` `!party info/set/add/split`\n"
    "`/faction create/list/edit/attack` `!faction create/list/edit/attack`\n\n"
    "**Server Tools**\n"
    "`/channel role` `/channel setup` `/channel reactionrole` - Channel/reaction roles\n"
    "`!rr` `!role` `!lock` `/lock` - Prefix channel tools\n"
    "`/avatar` `!avatar` `/rename` `!rename` `!sync guild` `!sync global`\n"
    "`/backup` `/heartbeat` `!logs` `!payload` `!reload` - Owner/admin diagnostics\n\n"
    "**Start Here**\n"
    "`/starthere` `!starthere` `/swnhelp` `/wwnhelp` `/cwnhelp` - Quick guides\n"
    "`/help` `!help` `!wnhelp` - This directory"
)
)


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_help(self, ctx_or_interaction):
        try:
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(HELP_MESSAGES[0], ephemeral=True)
                for message in HELP_MESSAGES[1:]:
                    await ctx_or_interaction.followup.send(message, ephemeral=True)
            else:
                try:
                    for message in HELP_MESSAGES:
                        await ctx_or_interaction.author.send(message)
                    if ctx_or_interaction.guild:
                        await ctx_or_interaction.send("I've sent the help menu to your DMs!")
                except discord.Forbidden:
                    for message in HELP_MESSAGES:
                        await ctx_or_interaction.send(message)
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
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        locale = self.bot.db.get_setting(user_id, "language", "en")

        app_name = getattr(self.bot.web_service, "settings", {}).get("app_name", "DICEwithoutNumber")
        embed = discord.Embed(
            title=f"💖 Support {app_name}",
            description=f"{app_name} is free and built for the community. If you enjoy using it, consider supporting development with a tip!",
            color=discord.Color.from_rgb(88, 101, 242),
        )

        embed.set_thumbnail(url="http://dicewithoutnumber.duckdns.org/static/hero_premium.png")

        embed.add_field(
            name="☕ Support the Creator",
            value=(
                "Every contribution helps keep the server running and fuels the development of new features for SWN, WWN, and CWN.\n\n"
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
                "1. Surprise\n"
                "2. Initiative\n"
                "3. Setup Tracker\n"
                "4. Tactical Grid\n"
                "5. Take Turns\n"
                "6. Player Attacks\n"
                "7. Deal Damage\n\n"
                "On your turn, you can take One Main Action and One Move Action."
            ),
            color=discord.Color.dark_red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
