import discord
from discord import app_commands
from discord.ext import commands
import csv
import io
import aiohttp
import json
import os
import re
from cogs.ui.character_selector import CharacterSelectorView
import urllib.parse

class ImportTextModal(discord.ui.Modal, title='Import from characterswithoutnumber.app'):
    character_text = discord.ui.TextInput(
        label='Paste "Copy Text" Output Here',
        style=discord.TextStyle.paragraph,
        placeholder='e.g. Rey Chen\nLevel 1 Expert\nSpacer\n\nHP: 1\nAC: 10\n...',
        required=True,
        max_length=4000
    )

    def __init__(self, cog, system):
        super().__init__()
        self.cog = cog
        self.system = system

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        text = self.character_text.value
        char_data, error = self.cog.parse_cwn_app_text(text, self.system)
        if error:
            await interaction.followup.send(f"❌ Error parsing text: {error}")
            return
            
        safe_name, is_update = self.cog.save_character(interaction.user.id, char_data)
        verb = "Updated" if is_update else "Imported"
        embed = discord.Embed(title=f"✅ Character {verb}: {safe_name}", color=discord.Color.green())
        embed.description = f"Level {char_data['level']} {char_data['class']} ({self.system})"
        embed.add_field(name="HP", value=str(char_data['hp']), inline=True)
        embed.add_field(name="AC", value=str(char_data['ac']), inline=True)
        embed.add_field(name="Attack Bonus", value=f"+{char_data['attack_bonus']}", inline=True)
        embed.set_footer(text=f"Imported {len(char_data['skills'])} skills.")
        await interaction.followup.send(embed=embed)

class CharacterSheetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.char_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'characters')
        os.makedirs(self.char_dir, exist_ok=True)
        self.awn_sheet_gid = "989086139" # Default GID for AWN Character Sheet tab
        
    async def get_active_character_data(self, ctx_or_int, allow_none=False):
        """Smart helper to get character data for a channel. 
        If allow_none=True, will return None instead of erroring for guest users."""
        is_int = isinstance(ctx_or_int, discord.Interaction)
        user_id = ctx_or_int.user.id if is_int else ctx_or_int.author.id
        channel = ctx_or_int.channel
        channel_id = str(channel.id)
        category_id = str(channel.category_id) if hasattr(channel, 'category_id') and channel.category_id else None
        
        char_data = self.bot.db.get_active_character(user_id, channel_id, category_id)
        char_names = self.bot.db.get_user_characters(user_id)
        if not char_names:
            if allow_none: return None
            
            msg = "❌ You have no characters! Use `/importtext` or drag-and-drop a JSON to load one."
            if is_int: await (ctx_or_int.followup.send if ctx_or_int.response.is_done() else ctx_or_int.response.send_message)(msg, ephemeral=True)
            else: await ctx_or_int.send(msg)
            return None

        if char_data: return char_data

        if len(char_names) == 1:
            char_name = char_names[0]
            target_id = category_id or channel_id
            self.bot.db.bind_character(user_id, target_id, 'category' if category_id else 'channel', char_name)
            return self.bot.db.get_character(user_id, char_name)

        view = CharacterSelectorView(user_id, char_names, has_category=bool(category_id))
        prompt = f"🎭 Which character are you playing in **{channel.category.name if category_id else channel.name}**?"
        if is_int:
            if not ctx_or_int.response.is_done(): await ctx_or_int.response.send_message(prompt, view=view, ephemeral=True)
            else: await ctx_or_int.followup.send(prompt, view=view, ephemeral=True)
        else:
            await ctx_or_int.send(prompt, view=view)

        await view.wait()
        if view.selected_value:
            target_id = category_id if view.selected_scope == 'category' else channel_id
            self.bot.db.bind_character(user_id, target_id, view.selected_scope, view.selected_value)
            return self.bot.db.get_character(user_id, view.selected_value)
        return None

    def save_character(self, user_id, char_data, name_override=None, source_url=None):
        char_name = name_override or char_data.get('name', 'Unknown')
        safe_name = "".join([c for c in char_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        is_update = self.bot.db.get_character(user_id, safe_name) is not None
        self.bot.db.save_character(user_id, safe_name, char_data.get('system', 'SWN'), char_data, source_url)
        return safe_name, is_update

    @app_commands.command(name="sheet")
    async def sheet_slash(self, interaction: discord.Interaction, view: str = "combat"):
        char_data = await self.get_active_character_data(interaction)
        if char_data: await self._send_sheet_embed(interaction, char_data, view)

    @commands.command(name="sheet", aliases=["s", "sc", "sf"])
    async def sheet_prefix(self, ctx, view: str = "combat"):
        if ctx.invoked_with == "sc": view = "combat"
        elif ctx.invoked_with == "sf": view = "full"
        char_data = await self.get_active_character_data(ctx)
        if char_data: await self._send_sheet_embed(ctx, char_data, view)

    async def _send_sheet_embed(self, target, char_data, view):
        is_int = isinstance(target, discord.Interaction)
        system_display = char_data.get('system', 'SWN').upper()
        color = discord.Color.blue()
        if system_display == "WWN": color = discord.Color.dark_red()
        elif system_display == "CWN": color = discord.Color.dark_grey()
            
        embed = discord.Embed(title=f"Character Sheet: {char_data['name']}", color=color)
        embed.set_author(name=f"Level {char_data['level']} {char_data.get('class', 'Hero')} ({system_display})")
        if char_data.get('portrait_url'): embed.set_thumbnail(url=char_data['portrait_url'])
        
        embed.add_field(name="Combat", value=f"**HP:** {char_data['hp']}  |  **AC:** {char_data['ac']}  |  **Attack Bonus:** +{char_data['attack_bonus']}", inline=False)
        embed.add_field(name="Attributes", value=", ".join([f"**{k.upper()}**: {v:+d}" for k, v in char_data['attributes'].items()]), inline=False)
        
        trained = {k: v for k, v in char_data.get('skills', {}).items() if v >= 0}
        if trained: embed.add_field(name="Skills", value=", ".join([f"{k.capitalize()} {v:+d}" for k, v in trained.items()]), inline=False)
        
        if char_data.get('weapons'):
            embed.add_field(name="Weapons", value="\n".join([f"• **{w['name']}**: To Hit {w['to_hit']:+d}, Dmg {w['damage']}" for w in char_data['weapons']]), inline=False)
            
        if view == "full":
            if char_data.get('foci'): embed.add_field(name="Foci", value=", ".join(char_data['foci']), inline=False)
            if char_data.get('equipment'):
                eq_text = ", ".join(char_data['equipment'])
                embed.add_field(name="Equipment", value=eq_text[:1020] + "..." if len(eq_text)>1024 else eq_text, inline=False)

        send = target.followup.send if is_int else target.send
        await send(embed=embed)

    @app_commands.command(name="portrait")
    async def portrait_slash(self, interaction: discord.Interaction, url: str = None, name: str = None):
        user_id = interaction.user.id
        char_names = self.bot.db.get_user_characters(user_id)
        if not char_names:
            await interaction.response.send_message("❌ Import a character first!", ephemeral=True)
            return
        target_char = name or (char_names[0] if len(char_names)==1 else None)
        if not target_char:
            view = CharacterSelectorView(user_id, char_names)
            await interaction.response.send_message("🖼️ Which character?", view=view, ephemeral=True)
            await view.wait()
            target_char = view.selected_value
        if target_char: await self._set_portrait(interaction, target_char, url)

    @commands.command(name="portrait")
    async def portrait_prefix(self, ctx, url: str = None):
        user_id = ctx.author.id
        char_data = await self.get_active_character_data(ctx)
        if char_data: await self._set_portrait(ctx, char_data['name'], url)

    async def _set_portrait(self, target, char_name, url):
        is_int = isinstance(target, discord.Interaction)
        image_url = url or (target.message.attachments[0].url if not is_int and target.message.attachments else None)
        if not image_url:
            msg = "❌ Provide a URL or attach an image."
            send = target.followup.send if is_int else target.send
            await send(msg)
            return
        char_data = self.bot.db.get_character(target.user.id if is_int else target.author.id, char_name)
        char_data['portrait_url'] = image_url
        self.bot.db.save_character(target.user.id if is_int else target.author.id, char_name, char_data.get('system', 'SWN'), char_data)
        embed = discord.Embed(title=f"✅ Portrait Set for {char_name}", color=discord.Color.green())
        embed.set_thumbnail(url=image_url)
        send = target.followup.send if is_int else target.send
        await send(embed=embed)

    @app_commands.command(name="bind")
    async def bind_slash(self, interaction: discord.Interaction, name: str = None, scope: str = "category"):
        await self._perform_bind(interaction, name, scope)

    @commands.command(name="bind")
    async def bind_prefix(self, ctx, name: str = None, scope: str = "category"):
        await self._perform_bind(ctx, name, scope)

    async def _perform_bind(self, target, name, scope):
        is_int = isinstance(target, discord.Interaction)
        user = target.user if is_int else target.author
        char_names = self.bot.db.get_user_characters(user.id)
        if not char_names:
            msg = "❌ No characters found."
            send = target.followup.send if is_int else target.send
            await send(msg)
            return
        target_char = name
        if not target_char:
            view = CharacterSelectorView(user.id, char_names, has_category=True)
            prompt = "🎭 Bind which character?"
            send = target.response.send_message if is_int and not target.response.is_done() else target.send
            await (send(prompt, view=view, ephemeral=True) if is_int else send(prompt, view=view))
            await view.wait()
            if not view.selected_value: return
            target_char, scope = view.selected_value, view.selected_scope
        
        target_id = target.channel.id if not scope=="category" else (target.channel.category_id or target.channel.id)
        real_scope = scope if (scope=="category" and target.channel.category_id) else "channel"
        self.bot.db.bind_character(user.id, target_id, real_scope, target_char)
        await (target.followup.send if is_int else target.send)(f"✅ Bound **{target_char}** to {real_scope}.")

    @app_commands.command(name="importtext")
    async def importtext(self, interaction: discord.Interaction, system: str = "SWN"):
        await interaction.response.send_modal(ImportTextModal(self, system))

    @app_commands.command(name="importsheet", description="Import a character from a Google Sheet (AWN Template)")
    @app_commands.describe(url="The Google Sheet URL")
    async def importsheet_slash(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        char_data, error = await self.fetch_and_parse_sheet(url)
        if error:
            await interaction.followup.send(f"❌ Error: {error}")
            return
            
        safe_name, is_update = self.save_character(interaction.user.id, char_data, source_url=url)
        verb = "Updated" if is_update else "Imported"
        await interaction.followup.send(f"✅ {verb} **{safe_name}** from Google Sheets!")

    @commands.command(name="importsheet")
    async def importsheet_prefix(self, ctx, url: str):
        char_data, error = await self.fetch_and_parse_sheet(url)
        if error:
            await ctx.send(f"❌ Error: {error}")
            return
            
        safe_name, is_update = self.save_character(ctx.author.id, char_data, source_url=url)
        verb = "Updated" if is_update else "Imported"
        await ctx.send(f"✅ {verb} **{safe_name}** from Google Sheets!")

    @app_commands.command(name="sync", description="Sync your active character from its Google Sheet source.")
    async def sync_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        char_data = await self.get_active_character_data(interaction)
        if not char_data or not char_data.get('source_url'):
            await interaction.followup.send("❌ Active character has no Google Sheet link. Use `/importsheet` first.")
            return
            
        new_data, error = await self.fetch_and_parse_sheet(char_data['source_url'])
        if error:
            await interaction.followup.send(f"❌ Sync failed: {error}")
            return
            
        self.save_character(interaction.user.id, new_data, source_url=char_data['source_url'])
        await interaction.followup.send(f"🔄 Synced **{char_data['name']}**!")

    @app_commands.command(name="update", description="Instantly refresh your active character stats from its stored source URL.")
    async def update_slash(self, interaction: discord.Interaction):
        await self.sync_slash(interaction)

    @commands.command(name="update", aliases=["up"])
    async def update_prefix(self, ctx):
        await self.sync_prefix(ctx)

    @commands.command(name="sync")
    async def sync_prefix(self, ctx):
        char_data = await self.get_active_character_data(ctx)
        if not char_data or not char_data.get('source_url'):
            await ctx.send("❌ Active character has no Google Sheet link.")
            return
            
        new_data, error = await self.fetch_and_parse_sheet(char_data['source_url'])
        if error:
            await ctx.send(f"❌ Sync failed: {error}")
            return
            
        self.save_character(ctx.author.id, new_data, source_url=char_data['source_url'])
        await ctx.send(f"🔄 Synced **{char_data['name']}**!")

    @app_commands.command(name="importjson", description="Import a character from a raw JSON URL.")
    @app_commands.describe(url="The JSON URL")
    async def importjson_slash(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        char_data, error = await self.fetch_json_character(url)
        if error:
            await interaction.followup.send(f"❌ Error: {error}")
            return
            
        safe_name, is_update = self.save_character(interaction.user.id, char_data, source_url=url)
        verb = "Updated" if is_update else "Imported"
        await interaction.followup.send(f"✅ {verb} **{safe_name}** from JSON source!")

    @commands.command(name="importjson")
    async def importjson_prefix(self, ctx, url: str):
        char_data, error = await self.fetch_json_character(url)
        if error:
            await ctx.send(f"❌ Error: {error}")
            return
            
        safe_name, is_update = self.save_character(ctx.author.id, char_data, source_url=url)
        verb = "Updated" if is_update else "Imported"
        await ctx.send(f"✅ {verb} **{safe_name}** from JSON source!")

    async def fetch_json_character(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None, f"Failed to download JSON (Status {resp.status})."
                    data = await resp.json()
                    # Basic validation: ensure name exists
                    if 'name' not in data and 'character_name' not in data:
                        return None, "Invalid character JSON format."
                    if 'character_name' in data and 'name' not in data:
                        data['name'] = data['character_name']
                    return data, None
        except Exception as e:
            return None, str(e)

    async def fetch_and_parse_sheet(self, url):
        # Extract Sheet ID and GID
        if url.endswith('.json') or 'json' in url.lower():
             return await self.fetch_json_character(url)
             
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not match: return None, "Invalid Google Sheet URL."
        sheet_id = match.group(1)
        
        gid = self.awn_sheet_gid
        gid_match = re.search(r'gid=([0-9]+)', url)
        if gid_match: gid = gid_match.group(1)
        
        # AWN template specific: If user provides the Welcome tab GID, switch to Character Sheet GID
        if gid == "1671565117": gid = self.awn_sheet_gid
        
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(csv_url) as resp:
                    if resp.status != 200:
                        return None, f"Failed to download sheet (Status {resp.status}). Is it shared as 'Anyone with the link can view'?"
                    content = await resp.text()
                    return self.parse_awn_google_sheet(content)
        except Exception as e:
            return None, str(e)

    def parse_awn_google_sheet(self, csv_text):
        try:
            f = io.StringIO(csv_text)
            reader = list(csv.reader(f))
            
            # Helper to get value safely
            def get_val(r, c, default=""):
                try: return reader[r][c].strip()
                except: return default

            # Detect if this is the AWN template
            # Row 2, Col 2 (B2) should be "Name" or similar
            if get_val(1, 1).lower() != "name":
                return None, "This doesn't look like the AWN Character Sheet template (Missing 'Name' label in B2)."

            char_data = {
                'name': get_val(1, 3) or get_val(1, 4) or get_val(1, 5), # Merged cell D2:G2
                'level': int(get_val(3, 2) or 1),
                'hp': int(re.search(r'(\d+)', get_val(2, 33) or "0").group(1) if re.search(r'(\d+)', get_val(2, 33) or "") else 0), # AH3 often has "/ MaxHP"
                'ac': int(get_val(5, 33) or 10), # AH6 is AC
                'attack_bonus': int(get_val(4, 33) or 0), # AH5 is Attack Bonus
                'attributes': {
                    'strength': int(get_val(8, 10) or 0),
                    'dexterity': int(get_val(9, 10) or 0),
                    'constitution': int(get_val(10, 10) or 0),
                    'intelligence': int(get_val(11, 10) or 0),
                    'wisdom': int(get_val(12, 10) or 0),
                    'charisma': int(get_val(13, 10) or 0)
                },
                'skills': {},
                'weapons': [],
                'system': 'AWN'
            }

            # If name is still empty, use a fallback
            if not char_data['name']: char_data['name'] = "Unknown Survivor"

            # Parse Skills (Row 17 to 35, Col 9)
            for i in range(16, 35):
                s_name = get_val(i, 8).lower()
                s_val = get_val(i, 11)
                if s_name and s_val:
                    try: char_data['skills'][s_name] = int(s_val)
                    except: pass

            # Parse Weapons (Row 10 to 18, Col 22)
            for i in range(9, 17):
                w_name = get_val(i, 21)
                if w_name and w_name != "-":
                    char_data['weapons'].append({
                        'name': w_name,
                        'to_hit': int(get_val(i, 22).replace('+', '') or 0),
                        'damage': get_val(i, 23)
                    })

            return char_data, None
        except Exception as e:
            return None, f"Parsing error: {str(e)}"

    def parse_cwn_app_text(self, text, system):
        lines = text.split('\n')
        char_data = {'name': lines[0].strip(), 'level': 1, 'class': 'Expert', 'hp': 0, 'ac': 10, 'attack_bonus': 0, 'attributes': {}, 'skills': {}, 'weapons': [], 'system': system}
        try:
            for line in lines:
                if 'HP:' in line: char_data['hp'] = int(re.search(r'HP:\s*(\d+)', line).group(1))
                if 'AC:' in line: char_data['ac'] = int(re.search(r'AC:\s*(\d+)', line).group(1))
                if 'Attack Bonus:' in line: char_data['attack_bonus'] = int(re.search(r'Attack Bonus:\s*\+?(-?\d+)', line).group(1))
            return char_data, None
        except Exception as e: return None, str(e)

async def setup(bot):
    await bot.add_cog(CharacterSheetCog(bot))
