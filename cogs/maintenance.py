import discord
import json
from discord.ext import commands, tasks
import os
import zipfile
import datetime
import sys
import subprocess
from services.secret_loader import load_project_env

load_project_env()

from typing import Optional

class Maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_channel_id: Optional[int] = None
        backup_id = os.getenv("BACKUP_CHANNEL_ID")
        if backup_id and str(backup_id).isdigit():
            self.backup_channel_id = int(backup_id)
        else:
            self.backup_channel_id = None
            print("Warning: BACKUP_CHANNEL_ID not properly set in private env files.")

        # Start the daily backup task
        self.daily_backup.start()

    def cog_unload(self):
        self.daily_backup.cancel()

    async def create_backup(self):
        """Creates a zip file of the data directory."""
        data_dir = "data"
        if not os.path.exists(data_dir):
            return None

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.zip"
        backup_path = os.path.join("tmp", backup_filename)
        
        # Ensure tmp dir exists
        os.makedirs("tmp", exist_ok=True)

        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.join(data_dir, '..'))
                    zipf.write(file_path, arcname)
        
        return backup_path

    @tasks.loop(hours=24)
    async def daily_backup(self):
        """Runs the backup every 24 hours."""
        if not self.backup_channel_id:
            return

        # Wait for bot to be ready
        await self.bot.wait_until_ready()
        
        channel = self.bot.get_channel(self.backup_channel_id)
        if not channel:
            print(f"Error: Could not find backup channel with ID {self.backup_channel_id}")
            return

        try:
            backup_path = await self.create_backup()
            if backup_path:
                file = discord.File(backup_path)
                await channel.send(f"📦 **Automated Daily Backup** - {datetime.datetime.now().strftime('%Y-%m-%d')}", file=file)
                # Clean up local zip
                os.remove(backup_path)
        except Exception as e:
            print(f"Backup failed: {e}")

    @commands.hybrid_command(name="backup", description="Manually trigger a data backup.")
    @commands.has_permissions(administrator=True)
    async def manual_backup(self, ctx):
        await ctx.defer(ephemeral=True)
        try:
            backup_path = await self.create_backup()
            if backup_path:
                file = discord.File(backup_path)
                await ctx.send("Backup created and uploaded.", file=file, ephemeral=True)
                os.remove(backup_path)
            else:
                await ctx.send("Data directory not found.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"Backup failed: {e}", ephemeral=True)

    @commands.hybrid_command(name="heartbeat", description="Check bot health and latency.")
    async def heartbeat(self, ctx):
        latency = round(self.bot.latency * 1000)
        uptime = str(datetime.datetime.now() - self.bot.start_time).split(".")[0]
        
        embed = discord.Embed(title="💓 Bot Heartbeat", color=discord.Color.green())
        embed.add_field(name="Latency", value=f"{latency}ms")
        embed.add_field(name="Uptime", value=uptime)
        embed.add_field(name="Provider", value=os.getenv("AI_PROVIDER", "gemini").upper())
        embed.set_footer(text=f"System: {os.name}")
        
        await ctx.send(embed=embed)

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, ctx, cog: str = None):
        """Reloads a specific cog or all cogs (Owner only)."""
        if cog:
            try:
                # Basic check for path traversal or invalid names
                cog = cog.lower().replace("cogs.", "").replace(".py", "")
                await self.bot.reload_extension(f"cogs.{cog}")
                await ctx.send(f"✅ **Reloaded cog:** `{cog}`")
            except Exception as e:
                await ctx.send(f"❌ **Failed to reload `{cog}`:**\n`{e}`")
        else:
            # Reload all cogs in the cogs/ directory
            await ctx.send("⏳ **Reloading all modules...**")
            results = []
            for filename in os.listdir("cogs"):
                if filename.endswith(".py") and not filename.startswith("__"):
                    cog_name = filename[:-3]
                    try:
                        await self.bot.reload_extension(f"cogs.{cog_name}")
                        results.append(f"✅ `{cog_name}`")
                    except Exception as e:
                        results.append(f"❌ `{cog_name}`: `{e}`")
            
            await ctx.send(f"🔄 **System Refresh Complete:**\n" + "\n".join(results))

    @commands.command(name="logs")
    @commands.is_owner()
    async def get_logs(self, ctx, lines: int = 30):
        """Get the latest bot logs (Owner only)."""
        log_file = "bot_new.log"
        if not os.path.exists(log_file):
            await ctx.send("Log file not found.")
            return
            
        try:
            with open(log_file, "r") as f:
                content = f.readlines()
                last_lines = content[-lines:]
                msg = "".join(last_lines)
                # Truncate to avoid 2000 char limit
                if len(msg) > 1900:
                    msg = msg[-1900:]
                await ctx.send(f"📋 **Latest Logs:**\n```{msg}```")
        except Exception as e:
            await ctx.send(f"Error reading logs: {e}")

    @commands.command(name="payload")
    @commands.is_owner()
    async def get_payload(self, ctx, search: str = None):
        """Get the latest sync payload info. Use !payload <name> to search."""
        payload_file = "sync_payload.json"
        if not os.path.exists(payload_file):
            await ctx.send("Payload file not found. Run !sync global first.")
            return
            
        try:
            with open(payload_file, "r") as f:
                data = json.load(f)
                count = len(data)
                
                if search:
                    match = next((c for c in data if c['name'].lower() == search.lower()), None)
                    if match:
                        await ctx.send(f"✅ **Found /{search}:**\nDescription: {match.get('description', 'No description')}\nOptions: {len(match.get('options', []))}")
                    else:
                        await ctx.send(f"❌ **/{search} NOT found** in the payload of {count} commands.")
                    return

                names = [c['name'] for c in data]
                await ctx.send(f"📦 **Last Sync Payload:**\n- Commands: {count}\n- Names: {', '.join(names[:15])}{'...' if count > 15 else ''}")
        except Exception as e:
            await ctx.send(f"Error reading payload: {e}")

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_guild(self, ctx, scope: str = "guild"):
        """Sync slash commands logic."""
        if not ctx.guild:
            await ctx.send("This command must be used in a server.")
            return
            
        guild = discord.Object(id=ctx.guild.id)
        
        if scope.lower() == "global":
            await ctx.send("⏳ **Syncing globally (Safe Mode)...**\n*Note: This avoids 'Entry Point' errors and takes ~1 hour to propagate.*")
            try:
                # Use the external script to handle the Entry Point dance
                import subprocess
                result = subprocess.run([sys.executable, "scripts/sync_global_safe.py"], capture_output=True, text=True)
                if result.returncode == 0:
                    await ctx.send(f"✅ **Global Sync Successful!**\nCommands updated and Entry Point restored.")
                else:
                    err_msg = result.stderr if result.stderr else result.stdout
                    # Truncate to avoid 2000 char limit
                    if len(err_msg) > 1800:
                        err_msg = err_msg[:1800] + "\n... (truncated)"
                    await ctx.send(f"❌ **Safe Sync Failed:**\n```{err_msg}```")
            except Exception as e:
                await ctx.send(f"❌ **Process Error:** `{e}`")

        elif scope.lower() == "guild":
            await ctx.send(f"⏳ **Syncing to this server ({ctx.guild.name})...**")
            try:
                self.bot.tree.copy_global_to(guild=guild)
                synced = await self.bot.tree.sync(guild=guild)
                await ctx.send(f"✅ **Local Sync Successful!**\nSynced **{len(synced)}** command(s) to this server.\n*These commands should appear instantly.*")
            except Exception as e:
                await ctx.send(f"❌ **Local Sync Failed:** `{e}`")

        elif scope.lower() == "clear":
            await ctx.send("⏳ **Clearing server overrides...**")
            try:
                self.bot.tree.clear_commands(guild=guild)
                await self.bot.tree.sync(guild=guild)
                await ctx.send("🧹 **Server overrides cleared.** Commands will now use the global registration.")
            except Exception as e:
                await ctx.send(f"❌ **Clear Failed:** `{e}`")
        
        else:
            await ctx.send("❌ Invalid option. Use `global`, `guild`, or `clear`.")

    @commands.command(name="maprestore", help="Manually restore the Primary Entry Point command (for App Launcher).")
    @commands.has_permissions(administrator=True)
    async def maprestore_cmd(self, ctx):
        """Run the restore_entry_point.py logic directly."""
        await ctx.send("⏳ **Restoring Entry Point...**")
        try:
            from scripts.restore_entry_point import restore_entry_point
            await restore_entry_point()
            await ctx.send("✅ **Entry Point restored!** Check your App Launcher.")
        except Exception as e:
            await ctx.send(f"❌ Restore failed: `{e}`")


    async def _do_avatar(self, responder, attachment):
        """Shared logic for avatar change — works from slash or prefix."""
        allowed_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp")

        if attachment is None:
            await responder(
                "❌ **No image provided.**\n"
                "**Slash command:** Type `/avatar`, click the `image` option, and attach a file.\n"
                "**Prefix command:** Type `!avatar` and attach a file to the same message.\n"
                "*Supported formats: PNG, JPG, JPEG, GIF, WebP — max 8 MB*"
            )
            return

        if not any(attachment.filename.lower().endswith(ext) for ext in allowed_extensions):
            await responder(
                f"❌ **Unsupported file type.**\n"
                f"Please use: `{', '.join(allowed_extensions)}`"
            )
            return

        if attachment.size > 8 * 1024 * 1024:
            await responder("❌ **Image too large.** Please use an image under 8 MB.")
            return

        try:
            image_bytes = await attachment.read()
            await self.bot.user.edit(avatar=image_bytes)
            await responder(
                "✅ **Avatar updated!**\n"
                "The bot's picture has been changed successfully.\n"
                "*It may take a moment to appear everywhere on Discord.*"
            )
        except discord.HTTPException as e:
            if e.status == 429 or "too fast" in str(e).lower():
                await responder(
                    "⏳ **Rate limited by Discord.**\n"
                    "You can only change the avatar a few times per hour. Try again later."
                )
            else:
                await responder(f"❌ **Failed to update avatar:** `{e}`")
        except Exception as e:
            await responder(f"❌ **Unexpected error:** `{e}`")

    # ── Slash command version (image is a named parameter Discord shows in the UI) ──
    @discord.app_commands.command(name="avatar", description="Change the bot's avatar. Click 'image' and attach a PNG/JPG/GIF.")
    @discord.app_commands.describe(image="The image file to use as the new bot avatar (PNG, JPG, GIF, WebP).")
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def avatar_slash(self, interaction: discord.Interaction, image: discord.Attachment):
        """Slash command: /avatar image:<file>"""
        await interaction.response.defer(ephemeral=True)
        async def respond(msg):
            await interaction.followup.send(msg, ephemeral=True)
        await self._do_avatar(respond, image)

    @avatar_slash.error
    async def avatar_slash_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 **Permission Denied:** You need **Manage Server** permission to change the bot's avatar.",
                ephemeral=True
            )

    # ── Prefix command version (!avatar with attached file) ──
    @commands.command(name="avatar", help="Change the bot's avatar. Attach an image to the message. Requires Manage Server.")
    @commands.has_permissions(manage_guild=True)
    async def avatar_prefix(self, ctx):
        """Prefix command: !avatar (with image attached to message)"""
        attachment = ctx.message.attachments[0] if ctx.message.attachments else None
        async def respond(msg):
            await ctx.send(msg)
        await self._do_avatar(respond, attachment)

    @avatar_prefix.error
    async def avatar_prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 **Permission Denied:** You need **Manage Server** permission to change the bot's avatar.")

    @commands.hybrid_command(name="rename", description="Change the bot's name (requires Server ID for verification).")
    @commands.has_permissions(manage_guild=True)
    async def rename_bot(self, ctx, server_id: str, *, name: str):
        """Update the bot's nickname (requires providing the actual Server ID)."""
        if not ctx.guild:
            await ctx.send("This command must be used in a server.", ephemeral=True)
            return

        # Clean the server_id (remove brackets, spaces, etc. if the user copied them literally)
        clean_id = server_id.strip("[]<>@! ")
        actual_id = str(ctx.guild.id)

        if clean_id != actual_id:
            await ctx.send(f"❌ **Identity Sync Failed**\nIncorrect Server ID. Verification required to change bot identity.\n*Hint: Use the exact ID for this server.*", ephemeral=True)
            return

        await ctx.defer(ephemeral=False) # Make response visible to everyone if using text command
        guild_id = actual_id
        
        try:
            settings = self.bot.web_service.settings
            if "servers" not in settings:
                settings["servers"] = {}
            
            if name.lower() == "clear":
                if guild_id in settings["servers"]:
                    del settings["servers"][guild_id]
                    message = "✨ **Server Identity Reset!** Reverting to global default name."
                else:
                    message = "ℹ️ No server override found. Already using global name."
            else:
                if guild_id not in settings["servers"]:
                    settings["servers"][guild_id] = {}
                settings["servers"][guild_id]["app_name"] = name
                message = f"🛡️ **Branding Sync Successful!**\nThis server now knows me as: **{name}**\n*Web tools and bot identity synced.*"

            # Save and Sync
            self.bot.web_service._save_settings()
            await self.bot.sync_identity()
            
            await ctx.send(message)
        except Exception as e:
            await ctx.send(f"❌ **System Error:** `{e}`")

    @rename_bot.error
    async def rename_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ **Missing Info:** Usage: `!rename [Server ID] [New Name]`\nExample: `!rename {ctx.guild.id} My Bot Name`", ephemeral=True)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f"🚫 **Permission Denied:** Only server administrators can rename the bot.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Maintenance(bot))
