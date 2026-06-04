import discord
from discord import app_commands
from discord.ext import commands


class VoiceAccessCog(commands.Cog):
    """Short slash commands that are easier to trigger through voice dictation."""

    def __init__(self, bot):
        self.bot = bot

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
        text = (
            "**Voice-friendly commands**\n"
            "`/roll expression: d20` - Roll dice with user install.\n"
            "`/roll expression: d20 7 times` - Repeated rolls in order.\n"
            "`/rr` is not possible as a user install; use `/multiroll` instead.\n"
            "`/up` or `/down` - Show recent messages so you do not have to scroll.\n"
            "`/catchup count: 10` - Read the last messages in a compact list.\n"
            "`/findchannel query: lore` - Find channel links when the bot is installed in the server.\n\n"
            "Discord does not allow an app to physically scroll your client. "
            "These commands give you clickable/context summaries that are easier to use with voice."
        )
        await interaction.response.send_message(text, ephemeral=True)


async def setup(bot):
    await bot.add_cog(VoiceAccessCog(bot))
