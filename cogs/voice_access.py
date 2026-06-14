import discord
from discord import app_commands
from discord.ext import commands


class VoiceAccessCog(commands.Cog):
    """Short slash commands that are easier to trigger through voice dictation."""

    def __init__(self, bot):
        self.bot = bot

    async def _send_voice_help(self, interaction: discord.Interaction):
        text = (
            "**Voice-friendly commands**\n"
            "`roll one d6`, `sheet`, `help`, and other commands can be sent without `/` or `!` "
            "when the bot is installed in the server.\n"
            "The message must begin with an exact command name and stay on one line.\n"
            "`/voice phrase: roll one d6` - Natural dice command with a personal install.\n"
            "`/voice phrase: roll d20 seven times` - Repeated rolls in order.\n"
            "`/voice phrase: oracle` - Ask the Oracle.\n"
            "`/voice phrase: weather` - Generate weather.\n"
            "`/roll expression: d20` - Direct dice command.\n"
            "`/up` `/down` `/catchup` - Show recent messages when the bot is installed in the server.\n\n"
            "Discord does not send plain messages like `roll one d6` to a user-installed app. "
            "Say `/voice`, then dictate the phrase."
        )
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="voice", description="Run a natural spoken command through your personal app install.")
    @app_commands.describe(phrase="Say a command, such as: roll one d6")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def voice_slash(self, interaction: discord.Interaction, phrase: str):
        phrase = " ".join((phrase or "").strip().split())
        normalized, _ = self.bot.web_service._normalize_voice_roll_message(phrase)
        if normalized.startswith(("!roll ", "!gmroll ", "!multiroll ", "!attack ", "!skill ")):
            command, expression = normalized[1:].split(" ", 1)
            response = self.bot.web_service._build_voice_roll_response(
                command,
                expression,
                self.bot.dice_service,
                interaction.user.display_name,
            )
            await interaction.response.send_message(
                f"Interpreted as `{normalized}`\n{response}",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        storyteller = self.bot.get_cog("StorytellerCog")
        simple_commands = {
            "oracle": "oracle",
            "reaction": "reaction",
            "reaction roll": "reaction",
            "plot": "plot",
            "plot hook": "plot",
            "loot": "loot",
            "weather": "weather",
            "encounter": "encounter",
            "encounter check": "encounter",
            "hazard": "hazard",
        }
        callback_name = simple_commands.get(phrase.lower())
        if callback_name and storyteller:
            command = getattr(storyteller, callback_name)
            await command.callback(storyteller, interaction)
            return

        if phrase.lower() in {"help", "voice help", "voicehelp"}:
            await self._send_voice_help(interaction)
            return

        await interaction.response.send_message(
            "I could not understand that voice command. Try `/voicehelp`.",
            ephemeral=True,
        )

    @app_commands.command(name="catchup", description="Read recent messages aloud-friendly so you do not need to scroll.")
    @app_commands.describe(count="How many recent messages to summarize, from 1 to 20.")
    async def catchup_slash(self, interaction: discord.Interaction, count: int = 10):
        await self.bot.send_catchup(interaction, count)

    @app_commands.command(name="up", description="Voice shortcut: show recent messages above this point.")
    @app_commands.describe(count="How many recent messages to show, from 1 to 20.")
    async def up_slash(self, interaction: discord.Interaction, count: int = 8):
        await self.bot.send_catchup(interaction, count)

    @app_commands.command(name="down", description="Voice shortcut: show the latest messages in this channel.")
    @app_commands.describe(count="How many recent messages to show, from 1 to 20.")
    async def down_slash(self, interaction: discord.Interaction, count: int = 8):
        await self.bot.send_catchup(interaction, count)

    @app_commands.command(name="voicehelp", description="Show voice-friendly ways to use DICEwithoutNumber.")
    async def voicehelp_slash(self, interaction: discord.Interaction):
        await self._send_voice_help(interaction)


async def setup(bot):
    await bot.add_cog(VoiceAccessCog(bot))
