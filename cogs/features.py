import re

import discord
from discord import app_commands
from discord.ext import commands


FEATURES = {
    "bot": ("all bot interactions", "bot_interactions"),
    "voice": ("voice/no-prefix commands", "voice_commands"),
    "sheets": ("automatic sheet imports", "automatic_sheet_imports"),
}


class FeaturesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _target_id(self, target, scope):
        if scope == "server" and target.guild:
            return f"guild:{target.guild.id}"
        user = target.user if isinstance(target, discord.Interaction) else target.author
        return f"user:{user.id}"

    def is_enabled(self, feature, message):
        _, key = FEATURES[feature]
        user_value = self.bot.db.get_setting(f"user:{message.author.id}", f"feature:{key}")
        if user_value is not None:
            return user_value == "on"
        if message.guild:
            server_value = self.bot.db.get_setting(f"guild:{message.guild.id}", f"feature:{key}")
            if server_value is not None:
                return server_value == "on"
        return True

    def is_user_muted(self, user_id):
        return self.bot.db.get_setting(f"user:{user_id}", "feature:bot_interactions") == "off"

    async def _send(self, target, text):
        if isinstance(target, discord.Interaction):
            await target.response.send_message(text, ephemeral=True)
        else:
            destination = target if hasattr(target, "send") else target.channel
            await destination.send(text)

    async def _configure(self, target, action="show", feature=None, scope="me"):
        if feature == "bot" and scope == "server":
            await self._send(target, "Full bot mute is personal only. Choose **Just me**.")
            return

        if scope == "server":
            if not target.guild:
                await self._send(target, "Server feature settings must be changed inside a server.")
                return
            permissions = target.user.guild_permissions if isinstance(target, discord.Interaction) else target.author.guild_permissions
            if not permissions.manage_guild:
                await self._send(target, "Only members with **Manage Server** can change server feature defaults.")
                return

        target_id = self._target_id(target, scope)
        if action == "show" or not feature:
            lines = [f"**Feature settings for {scope}:**"]
            for short_name, (label, key) in FEATURES.items():
                value = self.bot.db.get_setting(target_id, f"feature:{key}", "server default" if scope == "me" else "on")
                lines.append(f"- **{label}:** {value} (`{short_name}`)")
            lines.append("Use `features off bot` to be completely ignored, or `features on bot` to return.")
            await self._send(target, "\n".join(lines))
            return

        if feature not in FEATURES or action not in {"on", "off", "default"}:
            await self._send(target, "Use `features on/off bot`, `features on/off voice`, or `features on/off sheets`.")
            return

        label, key = FEATURES[feature]
        if action == "default":
            self.bot.db.delete_setting(target_id, f"feature:{key}")
            value = "server default" if scope == "me" else "on"
        else:
            value = action
            self.bot.db.set_setting(target_id, f"feature:{key}", value)
        if feature == "bot" and action == "off":
            await self._send(target, "The bot will now completely ignore you. Say `listen to me` or use `/features on bot` to return.")
            return
        await self._send(target, f"**{label}** set to **{value}** for {scope}.")

    async def handle_message(self, message):
        text = " ".join(str(message.content or "").lower().strip().split())
        patterns = (
            (r"^(?:ignore me|stop listening to me|do not interact with me|don't interact with me)$", "bot", "off"),
            (r"^(?:listen to me|stop ignoring me|interact with me)$", "bot", "on"),
            (r"^(?:turn|switch) (on|off) (?:the )?(?:voice commands?|no prefix commands?)$", "voice", None),
            (r"^enable (?:the )?(?:voice commands?|no prefix commands?)$", "voice", "on"),
            (r"^disable (?:the )?(?:voice commands?|no prefix commands?)$", "voice", "off"),
            (r"^i (?:do not|don't) want (?:the )?(?:voice commands?|no prefix commands?)$", "voice", "off"),
            (r"^i want (?:the )?(?:voice commands?|no prefix commands?)$", "voice", "on"),
            (r"^(?:turn|switch) (on|off) (?:the )?(?:automatic sheet imports?|sheet detection)$", "sheets", None),
            (r"^enable (?:the )?(?:automatic sheet imports?|sheet detection)$", "sheets", "on"),
            (r"^disable (?:the )?(?:automatic sheet imports?|sheet detection)$", "sheets", "off"),
            (r"^i (?:do not|don't) want (?:the )?(?:automatic sheet imports?|sheet detection)$", "sheets", "off"),
            (r"^i want (?:the )?(?:automatic sheet imports?|sheet detection)$", "sheets", "on"),
        )
        for pattern, feature, forced_action in patterns:
            match = re.match(pattern, text)
            if not match:
                continue
            action = forced_action or match.group(1)
            await self._configure(message, action, feature, "me")
            return True
        return False

    @app_commands.command(name="features", description="Manage features or make the bot completely ignore you.")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Show settings", value="show"),
            app_commands.Choice(name="Turn on", value="on"),
            app_commands.Choice(name="Turn off", value="off"),
            app_commands.Choice(name="Use default", value="default"),
        ],
        feature=[
            app_commands.Choice(name="Completely ignore me", value="bot"),
            app_commands.Choice(name="Voice / no-prefix commands", value="voice"),
            app_commands.Choice(name="Automatic sheet imports", value="sheets"),
        ],
        scope=[
            app_commands.Choice(name="Just me", value="me"),
            app_commands.Choice(name="Server default", value="server"),
        ],
    )
    async def features_slash(self, interaction: discord.Interaction, action: str = "show", feature: str = None, scope: str = "me"):
        await self._configure(interaction, action, feature, scope)

    @commands.command(name="features", aliases=["feature"], help="Manage features or use `!features off bot` for personal full mute.")
    async def features_prefix(self, ctx, action: str = "show", feature: str = None, scope: str = "me"):
        await self._configure(ctx, action.lower(), feature.lower() if feature else None, scope.lower())


async def setup(bot):
    await bot.add_cog(FeaturesCog(bot))
