import datetime
import secrets

import discord
from discord import app_commands
from discord.ext import commands


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _build_ticket(self, user, guild, channel, details, command=None):
        ticket_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M") + f"-{secrets.randbelow(1000):03d}"
        location = "Personal install / DM"
        if guild:
            location = f"{guild.name} ({guild.id})"
            if channel:
                location += f" / #{getattr(channel, 'name', 'unknown')} ({channel.id})"

        lines = [
            f"🎫 **Support Ticket {ticket_id}**",
            f"**User:** {user} ({user.id})",
            f"**Location:** {location}",
        ]
        if command:
            lines.append(f"**Command or feature:** {command}")
        lines.append(f"**Problem:** {details}")
        return ticket_id, "\n".join(lines)

    async def _submit(self, target, details, command=None):
        is_interaction = isinstance(target, discord.Interaction)
        user = target.user if is_interaction else target.author
        guild = target.guild
        channel = target.channel
        if is_interaction and not target.response.is_done():
            await target.response.defer(ephemeral=True)
        details = " ".join((details or "").strip().split())
        command = " ".join((command or "").strip().split()) or None

        if len(details) < 5:
            response = "Please include a short description of what went wrong."
            if is_interaction:
                await target.followup.send(response, ephemeral=True)
            else:
                await target.send(response)
            return

        ticket_id, report = self._build_ticket(user, guild, channel, details[:1200], command)
        await self.bot.send_alert(report)
        await self.bot.alert_owner(report)

        confirmation = (
            f"Ticket **{ticket_id}** was sent to the bot owner.\n"
            "Thank you. Include this ticket number if you send more information."
        )
        if is_interaction:
            await target.followup.send(confirmation, ephemeral=True)
        else:
            await target.send(confirmation)

    @app_commands.command(name="ticket", description="Report a bot problem directly to the owner.")
    @app_commands.describe(
        details="Describe what happened and what you expected.",
        command="Optional command or feature that failed, such as /sheet.",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ticket_slash(self, interaction: discord.Interaction, details: str, command: str = None):
        await self._submit(interaction, details, command)

    @commands.command(name="ticket", help="Report a bot problem. Usage: !ticket /sheet did not respond")
    async def ticket_prefix(self, ctx, *, details: str):
        await self._submit(ctx, details)


async def setup(bot):
    await bot.add_cog(TicketCog(bot))
