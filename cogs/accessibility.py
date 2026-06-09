import discord
from discord import app_commands
from discord.ext import commands


ACCESSIBILITY_MODES = {
    "standard": "Standard responses with normal formatting.",
    "simple": "Shorter, screen-reader-friendly responses with less decoration.",
    "private": "Prefer private responses where Discord supports them.",
}


class QuickMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    async def _tip(self, interaction, text):
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(label="Dice", style=discord.ButtonStyle.primary)
    async def dice(self, interaction, button):
        await self._tip(interaction, "Say `roll one d20`, `roll 2d6 target 8`, or use `/roll`.")

    @discord.ui.button(label="Characters", style=discord.ButtonStyle.primary)
    async def characters(self, interaction, button):
        await self._tip(interaction, "Use `importsheet <link>`, then say `sheet`, `bind`, or `attack`.")

    @discord.ui.button(label="Maps", style=discord.ButtonStyle.primary)
    async def maps(self, interaction, button):
        await self._tip(interaction, "Say `map` for the interactive map, or use `/tracker map` for combat.")

    @discord.ui.button(label="Help", style=discord.ButtonStyle.secondary)
    async def help(self, interaction, button):
        await self._tip(interaction, "Say `help`, `tutorial`, or `setupguide` for the right level of guidance.")

    @discord.ui.button(label="Support", style=discord.ButtonStyle.danger)
    async def support(self, interaction, button):
        await self._tip(interaction, "Say `ticket <what happened>` or use `/ticket` to contact the bot owner.")


class AccessibilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send(self, target, message, *, ephemeral=True):
        if isinstance(target, discord.Interaction):
            await target.response.send_message(message, ephemeral=ephemeral)
        else:
            await target.send(message)

    async def _set_accessibility(self, target, mode):
        user = target.user if isinstance(target, discord.Interaction) else target.author
        mode = (mode or "show").lower()
        if mode == "show":
            current = self.bot.db.get_setting(user.id, "accessibility_mode", "standard")
            await self._send(target, f"Your accessibility mode is **{current}**. {ACCESSIBILITY_MODES[current]}")
            return
        if mode not in ACCESSIBILITY_MODES:
            await self._send(target, "Choose `standard`, `simple`, or `private`.")
            return
        self.bot.db.set_setting(user.id, "accessibility_mode", mode)
        await self._send(target, f"Accessibility mode set to **{mode}**. {ACCESSIBILITY_MODES[mode]}")

    @app_commands.command(name="accessibility", description="Choose simpler or more private bot responses.")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Show current setting", value="show"),
        app_commands.Choice(name="Standard", value="standard"),
        app_commands.Choice(name="Simple / screen reader friendly", value="simple"),
        app_commands.Choice(name="Prefer private replies", value="private"),
    ])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def accessibility_slash(self, interaction: discord.Interaction, mode: str = "show"):
        await self._set_accessibility(interaction, mode)

    @commands.command(name="accessibility", aliases=["access"])
    async def accessibility_prefix(self, ctx, mode: str = "show"):
        await self._set_accessibility(ctx, mode)

    async def _tutorial(self, target):
        await self._send(
            target,
            "**DICEwithoutNumber Quick Tutorial**\n"
            "1. Try `roll one d20` - commands work without `/` or `!` when the bot is installed here.\n"
            "2. Use `importsheet <public Google Sheet link>` to load a character.\n"
            "3. Say `sheet` to view the active character, then `bind` to remember it in this channel.\n"
            "4. Say `map` or use `/tracker map` for interactive tactical maps.\n"
            "5. Say `help` for every command or `ticket <problem>` if something breaks.",
        )

    @app_commands.command(name="tutorial", description="Learn the bot with a short voice-friendly walkthrough.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def tutorial_slash(self, interaction: discord.Interaction):
        await self._tutorial(interaction)

    @commands.command(name="tutorial")
    async def tutorial_prefix(self, ctx):
        await self._tutorial(ctx)

    async def _setupguide(self, target):
        await self._send(
            target,
            "**Server Setup Guide**\n"
            "1. Give the bot View Channels, Send Messages, Read Message History, Embed Links, Attach Files, and Use Slash Commands.\n"
            "2. Test with `health`, `roll one d20`, and `help`.\n"
            "3. Start a campaign with `/campaign start`, then import and bind character sheets.\n"
            "4. Open tactical play with `map` or `/tracker map`.\n"
            "5. Use `/heartbeat` and `/backup` for owner diagnostics and backups.\n"
            "If anything fails, use `ticket <what happened>`.",
        )

    @app_commands.command(name="setupguide", description="Show the recommended server setup and permission checklist.")
    async def setupguide_slash(self, interaction: discord.Interaction):
        await self._setupguide(interaction)

    @commands.command(name="setupguide", aliases=["setuphelp"])
    async def setupguide_prefix(self, ctx):
        await self._setupguide(ctx)

    async def _menu(self, target):
        text = "**Quick Command Menu**\nChoose what you want to do, or say `tutorial` for a walkthrough."
        if isinstance(target, discord.Interaction):
            await target.response.send_message(text, view=QuickMenuView(), ephemeral=True)
        else:
            await target.send(text, view=QuickMenuView())

    @app_commands.command(name="menu", description="Open a button-based menu for common bot features.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def menu_slash(self, interaction: discord.Interaction):
        await self._menu(interaction)

    @commands.command(name="menu")
    async def menu_prefix(self, ctx):
        await self._menu(ctx)


async def setup(bot):
    await bot.add_cog(AccessibilityCog(bot))
