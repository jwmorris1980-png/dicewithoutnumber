import discord
from discord import app_commands
from discord.ext import commands
import os
import logging
import datetime
import asyncio
import json
from services.database import DatabaseService
from services.web_service import WebService
from services.localization_service import LocalizationService
from services.dice_service import DiceService
from services.secret_loader import load_project_env

# Initialize Localization
localizer = LocalizationService()

class MyTranslator(app_commands.Translator):
    async def translate(self, string, locale, context):
        # Only translate if it looks like a localization key (contains dot, NO spaces)
        if "." not in string.message or " " in string.message:
            return None
        return localizer.translate(string.message, locale.value[:2])

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot_new.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('discord')

# Load environment variables from the private secrets location first.
load_project_env()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

class WithoutNumberBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=('!', '/'), 
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        self.start_time = datetime.datetime.now()
        self.db = DatabaseService()
        self.web_service = WebService(self)
        self.localizer = localizer
        self.dice_service = DiceService()
        
        # Configure command tree for modern Discord "App Launcher" (Activities) compatibility
        self.tree.allowed_contexts = discord.app_commands.AppCommandContext(
            guild=True, 
            dm_channel=True, 
            private_channel=True
        )
        self.tree.integration_types = discord.app_commands.AppInstallationType(
            guild=True, 
            user=True # Enables "User Installable" apps
        )

        # Add tree error handler
        self.tree.on_error = self.on_tree_error

    async def sync_identity(self):
        """Update bot nickname in all guilds and sync global username."""
        if not self.user:
            logger.info("Skipping identity sync: Bot user not logged in.")
            return

        logger.info("Sync Identity triggered")
        try:
            settings = self.web_service.settings
            global_name = settings.get('global', {}).get('app_name', 'DICEwithoutNumber')
            servers_settings = settings.get('servers', {})
            
            # 1. Sync Global Username (limited to 2 changes per hour)
            if self.user.name != global_name:
                try:
                    logger.info(f"Syncing global username from {self.user.name} to {global_name}")
                    await self.user.edit(username=global_name)
                    logger.info(f"Updated Global Discord username to: {global_name}")
                except Exception as e:
                    logger.warning(f"Failed to update global username (likely rate limited or restricted): {e}")

            # 2. Sync Server Nicknames for ALL guilds
            for guild in self.guilds:
                guild_id_str = str(guild.id)
                # Determine target name for this guild (Server Specific -> Global Default)
                target_name = global_name
                if guild_id_str in servers_settings and 'app_name' in servers_settings[guild_id_str]:
                    target_name = servers_settings[guild_id_str]['app_name']
                
                # Trim to 32 chars
                if len(target_name) > 32:
                    target_name = target_name[:29] + "..."
                
                try:
                    # Get or fetch bot member
                    me = guild.get_member(self.user.id)
                    if not me:
                        me = await guild.fetch_member(self.user.id)
                    
                    if me and me.nick != target_name:
                        logger.info(f"Updating nickname in {guild.name} to: {target_name}")
                        await me.edit(nick=target_name)
                except Exception as e:
                    logger.error(f"Failed to sync identity in {guild.name}: {e}")
        except Exception as e:
            logger.error(f"Failed to sync identity: {e}", exc_info=True)

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        logger.error(f"Slash command error: {error}", exc_info=True)
        
        # 1. Alert Log Channel
        await self.send_alert(f"❌ **Slash Command Error: {interaction.command.name if interaction.command else 'Unknown'}**\nUser: {interaction.user}\nError: `{error}`")
        
        # 2. Alert Owner via DM for critical errors
        # Special case: If it's a roll command, alert owner even for typos if they are struggling
        is_roll_cmd = interaction.command and interaction.command.name in ['roll', 'multiroll', 'skill', 'attack', 'gmroll']
        is_user_error = isinstance(error, (app_commands.CheckFailure, app_commands.CommandNotFound))
        
        if not is_user_error or is_roll_cmd:
            await self.alert_owner(f"🚨 **Roll/Feature Issue!**\nCommand: `/{interaction.command.name if interaction.command else 'Unknown'}`\nUser: `{interaction.user}`\nError: `{error}`")

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"An error occurred: `{error}`", ephemeral=True)
            else:
                await interaction.followup.send(f"An error occurred: `{error}`", ephemeral=True)
        except:
            pass

    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            logger.info(f"Interaction: /{interaction.command.name if interaction.command else 'unknown'} from {interaction.user} (ID: {interaction.user.id})")

    async def setup_hook(self):
        # Initial identity sync in background so it doesn't block web service
        asyncio.create_task(self.sync_identity())
        
        # Load extensions/cogs here
        cogs = [
            'cogs.dice', 'cogs.compendium', 'cogs.chargen', 'cogs.sheets',
            'cogs.help', 'cogs.tracker', 'cogs.rules_specific', 'cogs.sandbox',
            'cogs.faction', 'cogs.party', 'cogs.campaign', 'cogs.wizard',
            'cogs.maintenance', 'cogs.ships', 'cogs.intro', 'cogs.storyteller',
            'cogs.map_commands', 'cogs.channel_mgmt'
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded extension: {cog}")
            except Exception as e:
                logger.error(f"Failed to load extension {cog}: {e}", exc_info=True)
        
        # Set the translator
        await self.tree.set_translator(MyTranslator())

        # Start the web service
        try:
            await self.web_service.start()
            logger.info("Web service started on port 8080!")
        except Exception as e:
            logger.error(f"Failed to start web service: {e}")

    # --- Reaction Role Listeners ---
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Assign role when reaction is added."""
        if payload.member and payload.member.bot:
            return

        role_id = self.db.get_reaction_role(payload.message_id, str(payload.emoji))
        if role_id:
            logger.info(f"Reaction Role Triggered: Msg {payload.message_id}, Emoji {payload.emoji}, Role {role_id}")
            guild = self.get_guild(payload.guild_id)
            if not guild: return
            
            role = guild.get_role(int(role_id))
            if role:
                try:
                    await payload.member.add_roles(role, reason="Reaction Role assignment")
                    logger.info(f"Successfully added role {role.name} to {payload.member.name}")
                except discord.Forbidden:
                    logger.warning(f"Error: Missing permissions to add role {role.name} in {guild.name}")
                except Exception as e:
                    logger.error(f"Failed to add reaction role: {e}")

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Remove role when reaction is removed."""
        role_id = self.db.get_reaction_role(payload.message_id, str(payload.emoji))
        if role_id:
            guild = self.get_guild(payload.guild_id)
            if not guild: return
            
            role = guild.get_role(int(role_id))
            member = guild.get_member(payload.user_id)
            
            if role and member:
                try:
                    await member.remove_roles(role, reason="Reaction Role removal")
                except discord.Forbidden:
                    logger.warning(f"Error: Missing permissions to remove role {role.name} in {guild.name}")
    async def close(self):
        await self.web_service.stop()
        await super().close()

    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info('------')
        logger.info('Registered Slash Commands:')
        for cmd in self.tree.get_commands():
            logger.info(f"/{cmd.name} - {cmd.description}")
        logger.info('------')

    async def on_error(self, event, *args, **kwargs):
        logger.error(f"Error in event {event}:", exc_info=True)
        await self.send_alert(f"⚠️ **System Error in {event}**\n```python\n{args}\n```")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            # If someone tries a common misspelled command like !r1d20, alert owner
            if ctx.invoked_with and ctx.invoked_with.startswith('r') and any(char.isdigit() for char in ctx.invoked_with):
                 await self.alert_owner(f"❓ **Possible Command Typo!**\nUser: `{ctx.author}`\nTried: `!{ctx.invoked_with}`\n(Advise them to add a space!)")
            return
        
        logger.error(f"Command error: {error}", exc_info=True)
        await self.send_alert(f"❌ **Command Error: {ctx.command}**\nUser: {ctx.author}\nError: `{error}`")
        
        # Alert Owner for non-user errors OR common roll failures
        is_roll_cmd = ctx.command and str(ctx.command) in ['roll', 'r', 'multiroll', 'skill', 'attack', 'gmroll', 'gr']
        is_user_error = isinstance(error, (commands.CheckFailure, commands.UserInputError))
        
        if not is_user_error or is_roll_cmd:
             await self.alert_owner(f"🚨 **Roll/Feature Issue!**\nCommand: `!{ctx.command}`\nUser: `{ctx.author}`\nError: `{error}`")

        if ctx.command:
            await ctx.send(f"An error occurred: `{error}`")

    async def alert_owner(self, message):
        """Send a DM directly to the bot owner."""
        try:
            if not hasattr(self, 'owner_id_cache'):
                app = await self.application_info()
                self.owner_id_cache = app.owner.id
            
            owner = self.get_user(self.owner_id_cache) or await self.fetch_user(self.owner_id_cache)
            if owner:
                await owner.send(message)
        except Exception as e:
            logger.error(f"Failed to alert owner: {e}")

    async def send_alert(self, message):
        log_channel_id = os.getenv("LOG_CHANNEL_ID")
        if not log_channel_id or not log_channel_id.isdigit():
            return
            
        channel = self.get_channel(int(log_channel_id))
        if channel:
            try:
                await channel.send(message)
            except:
                pass

    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
            
        # Ignore regular bots to prevent loops, but ALLOW webhooks (Tupperbox)
        if message.author.bot and not message.webhook_id:
            return

        logger.info(
            f"on_message: guild={getattr(message.guild, 'id', 'dm')} "
            f"channel={getattr(message.channel, 'id', 'unknown')} "
            f"author={message.author.id} content={message.content[:120]!r}"
        )

        # Debug log for prefix detection
        if message.content.startswith(self.command_prefix):
            logger.info(f"Command detected: {message.content} from {message.author}")

        if message.content and message.content.lower().startswith("!debugroll"):
            await self._handle_debug_roll(message)
            return

        if message.content and message.content.lower().startswith("!debugping"):
            await self._handle_debug_ping(message)
            return

        if message.content.startswith(self.command_prefix):
            await self.process_commands(message)
        elif self.user.mentioned_in(message):
            logger.info(f"Mention detected: {message.content} from {message.author}")

        # Social Map: Sync regular messages to DB for the web map
        if message.guild:
            author_name = message.author.display_name
            # If it's a webhook (Tupperbox), try to get the original author name if possible, 
            # or just use the display name which is usually the character name.
            logger.debug(f"Saving chat message from {author_name} in {message.channel.name}")
            self.db.save_chat_message(message.guild.id, message.channel.id, author_name, message.content)

    async def _handle_debug_ping(self, message: discord.Message):
        """Tiny channel ping to verify the message event is reaching the bot."""
        await message.channel.send(
            f"✅ debug ping received in #{getattr(message.channel, 'name', 'unknown')} "
            f"from {message.author.display_name}"
        )

    async def _handle_debug_roll(self, message: discord.Message):
        """Direct, command-router-free diagnostic for roll parsing and Discord send behavior."""
        try:
            if not hasattr(self, "owner_id_cache"):
                app = await self.application_info()
                self.owner_id_cache = app.owner.id

            if message.author.id != self.owner_id_cache:
                await message.channel.send("❌ `!debugroll` is owner-only.")
                return

            expression = message.content.split(maxsplit=1)[1].strip() if len(message.content.split(maxsplit=1)) > 1 else ""
            dice_cog = self.get_cog("DiceCog")
            parse_total = parse_details = parse_error = None
            repeats = 1
            end_idx = 0
            if expression:
                parse_total, parse_details, parse_error, repeats, end_idx = self.dice_service.parse_and_roll(expression)

            payload = {
                "command": "!debugroll",
                "author": f"{message.author} ({message.author.id})",
                "guild": f"{getattr(message.guild, 'name', 'DM')} ({getattr(message.guild, 'id', 'dm')})",
                "channel": f"#{getattr(message.channel, 'name', 'unknown')} ({message.channel.id})",
                "bot_ready": self.is_ready(),
                "dice_cog_loaded": bool(dice_cog),
                "command_prefix": str(self.command_prefix),
                "expression": expression,
                "parse_total": parse_total,
                "parse_details": parse_details,
                "parse_error": parse_error,
                "parse_repeats": repeats,
                "parse_end_index": end_idx,
            }
            logger.info(f"Debug roll payload: {json.dumps(payload, ensure_ascii=False)}")
            await message.channel.send(f"```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```")
        except Exception as e:
            logger.error(f"Debug roll failed: {e}", exc_info=True)
            try:
                await message.channel.send(f"❌ Debug roll failed: `{e}`")
            except Exception:
                pass

if __name__ == '__main__':
    if not TOKEN or TOKEN == "your_token_here":
        print("Please configure your DISCORD_TOKEN in your private env file.")
        exit(1)
        
    bot = WithoutNumberBot()

    # Global language commands for bot.py
    # Discord limits choices to 25
    LANG_CHOICES = [
        app_commands.Choice(name="English", value="en"), app_commands.Choice(name="Français", value="fr"),
        app_commands.Choice(name="Español", value="es"), app_commands.Choice(name="Deutsch", value="de"),
        app_commands.Choice(name="Português", value="pt"), app_commands.Choice(name="Italiano", value="it"),
        app_commands.Choice(name="Nederlands", value="nl"), app_commands.Choice(name="Polski", value="pl"),
        app_commands.Choice(name="Русский", value="ru"), app_commands.Choice(name="Svenska", value="sv"),
        app_commands.Choice(name="日本語", value="ja"), app_commands.Choice(name="한국어", value="ko"),
        app_commands.Choice(name="中文", value="zh"), app_commands.Choice(name="Dansk", value="da"),
        app_commands.Choice(name="Suomi", value="fi"), app_commands.Choice(name="Norsk", value="no"),
        app_commands.Choice(name="Türkçe", value="tr"), app_commands.Choice(name="Čeština", value="cs"),
        app_commands.Choice(name="Ελληνικά", value="el"), app_commands.Choice(name="Magyar", value="hu"),
        app_commands.Choice(name="Română", value="ro"), app_commands.Choice(name="Tiếng Việt", value="vi"),
        app_commands.Choice(name="ไทย", value="th"), app_commands.Choice(name="Українська", value="uk"),
        app_commands.Choice(name="Bahasa Indonesia", value="id")
    ]

    @bot.tree.command(name="language", description="Set your preferred language for bot responses.")
    @app_commands.describe(lang="Choose a language from the list")
    @app_commands.choices(lang=LANG_CHOICES)
    async def language_set_bot(interaction: discord.Interaction, lang: str):
        # Save to database
        interaction.client.db.set_setting(interaction.user.id, "language", lang)
        
        # Get localized success message
        msg = localizer.translate("commands.lang_set_success", lang, lang=lang.upper())
        await interaction.response.send_message(msg, ephemeral=True)

    @bot.command(name="language", help="Set your preferred language. Usage: !language [code] (e.g. en, fr, es, ja, zh)")
    async def language_prefix_bot(ctx, lang: str = "en"):
        lang = lang.lower()
        valid_codes = [c.value for c in LANG_CHOICES]
        if lang not in valid_codes:
            msg = localizer.translate("commands.lang_invalid", "en")
            await ctx.send(msg + f" Valid codes: {', '.join(valid_codes[:10])}...")
            return
            
        ctx.bot.db.set_setting(ctx.author.id, "language", lang)
        msg = localizer.translate("commands.lang_set_success", lang, lang=lang.upper())
        await ctx.send(msg)

    @bot.tree.command(name="health", description="Run bot diagnostics.")
    async def health_slash(interaction: discord.Interaction):
        await perform_health_check(interaction)

    @bot.command(name="health", help="Run bot diagnostics.")
    async def health_prefix(ctx):
        await perform_health_check(ctx)

    async def perform_health_check(target):
        is_int = isinstance(target, discord.Interaction)
        bot = target.client if is_int else target.bot
        owner_id = (await bot.application_info()).owner.id
        user_id = target.user.id if is_int else target.author.id
        
        if user_id != owner_id:
            msg = "❌ This command is restricted to the bot owner."
            if is_int: await target.response.send_message(msg, ephemeral=True)
            else: await target.send(msg)
            return

        # 1. DB Check
        db_ok = "🟢 OK"
        try:
            bot.db.get_user_characters(0)
        except:
            db_ok = "🔴 ERROR"
            
        # 2. Cogs Check
        loaded_cogs = list(bot.cogs.keys())
        expected = ['DiceCog', 'CharacterSheetCog', 'CompendiumCog'] # Core ones
        missing = [c for c in expected if c not in loaded_cogs]
        cogs_ok = "🟢 All Core Loaded" if not missing else f"🔴 Missing: {', '.join(missing)}"
        
        embed = discord.Embed(title="🏥 Bot Health Diagnostic", color=discord.Color.blue())
        embed.add_field(name="Database", value=db_ok, inline=True)
        embed.add_field(name="Core Cogs", value=cogs_ok, inline=True)
        embed.add_field(name="Guilds", value=str(len(bot.guilds)), inline=True)
        embed.add_field(name="Uptime", value=str(datetime.datetime.now() - bot.start_time).split('.')[0], inline=True)
        
        owner_id = (await bot.application_info()).owner.id
        user_id = target.user.id if is_int else target.author.id
        
        # Hide sensitive info if not owner
        if user_id == owner_id:
            embed.add_field(name="Log Level", value=logging.getLevelName(logger.level), inline=True)
            embed.set_footer(text="Diagnostic run by Owner")
        else:
            embed.set_footer(text="Basic Health Check")

        send = target.response.send_message if is_int else target.send
        await send(embed=embed)

    bot.run(TOKEN)
