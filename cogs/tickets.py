import datetime
import secrets

import discord
from discord import app_commands
from discord.ext import commands


class TicketReplyModal(discord.ui.Modal, title="Reply to support ticket"):
    message = discord.ui.TextInput(label="Message", style=discord.TextStyle.paragraph, max_length=1200)

    def __init__(self, cog, ticket_id):
        super().__init__()
        self.cog = cog
        self.ticket_id = ticket_id

    async def on_submit(self, interaction):
        await self.cog._owner_reply(interaction, self.ticket_id, str(self.message))


class TicketOwnerView(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=900)
        self.cog = cog
        self.ticket_id = ticket_id

    async def interaction_check(self, interaction):
        if await self.cog._is_owner(interaction.user):
            return True
        await interaction.response.send_message("These ticket controls are restricted to the bot owner.", ephemeral=True)
        return False

    @discord.ui.button(label="Reply", style=discord.ButtonStyle.primary)
    async def reply(self, interaction, button):
        await interaction.response.send_modal(TicketReplyModal(self.cog, self.ticket_id))

    @discord.ui.button(label="Close as fixed", style=discord.ButtonStyle.success)
    async def close(self, interaction, button):
        await self.cog._owner_reply(interaction, self.ticket_id, "This issue has been fixed.", close=True)

    @discord.ui.button(label="Reopen", style=discord.ButtonStyle.secondary)
    async def reopen(self, interaction, button):
        self.cog.bot.db.set_support_ticket_status(self.ticket_id, "open")
        await self.cog._respond(interaction, f"Ticket **{self.ticket_id}** reopened.")


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _is_owner(self, user):
        app = await self.bot.application_info()
        return user.id == app.owner.id

    async def _respond(self, target, message, *, ephemeral=True):
        if isinstance(target, discord.Interaction):
            if not target.response.is_done():
                await target.response.send_message(message, ephemeral=ephemeral)
            else:
                await target.followup.send(message, ephemeral=ephemeral)
        else:
            await target.send(message)

    def _ticket_id(self):
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M")
        return f"{stamp}-{secrets.randbelow(1000):03d}"

    def _location(self, ticket):
        if not ticket.get("guild_id"):
            return "Personal install / DM"
        location = f"{ticket.get('guild_name') or 'Unknown Server'} ({ticket['guild_id']})"
        if ticket.get("channel_id"):
            location += f" / #{ticket.get('channel_name') or 'unknown'} ({ticket['channel_id']})"
        return location

    def _render_ticket(self, ticket):
        lines = [
            f"🎫 **Support Ticket {ticket['ticket_id']}** [{ticket['status'].upper()}]",
            f"**User:** {ticket.get('user_name')} ({ticket['user_id']})",
            f"**Location:** {self._location(ticket)}",
        ]
        if ticket.get("command_name"):
            lines.append(f"**Command or feature:** {ticket['command_name']}")
        lines.append("**Conversation:**")
        for message in ticket.get("messages", []):
            role = "Owner" if message["author_role"] == "owner" else "Reporter"
            content = str(message["content"]).replace("\n", " ")
            lines.append(f"- **{role}:** {content}")
        rendered = "\n".join(lines)
        return rendered[:1950] + ("..." if len(rendered) > 1950 else "")

    async def _notify_owner(self, ticket):
        report = self._render_ticket(ticket)
        await self.bot.send_alert(report)
        await self.bot.alert_owner(report)

    async def _submit(self, target, details, command=None, ticket_id=None):
        is_interaction = isinstance(target, discord.Interaction)
        user = target.user if is_interaction else target.author
        guild = target.guild
        channel = target.channel
        if is_interaction and not target.response.is_done():
            await target.response.defer(ephemeral=True)

        details = " ".join((details or "").strip().split())
        command = " ".join((command or "").strip().split()) or None
        ticket_id = (ticket_id or "").strip()
        if len(details) < 5:
            await self._respond(target, "Please include a short description of what went wrong.")
            return

        if ticket_id:
            ticket = self.bot.db.get_support_ticket(ticket_id)
            if not ticket or str(ticket["user_id"]) != str(user.id):
                await self._respond(target, f"I could not find ticket `{ticket_id}` for your account.")
                return
            if ticket["status"] == "closed":
                await self._respond(target, f"Ticket `{ticket_id}` is closed. Please open a new ticket.")
                return
            self.bot.db.add_support_ticket_message(ticket_id, user.id, str(user), "reporter", details[:1200])
            ticket = self.bot.db.get_support_ticket(ticket_id)
            await self._notify_owner(ticket)
            await self._respond(target, f"Your follow-up was added to ticket **{ticket_id}**.")
            return

        ticket_id = self._ticket_id()
        self.bot.db.create_support_ticket(
            ticket_id=ticket_id,
            user_id=user.id,
            user_name=str(user),
            guild_id=guild.id if guild else None,
            guild_name=guild.name if guild else None,
            channel_id=channel.id if channel else None,
            channel_name=getattr(channel, "name", None),
            command_name=command,
            details=details[:1200],
        )
        await self._notify_owner(self.bot.db.get_support_ticket(ticket_id))
        await self._respond(
            target,
            f"Ticket **{ticket_id}** was sent to the bot owner.\n"
            f"Add more information later with `/ticket details:<message> ticket_id:{ticket_id}`.",
        )

    async def _owner_reply(self, target, ticket_id, message, close=False):
        user = target.user if isinstance(target, discord.Interaction) else target.author
        if isinstance(target, discord.Interaction) and not target.response.is_done():
            await target.response.defer(ephemeral=True)
        if not await self._is_owner(user):
            await self._respond(target, "This command is restricted to the bot owner.")
            return

        ticket = self.bot.db.get_support_ticket(ticket_id)
        if not ticket:
            await self._respond(target, f"Ticket `{ticket_id}` was not found.")
            return

        message = " ".join((message or "").strip().split())
        if message:
            self.bot.db.add_support_ticket_message(ticket_id, user.id, str(user), "owner", message[:1200])
        if close:
            self.bot.db.set_support_ticket_status(ticket_id, "closed")

        delivered = False
        try:
            reporter = self.bot.get_user(int(ticket["user_id"])) or await self.bot.fetch_user(int(ticket["user_id"]))
            status_text = "\n\nThis ticket is now closed." if close else ""
            followup_text = "" if close else f"\n\nReply with `/ticket details:<message> ticket_id:{ticket_id}`."
            await reporter.send(
                f"🎫 **Update for ticket {ticket_id}**\n"
                f"{message or 'Your ticket has been closed.'}{status_text}{followup_text}"
            )
            delivered = True
        except Exception:
            delivered = False

        action = "closed" if close else "replied to"
        delivery = "Reporter notified by DM." if delivered else "DM delivery failed."
        await self._respond(target, f"Ticket **{ticket_id}** {action}. {delivery}")

    @app_commands.command(name="ticket", description="Open or follow up on a support ticket.")
    @app_commands.describe(
        details="Describe what happened or add follow-up information.",
        command="Optional command or feature that failed, such as /sheet.",
        ticket_id="Optional existing ticket number for a follow-up.",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ticket_slash(self, interaction: discord.Interaction, details: str, command: str = None, ticket_id: str = None):
        await self._submit(interaction, details, command, ticket_id)

    @commands.command(name="ticket", help="Open a ticket. Usage: !ticket /sheet did not respond")
    async def ticket_prefix(self, ctx, *, details: str):
        await self._submit(ctx, details)

    @app_commands.command(name="tickets", description="Owner: list recent support tickets.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def tickets_slash(self, interaction: discord.Interaction, status: str = "open"):
        await interaction.response.defer(ephemeral=True)
        if not await self._is_owner(interaction.user):
            await self._respond(interaction, "This command is restricted to the bot owner.")
            return
        tickets = self.bot.db.list_support_tickets(status.lower() if status.lower() in {"open", "closed", "all"} else "open")
        lines = ["**Support Tickets**"]
        lines.extend(
            f"- `{ticket['ticket_id']}` [{ticket['status']}] {ticket.get('user_name')} - {ticket.get('command_name') or 'general'}"
            for ticket in tickets
        )
        await self._respond(interaction, "\n".join(lines) if tickets else "No matching tickets.")

    @commands.command(name="tickets")
    @commands.is_owner()
    async def tickets_prefix(self, ctx, status: str = "open"):
        tickets = self.bot.db.list_support_tickets(status.lower() if status.lower() in {"open", "closed", "all"} else "open")
        lines = ["**Support Tickets**"]
        lines.extend(f"- `{t['ticket_id']}` [{t['status']}] {t.get('user_name')} - {t.get('command_name') or 'general'}" for t in tickets)
        await ctx.send("\n".join(lines) if tickets else "No matching tickets.")

    @app_commands.command(name="ticketview", description="Owner: view a support ticket conversation.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ticketview_slash(self, interaction: discord.Interaction, ticket_id: str):
        await interaction.response.defer(ephemeral=True)
        if not await self._is_owner(interaction.user):
            await self._respond(interaction, "This command is restricted to the bot owner.")
            return
        ticket = self.bot.db.get_support_ticket(ticket_id)
        if not ticket:
            await self._respond(interaction, f"Ticket `{ticket_id}` was not found.")
            return
        await interaction.followup.send(
            self._render_ticket(ticket),
            view=TicketOwnerView(self, ticket_id),
            ephemeral=True,
        )

    @commands.command(name="ticketview")
    @commands.is_owner()
    async def ticketview_prefix(self, ctx, ticket_id: str):
        ticket = self.bot.db.get_support_ticket(ticket_id)
        await ctx.send(
            self._render_ticket(ticket) if ticket else f"Ticket `{ticket_id}` was not found.",
            view=TicketOwnerView(self, ticket_id) if ticket else None,
        )

    @app_commands.command(name="ticketreply", description="Owner: reply to a support ticket.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ticketreply_slash(self, interaction: discord.Interaction, ticket_id: str, message: str):
        await self._owner_reply(interaction, ticket_id, message)

    @commands.command(name="ticketreply")
    @commands.is_owner()
    async def ticketreply_prefix(self, ctx, ticket_id: str, *, message: str):
        await self._owner_reply(ctx, ticket_id, message)

    @app_commands.command(name="ticketclose", description="Owner: reply to and close a support ticket.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ticketclose_slash(self, interaction: discord.Interaction, ticket_id: str, message: str = "This issue has been fixed."):
        await self._owner_reply(interaction, ticket_id, message, close=True)

    @commands.command(name="ticketclose")
    @commands.is_owner()
    async def ticketclose_prefix(self, ctx, ticket_id: str, *, message: str = "This issue has been fixed."):
        await self._owner_reply(ctx, ticket_id, message, close=True)

    def _render_errors(self):
        errors = self.bot.db.list_runtime_errors(10)
        if not errors:
            return "No persisted runtime errors."
        lines = ["**Recent Runtime Errors**"]
        for item in errors:
            location = f"{item.get('guild_id') or 'DM'}/{item.get('channel_id') or '-'}"
            error = " ".join(str(item.get("error") or "").split())[:220]
            lines.append(
                f"- `{item['id']}` {item['created_at']} **{item.get('source')}** "
                f"`{item.get('command_name') or '-'}` at `{location}`: {error}"
            )
        return "\n".join(lines)[:1950]

    @app_commands.command(name="errors", description="Owner: show recently persisted runtime errors.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def errors_slash(self, interaction: discord.Interaction):
        if not await self._is_owner(interaction.user):
            await interaction.response.send_message("This command is restricted to the bot owner.", ephemeral=True)
            return
        await interaction.response.send_message(self._render_errors(), ephemeral=True)

    @commands.command(name="errors")
    @commands.is_owner()
    async def errors_prefix(self, ctx):
        await ctx.send(self._render_errors())


async def setup(bot):
    await bot.add_cog(TicketCog(bot))
