import logging
import os
import asyncio

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-category embed data
# ---------------------------------------------------------------------------

CATEGORIES = {
    "sheets": {
        "label": "Sheets & Characters",
        "emoji": "📋",
        "color": discord.Color.blue(),
        "fields": [
            ("Import", (
                "Paste a Google Sheet link or attach CSV/TXT/JSON — auto-imports\n"
                "`/importsheet` `!importsheet` — Manual import\n"
                "`/importjson` `!importjson` `!uploadjson` — Import JSON from URL or attachment"
            )),
            ("View & Sync", (
                "`/sheet` `!sheet` `!s` `!sc` `!sf` — Show active sheet\n"
                "`/update` `!update` `!up` — Refresh active sheet\n"
                "`/sync` `!sync` — Sync character source\n"
                "`/bind` `!bind` — Bind character to this channel\n"
                "`/portrait` `!portrait` — Set character portrait"
            )),
            ("Ships & Generation", (
                "`/ship` `!ship` `/shiplist` `!shiplist` — Starship sheets\n"
                "`/threshold_wizard` `/swn` `/wwn` `/cwn` `/threshold` — Character generation"
            )),
        ],
    },
    "dice": {
        "label": "Dice & Combat",
        "emoji": "🎲",
        "color": discord.Color.red(),
        "fields": [
            ("Rolling", (
                "`/roll` `!roll` `!r` — Roll dice, e.g. `1d20+5` or `3x 2d6`\n"
                "`7x d20` or `d20 7 times` — Repeated rolls listed in order\n"
                "`target N` / `target low N` — Success check, e.g. `!roll d20 target low 13`\n"
                "`/gmroll` `!gmroll` `!gr` — Hidden/private roll\n"
                "`/multiroll` `!multiroll` `!rr` — Repeat one expression, e.g. `!rr 7 1d20`"
            )),
            ("Sheet-Based Actions", (
                "`/skill` `!skill` — Exact skill check from active sheet; never guesses missing skills\n"
                "`/attack` `!attack` — Weapon attack from active sheet"
            )),
            ("Rule Helpers", (
                "`/combathelp` — Combat cheat-sheet\n"
                "`/ship_combat` `!ship_combat` — Starship combat guide\n"
                "`/hack_help` `!hack_help` — Hacking rules"
            )),
        ],
    },
    "tracker": {
        "label": "Tracker & Map",
        "emoji": "🗺️",
        "color": discord.Color.green(),
        "fields": [
            ("GM Mode Setup", (
                "`game master mode` — Voice/text wizard, uses server sheets\n"
                "Say `skip` during setup to omit any section\n"
                "`/gmmode` — Fully hidden one-form setup"
            )),
            ("Tracker Commands", (
                "`/tracker add` — Add enemies\n"
                "`/tracker list` — Show tracker\n"
                "`/tracker damage` — Apply damage\n"
                "`/tracker move` — Move token\n"
                "`/tracker next` — Advance turn\n"
                "`/tracker clear` — Clear tracker\n"
                "`/tracker ac` `/tracker hide` `/tracker condition` `/tracker distance` `/tracker grid` `/tracker party` — Extra tools"
            )),
            ("Map", (
                "`/tracker map` `!tracker map` — Open tactical map\n"
                "`/tracker controller` `!tracker controller` — Map controller\n"
                "`/importmap` `/map` `!map` — Upload or link a map"
            )),
        ],
    },
    "assets": {
        "label": "Free Image Library",
        "emoji": "🖼️",
        "color": discord.Color.teal(),
        "fields": [
            ("Maps", (
                "`/maplibrary [query]` `!findmap [query]` — Search trusted free RPG maps\n"
                "e.g. `/maplibrary space station` or `/maplibrary ruins`\n"
                "`find map forest` — Expands into RPG terms like battlemap, VTT, and encounter"
            )),
            ("Portraits", (
                "`/portraitlibrary [query]` `!findportrait [query]` — Search free portraits\n"
                "e.g. `/portraitlibrary psychic female` or `/portraitlibrary corporate npc`\n"
                "`find portrait operative` — Natural-language shortcut"
            )),
            ("Random & Admin", (
                "`/randomimage [type] [system]` — Random free image (SWN/CWN/WWN)\n"
                "`/addimage` — Admin: add a new free image to the catalog\n"
                "All images link to the original artist with full attribution."
            )),
        ],
    },
    "world": {
        "label": "World, Rules & Gear",
        "emoji": "📖",
        "color": discord.Color.gold(),
        "fields": [
            ("Equipment Lookup", (
                "`/weapon` `!weapon` — Weapon stats\n"
                "`/armor` `!armor` — Armour stats\n"
                "`/gear` `!gear` — General equipment\n"
                "`/shipinfo` `!shipinfo` `!si` — Ship stats\n"
                "`/foci` `!foci` `!focus` — Focus reference"
            )),
            ("Rules & Generation", (
                "`/rule` `!rule` — Search rules index\n"
                "`/gen` `!gen` — Generate planet/NPC/corp/alien"
            )),
            ("GM Tools", (
                "`/reaction` `/morale` `/oracle` `/plot` `/loot`\n"
                "`/weather` `/encounter` `/hazard` — Random GM tables"
            )),
        ],
    },
    "voice": {
        "label": "Voice & Accessibility",
        "emoji": "🎙️",
        "color": discord.Color.purple(),
        "fields": [
            ("No-Prefix Commands", (
                "`roll one d6`, `sheet`, `help` — Works without `/` or `!`\n"
                "A no-prefix command must start with the exact command name on one line\n"
                "`accessibility` — Switch between standard, simple, or private responses"
            )),
            ("Features Toggle", (
                "`/features` `!features` — Turn optional features on/off\n"
                "`ignore me` or `features off bot` — Bot ignores you completely\n"
                "`listen to me` or `/features on bot` — Re-enable the bot for yourself\n"
                "`features off voice` / `features off sheets` — Disable sub-systems"
            )),
            ("Navigation", (
                "`menu` / `open menu` — Button-based quick menu\n"
                "`tutorial` — Guided walkthrough\n"
                "`setupguide` — Server setup checklist\n"
                "`/voicehelp` — Voice-friendly tips and supported phrases\n"
                "`/up` `/down` `/catchup` — Browse recent messages without scrolling\n"
                "`/voice roll one d6` — Natural speech with personal install"
            )),
        ],
    },
    "campaign": {
        "label": "Campaign, Party & Factions",
        "emoji": "⚔️",
        "color": discord.Color.orange(),
        "fields": [
            ("Campaign", (
                "`/campaign start` `/campaign join` `/campaign leave` `/campaign info`\n"
                "`!campaign start/join/leave/info`"
            )),
            ("Party", (
                "`/party info` `/party set` `/party add` `/party split`\n"
                "`!party info/set/add/split`"
            )),
            ("Factions", (
                "`/faction create` `/faction list` `/faction edit` `/faction attack`\n"
                "`!faction create/list/edit/attack`"
            )),
            ("Polls", (
                "`/poll` `!poll` — Yes/no or multiple-choice polls\n"
                '`!poll "Question?" "Choice A" "Choice B"` — Prefix poll with quoted choices'
            )),
        ],
    },
    "server": {
        "label": "Server Tools & Support",
        "emoji": "🔧",
        "color": discord.Color.greyple(),
        "fields": [
            ("Channel & Roles", (
                "`/channel role` `/channel setup` `/channel reactionrole` — Role assignment\n"
                "`!rrrole` `!role` `!lock` `/lock` — Prefix channel tools\n"
                "`/avatar` `!avatar` `/rename` `!rename`"
            )),
            ("Admin / Owner", (
                "`!botsync guild` `!botsync global` — Sync slash commands\n"
                "`/backup` `/heartbeat` `!logs` `!payload` `!reload` — Diagnostics\n"
                "`/errors` — View persisted runtime errors"
            )),
            ("Getting Help", (
                "`/starthere` `!starthere` — Quick start guide\n"
                "`/swnhelp` `/wwnhelp` `/cwnhelp` — Game-specific guides\n"
                "`/ticket` `!ticket` — Open a support ticket\n"
                "`/tickets` `/ticketview` `/ticketreply` `/ticketclose` — Ticket management"
            )),
        ],
    },
}

# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def _category_embed(key: str) -> discord.Embed:
    cat = CATEGORIES[key]
    embed = discord.Embed(
        title=f"{cat['emoji']}  {cat['label']}",
        color=cat["color"],
    )
    for name, value in cat["fields"]:
        embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text="DICEwithoutNumber • /help to return to the menu")
    return embed


def _index_embed() -> discord.Embed:
    embed = discord.Embed(
        title="DICEwithoutNumber — Help",
        description=(
            "Free, open-source, accessibility-focused play tools for SWN, CWN, and WWN.\n\n"
            "**Pick a category below** to see its commands.\n"
            "All responses are private — only you can see them."
        ),
        color=discord.Color.blurple(),
    )
    for key, cat in CATEGORIES.items():
        embed.add_field(
            name=f"{cat['emoji']} {cat['label']}",
            value="\u200b",  # zero-width space keeps columns tidy
            inline=True,
        )
    embed.set_footer(text="DICEwithoutNumber • type /help any time")
    return embed


class CategoryButton(discord.ui.Button):
    def __init__(self, key: str, session=None):
        cat = CATEGORIES[key]
        super().__init__(
            label=cat["label"],
            emoji=cat["emoji"],
            style=discord.ButtonStyle.secondary,
            custom_id=f"help_{key}",
        )
        self.key = key
        self.session = session

    async def callback(self, interaction: discord.Interaction):
        if self.session:
            self.session.touch()
        await interaction.response.edit_message(
            embed=_category_embed(self.key),
            view=CategoryDetailView(self.key, session=self.session),
        )


class BackButton(discord.ui.Button):
    def __init__(self, session=None):
        super().__init__(label="← Back to menu", style=discord.ButtonStyle.primary)
        self.session = session

    async def callback(self, interaction: discord.Interaction):
        if self.session:
            self.session.touch()
        await interaction.response.edit_message(
            embed=_index_embed(),
            view=HelpIndexView(session=self.session),
        )


class HelpIndexView(discord.ui.View):
    def __init__(self, session=None):
        super().__init__(timeout=300)
        self.session = session
        for key in CATEGORIES:
            self.add_item(CategoryButton(key, session=session))


class CategoryDetailView(discord.ui.View):
    def __init__(self, active_key: str, session=None):
        super().__init__(timeout=300)
        self.session = session
        self.add_item(BackButton(session=session))
        for key in CATEGORIES:
            btn = CategoryButton(key, session=session)
            if key == active_key:
                btn.style = discord.ButtonStyle.primary
            self.add_item(btn)


class TemporaryHelpSession:
    def __init__(self, idle_seconds=60):
        self.idle_seconds = idle_seconds
        self.message = None
        self._generation = 0
        self._task = None

    def touch(self):
        self._generation += 1
        generation = self._generation
        if self._task:
            self._task.cancel()
        self._task = asyncio.create_task(self._delete_after_idle(generation))

    async def _delete_after_idle(self, generation):
        try:
            await asyncio.sleep(self.idle_seconds)
            if generation == self._generation and self.message:
                await self.message.delete()
        except (asyncio.CancelledError, discord.Forbidden, discord.NotFound):
            pass


class PrivateHelpLauncher(discord.ui.View):
    def __init__(self, requester_id: int):
        super().__init__(timeout=120)
        self.requester_id = requester_id

    @discord.ui.button(label="Open private help", style=discord.ButtonStyle.primary)
    async def open_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "Use `/help` to open your own private help menu.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=_index_embed(),
            view=HelpIndexView(),
            ephemeral=True,
        )


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _use_private_launcher(ctx) -> bool:
        test_guild_id = os.getenv("TEST_GUILD_ID", "").strip()
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        return bool(test_guild_id and str(guild_id) == test_guild_id)

    async def _send_help(self, ctx_or_interaction):
        try:
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(
                    embed=_index_embed(),
                    view=HelpIndexView(),
                    ephemeral=True,
                )
            else:
                if not self._use_private_launcher(ctx_or_interaction):
                    try:
                        await ctx_or_interaction.author.send(
                            embed=_index_embed(),
                            view=HelpIndexView(),
                        )
                        if ctx_or_interaction.guild:
                            await ctx_or_interaction.send("Help menu sent to your DMs!")
                    except discord.Forbidden:
                        await ctx_or_interaction.send(
                            embed=_index_embed(),
                            view=HelpIndexView(),
                        )
                    return
                # Text and spoken commands cannot be ephemeral. Show the full
                # embed in-channel briefly, then remove it automatically.
                try:
                    await ctx_or_interaction.message.delete()
                except (discord.Forbidden, discord.NotFound, AttributeError):
                    pass
                session = TemporaryHelpSession(idle_seconds=60)
                session.message = await ctx_or_interaction.send(
                    embed=_index_embed(),
                    view=HelpIndexView(session=session),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                session.touch()
        except Exception as e:
            logger.exception("Help command failed")
            fallback = (
                "Help is available with `/help` or `!help`.\n"
                "Character import: `/importsheet <url>` or `!importsheet <url>`.\n"
                "You can also attach a `.csv` or `.json` file to import a character."
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                target = (
                    ctx_or_interaction.followup
                    if ctx_or_interaction.response.is_done()
                    else ctx_or_interaction.response
                )
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
