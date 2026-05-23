import discord
from discord import app_commands
from discord.ext import commands
from services.permissions import is_gm

class ChannelMgmt(commands.GroupCog, group_name="channel", description="Manage channel-specific settings like roles and reactions."):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rr", help="Super simple reaction role: !rr #channel @role 🚀")
    @commands.has_permissions(manage_guild=True)
    async def simple_rr_prefix(self, ctx, *args):
        """
        Easy prefix command: !rr [#channel] @role emoji
        """
        channel = None
        role = None
        emoji = None

        # Parse args
        for arg in args:
            if arg.startswith("<#") and arg.endswith(">"):
                # Channel mention
                cid = int(arg[2:-1])
                channel = ctx.guild.get_channel(cid)
            elif arg.startswith("<@&") and arg.endswith(">"):
                # Role mention
                rid = int(arg[3:-1])
                role = ctx.guild.get_role(rid)
            elif arg.startswith("<@") and arg.endswith(">"):
                # User mention (ignore)
                pass
            else:
                # Likely the emoji
                emoji = arg

        if not role or not emoji:
            await ctx.send("❌ Usage: `!rr @Role 🚀` or `!rr #channel @Role 🚀`")
            return

        target_channel = ctx.channel
        description_text = f"React with {emoji} to receive the **{role.name}** role!"
        
        if channel:
            description_text = f"React with {emoji} to receive the **{role.name}** role and gain access to {channel.mention}!"

        embed = discord.Embed(
            title="🔓 Channel Access",
            description=description_text,
            color=role.color if role.color.value != 0 else discord.Color.blue()
        )
        embed.set_footer(text=f"Role: {role.name}")

        try:
            msg = await target_channel.send(embed=embed)
            await msg.add_reaction(emoji)
            self.bot.db.add_reaction_role(ctx.guild.id, msg.id, emoji, role.id)
            
            await ctx.send(f"✅ Setup complete in {target_channel.mention}!", delete_after=10)
            try:
                await ctx.message.delete()
            except:
                pass
        except Exception as e:
            await ctx.send(f"❌ Setup failed: `{e}`")

    @commands.command(name="lock", help="Lock channel to a role: !lock #channel @Role")
    @commands.has_permissions(manage_guild=True)
    async def simple_lock_prefix(self, ctx, channel: discord.TextChannel, role: discord.Role):
        """Automate locking a channel to a specific role."""
        try:
            # 1. Deny everyone
            await channel.set_permissions(ctx.guild.default_role, view_channel=False)
            # 2. Allow the role
            await channel.set_permissions(role, view_channel=True, send_messages=True)
            await ctx.send(f"🔒 **{channel.mention}** is now locked! Only users with the **{role.name}** role can see it.")
        except Exception as e:
            await ctx.send(f"❌ Failed to set permissions: `{e}`")

    @app_commands.command(name="lock", description="Lock a channel so only a specific role can see it.")
    @app_commands.describe(channel="The channel to lock", role="The role that should have access")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def lock_slash(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
        """Slash version of the lock command."""
        try:
            await channel.set_permissions(interaction.guild.default_role, view_channel=False)
            await channel.set_permissions(role, view_channel=True, send_messages=True)
            await interaction.response.send_message(f"🔒 **{channel.mention}** is now locked to the **{role.name}** role!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to set permissions: `{e}`", ephemeral=True)

    @commands.command(name="role", help="BULK SETUP: !role <emoji> <ID> [emoji ID ...] [#postChannel]")
    @commands.has_permissions(manage_guild=True)
    async def smart_role_command(self, ctx, *args):
        """
        Smart command: 
        - !role @Role -> Sets channel GM
        - !role <emoji> <ID> [<emoji> <ID> ...] [#display_channel] -> Multi-Role Setup
        """
        if not args:
            await ctx.send("❌ Usage:\n- `!role @Role` (Set channel GM)\n- `!role 🚀 <ID> 💰 <ID> [#post-here]` (Bulk setup)")
            return

        arg1 = args[0]
        
        # Case 1: !role @Role
        if arg1.startswith("<@&") and arg1.endswith(">") and len(args) == 1:
            try:
                rid = int(arg1[3:-1])
                role = ctx.guild.get_role(rid)
                if role:
                    self.bot.db.set_setting(ctx.channel.id, "gm_role", str(role.id))
                    await ctx.send(f"✅ Users with the **{role.name}** role are now GMs in this channel.")
                    return
            except:
                pass

        # Case 2: Bulk Setup
        import re
        import unicodedata
        display_channel = None
        emojis = []
        ids = []

        for arg in args:
            # Custom Discord Emojis
            if arg.startswith("<:") or arg.startswith("<a:"):
                emojis.append(arg)
                continue

            # Channel Mentions
            if arg.startswith("<#") and arg.endswith(">"):
                ids.append(arg[2:-1])
                continue

            # Clean accidental trailing characters from copy-pasted IDs (e.g. '1465361516701155432v' -> '1465361516701155432')
            cleaned_arg = re.sub(r'(?<=\d)[a-zA-Z]+$', '', arg)
            
            # IDs
            if cleaned_arg.isdigit() and len(cleaned_arg) > 15:
                ids.append(cleaned_arg)
                continue

            # Bulletproof Emoji Check using Unicodedata Categories
            # Exclude standard letters (L*), numbers (N*), punctuation (P*), spaces (Z*), and invisible control chars (C*)
            # Standard emojis fall under 'So' (Symbol, Other), and compound emojis use marks that bypass this filter.
            cleaned_for_emoji = ""
            for c in arg:
                cat = unicodedata.category(c)
                if not (cat.startswith('L') or cat.startswith('N') or cat.startswith('P') or cat.startswith('Z') or cat.startswith('C')):
                    cleaned_for_emoji += c
            
            if cleaned_for_emoji:
                emojis.append(arg)

        # The last ID might be the display channel if it was explicitly passed as a mention at the very end
        if len(ids) == len(emojis) + 1:
            try:
                cid_str = ids.pop()
                display_channel = ctx.guild.get_channel(int(cid_str))
            except:
                pass
                
        if not emojis or len(emojis) != len(ids):
            await ctx.send(f"❌ Invalid format or unmatched pairs. Found {len(emojis)} emojis and {len(ids)} category/channel IDs.\n"
                           f"Detected Emojis: `{' '.join(emojis)}`\n"
                           f"Detected IDs: `{' '.join(ids)}`")
            return

        pairs = list(zip(emojis, ids))

        description_lines = []
        setup_actions = [] # (emoji, role_id)
        
        guild = ctx.guild
        for emoji, target_str in pairs:
            # Resolve target
            target = None
            if target_str.isdigit():
                target = guild.get_channel(int(target_str))
            elif target_str.startswith("<#") and target_str.endswith(">"):
                cid = int(target_str[2:-1])
                target = guild.get_channel(cid)
            
            if not target:
                await ctx.send(f"⚠️ Could not find channel/category for ID `{target_str}`. Skipping.")
                continue

            # 1. Find or Create Role
            role_name = target.name.replace("-", " ").title()
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    role = await guild.create_role(name=role_name, reason=f"Auto-created for {target.name} access.")
                    await ctx.send(f"✨ Created role: **{role.name}**", delete_after=5)
                except Exception as e:
                    await ctx.send(f"❌ Failed to create role for {target.name}: `{e}`")
                    continue

            # 2. Lock Target
            try:
                await target.set_permissions(guild.default_role, view_channel=False)
                await target.set_permissions(role, view_channel=True, send_messages=True)
            except Exception as e:
                await ctx.send(f"⚠️ Failed to lock {target.name}: `{e}`", delete_after=5)

            # 3. Add to Menu
            # Do NOT use target.mention because users without permissions will just see "#No Access"
            description_lines.append(f"{emoji} — Access to **{target.name}**")
            setup_actions.append((emoji, role.id))

        if not description_lines:
            await ctx.send("❌ No valid roles were set up.")
            return

        # Create the single compact embed
        post_in = display_channel or ctx.channel
        embed = discord.Embed(
            title="🔓 Server Access",
            description="\n".join(description_lines),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Click a reaction to join a channel!")

        try:
            msg = await post_in.send(embed=embed)
            for emoji, _ in setup_actions:
                await msg.add_reaction(emoji)
            
            # Save all to DB
            for emoji, role_id in setup_actions:
                self.bot.db.add_reaction_role(guild.id, msg.id, emoji, role_id)
            
            await ctx.send(f"✅ Compact menu created in {post_in.mention}!", delete_after=10)
            try:
                await ctx.message.delete()
            except:
                pass
        except Exception as e:
            await ctx.send(f"❌ Failed to post menu: `{e}`")

    # --- GM Role Management ---
    @app_commands.command(name="role", description="Show or set the GM role for this channel.")
    @app_commands.describe(
        action="Choose 'set', 'clear', or 'info'",
        role="The role to set as GM for this channel (only if action is 'set')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Set GM Role", value="set"),
        app_commands.Choice(name="Clear GM Role", value="clear"),
        app_commands.Choice(name="View Info", value="info")
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def role_management(self, interaction: discord.Interaction, action: str, role: discord.Role = None):
        """Manage channel GM roles."""
        channel_id = interaction.channel.id
        
        if action == "set":
            if not role:
                await interaction.response.send_message("❌ Please specify a role to set.", ephemeral=True)
                return
            
            self.bot.db.set_setting(channel_id, "gm_role", str(role.id))
            await interaction.response.send_message(f"✅ Users with the **{role.name}** role are now GMs in this channel.", ephemeral=True)
            
        elif action == "clear":
            self.bot.db.set_setting(channel_id, "gm_role", "None")
            await interaction.response.send_message("🧹 GM role cleared for this channel.", ephemeral=True)
            
        elif action == "info":
            role_id = self.bot.db.get_setting(channel_id, "gm_role")
            if not role_id or role_id == "None":
                await interaction.response.send_message("ℹ️ No GM role set for this channel. Only server admins and the campaign GM have control.", ephemeral=True)
            else:
                role_obj = interaction.guild.get_role(int(role_id))
                role_name = role_obj.name if role_obj else f"Unknown Role (ID: {role_id})"
                await interaction.response.send_message(f"🎭 Current GM role for this channel: **{role_name}**", ephemeral=True)

    # --- Reaction Role Management ---
    reactionrole = app_commands.Group(name="reactionrole", description="Manage reaction-based role assignment.")

    @reactionrole.command(name="create", description="Create a new message that grants a role when reacted to.")
    @app_commands.describe(
        channel="The channel to post the message in",
        text="The message text (e.g. 'React to join the Spacer deck!')",
        emoji="The emoji to use (copy-paste the actual emoji or use :name: if custom)",
        role="The role to grant"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rr_create(self, interaction: discord.Interaction, channel: discord.TextChannel, text: str, emoji: str, role: discord.Role):
        """Create a reaction role message."""
        try:
            # 1. Send the message
            msg = await channel.send(text)
            
            # 2. Add the initial reaction
            try:
                await msg.add_reaction(emoji)
            except discord.HTTPException:
                await msg.delete()
                await interaction.response.send_message(f"❌ Invalid emoji: `{emoji}`. Make sure it's a standard emoji or a custom one the bot can use.", ephemeral=True)
                return

            # 3. Save to database
            self.bot.db.add_reaction_role(interaction.guild_id, msg.id, emoji, role.id)
            
            await interaction.response.send_message(f"✅ Reaction role created in {channel.mention}!\nMessage ID: `{msg.id}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create reaction role: `{e}`", ephemeral=True)

    @reactionrole.command(name="add", description="Add a reaction role to an existing message.")
    @app_commands.describe(
        message_id="The ID of the existing message",
        emoji="The emoji to use",
        role="The role to grant"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rr_add(self, interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
        """Add a reaction role to an existing message."""
        if not message_id.isdigit():
            await interaction.response.send_message("❌ Invalid Message ID.", ephemeral=True)
            return

        try:
            # Try to find the message in the current channel or guild
            msg = None
            for ch in interaction.guild.text_channels:
                try:
                    msg = await ch.fetch_message(int(message_id))
                    if msg: break
                except:
                    continue
            
            if not msg:
                await interaction.response.send_message("❌ Could not find that message in this server.", ephemeral=True)
                return

            await msg.add_reaction(emoji)
            self.bot.db.add_reaction_role(interaction.guild_id, msg.id, emoji, role.id)
            await interaction.response.send_message(f"✅ Added reaction role to message `{message_id}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to add reaction: `{e}`", ephemeral=True)

    @reactionrole.command(name="list", description="List all reaction roles in this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rr_list(self, interaction: discord.Interaction):
        """List active reaction roles."""
        roles = self.bot.db.list_reaction_roles(interaction.guild_id)
        if not roles:
            await interaction.response.send_message("ℹ️ No reaction roles configured.", ephemeral=True)
            return

        embed = discord.Embed(title="🎭 Reaction Roles", color=discord.Color.blue())
        for r in roles:
            role_obj = interaction.guild.get_role(int(r['role_id']))
            role_name = role_obj.name if role_obj else f"Unknown ({r['role_id']})"
            embed.add_field(
                name=f"Message {r['message_id']}",
                value=f"Emoji: {r['emoji']} -> Role: **{role_name}**",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @reactionrole.command(name="remove", description="Remove a reaction role from a message.")
    @app_commands.describe(message_id="The ID of the message", emoji="The emoji to remove")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rr_remove(self, interaction: discord.Interaction, message_id: str, emoji: str):
        """Remove a reaction role."""
        self.bot.db.remove_reaction_role(message_id, emoji)
        await interaction.response.send_message(f"🗑️ Removed reaction role `{emoji}` from message `{message_id}`.", ephemeral=True)

    @app_commands.command(name="setup", description="Super simple reaction role setup.")
    @app_commands.describe(
        role="The role to grant",
        emoji="The emoji to use",
        channel="Optional: channel to post in (defaults to current)"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def simple_setup(self, interaction: discord.Interaction, role: discord.Role, emoji: str, channel: discord.TextChannel = None):
        """Quickly create a reaction role with a standard message."""
        target_channel = channel or interaction.channel
        
        embed = discord.Embed(
            title="🎭 Access Granted",
            description=f"React with {emoji} to receive the **{role.name}** role and gain access to related channels!",
            color=role.color if role.color.value != 0 else discord.Color.blue()
        )
        embed.set_footer(text=f"Role: {role.name}")

        try:
            msg = await target_channel.send(embed=embed)
            await msg.add_reaction(emoji)
            self.bot.db.add_reaction_role(interaction.guild_id, msg.id, emoji, role.id)
            
            await interaction.response.send_message(f"✅ Setup complete in {target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Setup failed: `{e}`", ephemeral=True)

    @role_management.error
    @rr_create.error
    @rr_add.error
    @rr_list.error
    @rr_remove.error
    @simple_setup.error
    async def perms_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("🚫 **Permission Denied:** You need **Manage Server** permission for this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChannelMgmt(bot))
