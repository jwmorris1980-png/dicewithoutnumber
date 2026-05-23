import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import re
from typing import Optional
from services.map_service import MapRenderer
from services.permissions import is_gm_check

class MapMovementView(discord.ui.View):
    def __init__(self, cog, guild_id, channel_id, combatants, current_selection=None):
        self.channel_id = channel_id
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.combatants = combatants
        self.current_selection = current_selection
        
        # Row 0: Token selector
        if self.combatants:
            options = []
            for c in self.combatants[:25]:
                label = f"{c['name']}"
                if c.get('x') is not None:
                    label += f" ({chr(ord('A') + c['x'])}{c['y'] + 1})"
                else:
                    label += " (BENCHED)"
                
                options.append(discord.SelectOption(
                    label=label,
                    value=str(c['id']),
                    default=(str(c['id']) == str(current_selection))
                ))
            
            select = discord.ui.Select(
                placeholder="Select a token...",
                options=options,
                custom_id="select_token",
                row=0
            )
            select.callback = self.select_callback
            self.add_item(select)

        # Only show movement buttons if selected token is on grid
        selected_obj = next((c for c in combatants if str(c['id']) == str(current_selection)), None)
        if selected_obj:
            if selected_obj.get('x') is not None:
                pass # The @discord.ui.button decorators handle these
            else:
                deploy_btn = discord.ui.Button(label="🚀 Deploy to A1", style=discord.ButtonStyle.green, custom_id="deploy_btn", row=1)
                deploy_btn.callback = self.deploy_callback
                self.add_item(deploy_btn)

        # Row 4: Terrain/Theme selector
        data = cog.get_guild_tracker(guild_id)
        current_theme = data.get("theme", "default")
        options = [
            discord.SelectOption(label="🌌 Space / Void", value="default", description="The standard black void", default=current_theme == "default"),
            discord.SelectOption(label="🌲 Forest", value="forest", description="Dense green vegetation", default=current_theme == "forest"),
            discord.SelectOption(label="🦇 Cave", value="cave", description="Dark stony corridors", default=current_theme == "cave"),
            discord.SelectOption(label="🏜️ Desert", value="desert", description="Arid sands", default=current_theme == "desert")
        ]
        
        # Add custom option if background exists
        if data.get("background_url"):
            options.append(discord.SelectOption(label="🖼️ Custom Map", value="custom", description="Your uploaded map image", default=current_theme == "custom"))

        theme_select = discord.ui.Select(
            placeholder="Select Terrain Theme...",
            options=options,
            custom_id="select_theme",
            row=4
        )
        theme_select.callback = self.theme_callback
        self.add_item(theme_select)

    async def select_callback(self, interaction: discord.Interaction):
        self.current_selection = int(interaction.data['values'][0])
        await self.update_view(interaction)

    async def theme_callback(self, interaction: discord.Interaction):
        new_theme = interaction.data['values'][0]
        data = self.cog.get_guild_tracker(self.guild_id, self.channel_id)
        data["theme"] = new_theme
        self.cog.save_guild_tracker(self.guild_id, data, self.channel_id)
        await self.update_view(interaction)

    async def deploy_callback(self, interaction: discord.Interaction):
        if not self.current_selection: return
        data = self.cog.get_guild_tracker(self.guild_id, self.channel_id)
        combatant = next((c for c in data["combatants"] if c["id"] == self.current_selection), None)
        if combatant:
            combatant['x'] = 0
            combatant['y'] = 0
            self.cog.save_guild_tracker(self.guild_id, data, self.channel_id)
            await self.update_view(interaction)

    @discord.ui.button(label="↑", style=discord.ButtonStyle.gray, row=1)
    async def up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move(interaction, 0, -1)

    @discord.ui.button(label="←", style=discord.ButtonStyle.gray, row=2)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move(interaction, -1, 0)

    @discord.ui.button(label="→", style=discord.ButtonStyle.gray, row=2)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move(interaction, 1, 0)

    @discord.ui.button(label="↓", style=discord.ButtonStyle.gray, row=3)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move(interaction, 0, 1)

    async def move(self, interaction: discord.Interaction, dx, dy):
        if not self.current_selection:
            await interaction.response.send_message("Please select a token first!", ephemeral=True)
            return
            
        data = self.cog.get_guild_tracker(self.guild_id, self.channel_id)
        combatant = next((c for c in data["combatants"] if c["id"] == self.current_selection), None)
        
        if combatant and combatant.get('x') is not None:
            new_x = max(0, min(9, combatant['x'] + dx))
            new_y = max(0, min(9, combatant['y'] + dy))
            combatant['x'] = new_x
            combatant['y'] = new_y
            self.cog.save_guild_tracker(self.guild_id, data, self.channel_id)
            await self.update_view(interaction)
        else:
            await interaction.response.send_message("Selected token not on grid! Deploy it first.", ephemeral=True)

    def _get_background_path(self, data):
        background_url = data.get("background_url")
        if background_url:
            filename = background_url.split("/")[-1]
            path = os.path.join("data", "maps", filename)
            if os.path.exists(path):
                return path
        return None

    async def update_view(self, interaction: discord.Interaction):
        # Re-render map and update message
        data = self.cog.get_guild_tracker(self.guild_id, self.channel_id)
        theme = data.get("theme", "default")
        background_path = self._get_background_path(data)
        grid_type = data.get("grid_type", "square")
        buffer = self.cog.map_renderer.render_map(data["combatants"], theme_name=theme, background_path=background_path, grid_type=grid_type)
        file = discord.File(fp=buffer, filename="map.png")
        
        embed = discord.Embed(title="🗺️ Tactical Map", color=discord.Color.blue())
        embed.set_image(url="attachment://map.png")
        
        ip = "147.182.248.196"
        link = f"http://{ip}:8080/map?guild_id={self.guild_id}&channel_id={self.channel_id}"
        
        on_grid = [c for c in data["combatants"] if c.get('x') is not None]
        bg_notice = "\n🎨 *Custom Background Active*" if background_path else ""
        if not on_grid:
            embed.description = f"🔗 [**Open Interactive Map**]({link})\n⚠️ **Grid is empty.** Deploy tokens from the **Bench** using the selector below or the website.{bg_notice}"
        else:
            embed.description = f"🔗 [**Open Interactive Map**]({link})\nMove tokens with buttons or mouse!{bg_notice}"
        
        if self.current_selection:
            sel = next((c for c in data["combatants"] if c["id"] == self.current_selection), None)
            if sel:
                pos = f"({chr(ord('A') + sel['x'])}{sel['y'] + 1})" if sel.get('x') is not None else "Bench"
                embed.set_footer(text=f"Selected: {sel['name']} at {pos} | Theme: {theme.capitalize()}")

        new_view = MapMovementView(self.cog, self.guild_id, self.channel_id, data["combatants"], self.current_selection)
        await interaction.response.edit_message(attachments=[file], embed=embed, view=new_view)

class TacticalControllerView(discord.ui.View):
    def __init__(self, cog, guild_id, channel_id):
        self.channel_id = channel_id
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self._setup_grid()

    def _get_data(self):
        return self.cog.get_guild_tracker(self.guild_id, self.channel_id)

    def _setup_grid(self):
        self.clear_items()
        data = self._get_data()
        vx = data.get("viewport_x", 0)
        vy = data.get("viewport_y", 0)
        mode = data.get("interaction_mode", "move")
        sel_id = data.get("active_selection_id")
        drawings = data.get("drawings", [])
        combatants = data["combatants"]

        # Grid Buttons (4x4)
        for r in range(4):
            for c in range(5):
                if c == 4: continue # Row limit helper
                mx, my = vx + c, vy + r
                label = f"{chr(ord('A')+mx)}{my+1}"
                style = discord.ButtonStyle.gray
                emoji = None
                
                # Check for token
                token = next((t for t in combatants if t.get('x') == mx and t.get('y') == my), None)
                if token:
                    emoji = "👤" if not token.get('is_enemy') else "👹"
                    if str(token['id']) == str(sel_id):
                        emoji = "🎯"
                        style = discord.ButtonStyle.primary
                
                # Check for drawing (paint)
                is_painted = any(d['x'] == mx and d['y'] == my for d in drawings)
                if is_painted:
                    style = discord.ButtonStyle.danger
                    if not emoji: emoji = "🟥"

                btn = discord.ui.Button(label=label, emoji=emoji, style=style, row=r)
                btn.callback = self._make_callback(mx, my)
                self.add_item(btn)

        # Control Row (Row 4)
        nav_buttons = [
            ("⬅️", -1, 0), ("🔼", 0, -1), ("🔽", 0, 1), ("➡️", 1, 0)
        ]
        for label, dx, dy in nav_buttons:
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, row=4)
            btn.callback = self._make_nav_callback(dx, dy)
            self.add_item(btn)

        # Settings/Mode button
        mode_label = "🎨 Paint" if mode == "move" else "♟️ Move"
        mode_btn = discord.ui.Button(label=mode_label, style=discord.ButtonStyle.green, row=4)
        mode_btn.callback = self._mode_callback
        self.add_item(mode_btn)

    def _make_callback(self, mx, my):
        async def callback(interaction: discord.Interaction):
            data = self._get_data()
            mode = data.get("interaction_mode", "move")
            sel_id = data.get("active_selection_id")
            
            if mode == "move":
                # Check if clicking on someone to select
                token = next((t for t in data["combatants"] if t.get('x') == mx and t.get('y') == my), None)
                if token:
                    data["active_selection_id"] = token["id"]
                elif sel_id:
                    # Move selected token
                    token = next((t for t in data["combatants"] if str(t['id']) == str(sel_id)), None)
                    if token:
                        token["x"] = mx
                        token["y"] = my
                else:
                    await interaction.response.send_message("Click a token first to select it!", ephemeral=True)
                    return
            else: # paint mode
                if "drawings" not in data: data["drawings"] = []
                drawings = data["drawings"]
                existing = next((i for i, d in enumerate(drawings) if d['x'] == mx and d['y'] == my), None)
                if existing is not None:
                    drawings.pop(existing)
                else:
                    drawings.append({"x": mx, "y": my, "color": "red"})
                data["drawings"] = drawings
            
            self.cog.save_guild_tracker(self.guild_id, data, self.channel_id)
            await self._update_message(interaction)
        return callback

    def _make_nav_callback(self, dx, dy):
        async def callback(interaction: discord.Interaction):
            data = self._get_data()
            vx = max(0, min(6, data.get("viewport_x", 0) + dx))
            vy = max(0, min(6, data.get("viewport_y", 0) + dy))
            data["viewport_x"] = vx
            data["viewport_y"] = vy
            self.cog.save_guild_tracker(self.guild_id, data, self.channel_id)
            await self._update_message(interaction)
        return callback

    async def _mode_callback(self, interaction: discord.Interaction):
        data = self._get_data()
        data["interaction_mode"] = "paint" if data.get("interaction_mode", "move") == "move" else "move"
        self.cog.save_guild_tracker(self.guild_id, data, self.channel_id)
        await self._update_message(interaction)

    async def _update_message(self, interaction: discord.Interaction):
        data = self._get_data()
        theme = data.get("theme", "default")
        background_path = self.cog._get_background_path(data)
        vx, vy = data.get("viewport_x", 0), data.get("viewport_y", 0)
        sel_id = data.get("active_selection_id")
        drawings = data.get("drawings", [])
        
        grid_type = data.get("grid_type", "square")
        buffer = self.cog.map_renderer.render_map(
            data["combatants"], 
            theme_name=theme, 
            background_path=background_path,
            drawings=drawings,
            viewport=(vx, vy),
            selection_id=sel_id,
            grid_type=grid_type
        )
        file = discord.File(fp=buffer, filename="map.png")
        
        embed = discord.Embed(title="🎮 Tactical Controller", color=discord.Color.green())
        embed.set_image(url="attachment://map.png")
        mode = data.get("interaction_mode", "move").upper()
        embed.description = f"**Mode:** {mode}\nUse grid buttons to interact. Viewport: {chr(ord('A')+vx)}{vy+1} to {chr(ord('A')+vx+3)}{vy+4}"
        
        self._setup_grid()
        await interaction.response.edit_message(attachments=[file], embed=embed, view=self)

@app_commands.guild_only()
class TrackerCog(commands.GroupCog, group_name="tracker", description="Manage combat initiative, HP, and tactical maps."):
    def __init__(self, bot):
        self.bot = bot
        self.tracker_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'trackers')
        os.makedirs(self.tracker_dir, exist_ok=True)
        self.map_renderer = MapRenderer()

    def parse_coords(self, coord_str: str):
        """Parses coordinates like 'A1', 'B2', or '1,1' into (x, y) integers."""
        if not coord_str:
            return None, None
            
        # Try '1,1' or '1 1' format
        match = re.match(r'(\d+)[,\s]+(\d+)', coord_str)
        if match:
            return int(match.group(1)) - 1, int(match.group(2)) - 1
            
        # Try 'A1' or 'B10' format
        match = re.match(r'([A-Za-z])(\d+)', coord_str)
        if match:
            col = ord(match.group(1).upper()) - ord('A')
            row = int(match.group(2)) - 1
            return col, row
            
        return None, None
        
    def get_guild_tracker(self, guild_id: int, channel_id: int = "default"):
        """Loads a guild's active combat tracker from the database."""
        data = self.bot.db.get_tracker(guild_id, str(channel_id))
        if data:
            if "current_turn_index" not in data: data["current_turn_index"] = -1
            if "theme" not in data: data["theme"] = "default"
            if "background_url" not in data: data["background_url"] = None
            if "viewport_x" not in data: data["viewport_x"] = 0
            if "viewport_y" not in data: data["viewport_y"] = 0
            if "interaction_mode" not in data: data["interaction_mode"] = "move"
            if "drawings" not in data: data["drawings"] = []
            if "active_channel_id" not in data: data["active_channel_id"] = None
            return data
        return {"combatants": [], "current_turn_index": -1, "theme": "default", "background_url": None, "viewport_x": 0, "viewport_y": 0, "interaction_mode": "move", "drawings": [], "active_channel_id": None}
        
    def save_guild_tracker(self, guild_id: int, data: dict, channel_id: int = "default"):
        """Saves a guild's combat tracker to the database."""
        """Saves a guild's combat tracker to the database."""
        self.bot.db.save_tracker(guild_id, data, str(channel_id))

    def _get_background_path(self, data: dict):
        """Helper to resolve the background image path from data."""
        background_url = data.get("background_url")
        if background_url:
            filename = background_url.split("/")[-1]
            
            # Check data/maps first (from old slash command uploads)
            path1 = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'maps', filename)
            if os.path.exists(path1):
                return path1
                
            # Check web/assets (from web uploads)
            path2 = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'assets', filename)
            if os.path.exists(path2):
                return path2
                
        return None

    def _get_status(self, current_hp: int, max_hp: int):
        """Returns a string describing the health state without showing exact numbers."""
        if current_hp <= 0:
            return "💀 **Dead**"
        
        ratio = current_hp / max_hp
        if ratio >= 0.9:
            return "🟢 **Healthy**"
        elif ratio >= 0.5:
            return "🟡 **Injured**"
        elif ratio >= 0.2:
            return "🟠 **Bloodied**"
        else:
            return "🔴 **Critical**"

    async def target_autocomplete(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        choices = [
            app_commands.Choice(name=f"{c['name']} (HP: {c['current_hp']}/{c['max_hp']})", value=c['name'])
            for c in data["combatants"] if current.lower() in c['name'].lower()
        ]
        return choices[:25]

    @app_commands.command(name="add", description="Add one or more enemies to the combat tracker.")
    @app_commands.describe(
        name="Name of the character (e.g. 'Goblin')", 
        hp="Starting/Max HP", 
        ac="Armor Class (e.g. 15)", 
        quantity="How many to add (default 1)",
        coords="Optional: starting coords (e.g. 'A1')", 
        distance="Optional: starting distance (e.g. '10m')"
    )
    @is_gm_check()
    async def add(self, interaction: discord.Interaction, name: str, hp: int, ac: int, quantity: int = 1, coords: str = None, distance: str = None):
        """Add new enemies to the tracker."""
        await interaction.response.defer()
        
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        x, y = self.parse_coords(coords) if coords else (None, None)
        
        added_names = []
        for _ in range(max(1, min(quantity, 50))):
            # Determine new ID (internal)
            new_id = 1
            if data["combatants"]:
                 new_id = max([c["id"] for c in data["combatants"]]) + 1
                 
            # Handle duplicate names
            final_name = name
            count = 1
            existing_names = [c["name"].lower() for c in data["combatants"]]
            while final_name.lower() in existing_names:
                count += 1
                final_name = f"{name} {count}"
                
            data["combatants"].append({
                "id": new_id,
                "name": final_name,
                "max_hp": hp,
                "current_hp": hp,
                "ac": ac,
                "hidden": False,
                "conditions": [],
                "distance": distance or "",
                "x": x,
                "y": y,
                "is_enemy": True
            })
            added_names.append(final_name)
        
        self.save_guild_tracker(guild_id, data, channel_id)
        if quantity > 1:
            msg = f"✅ Added **{len(added_names)}x {name}** to the tracker: {', '.join(added_names[:5])}"
            if len(added_names) > 5: msg += f" and {len(added_names)-5} more."
        else:
            msg = f"✅ Added **{added_names[0]}** (HP: {hp}, AC: {ac}) to the tracker."
            if x is not None:
                msg += f" Position: {coords.upper()}."
            if distance:
                msg += f" Distance: {distance}."
            
        await interaction.followup.send(msg)

    @app_commands.command(name="import", description="Import a sector map JSON from the 3D Map Generator.")
    @app_commands.describe(file="The .json file exported from the generator")
    @is_gm_check()
    async def import_sector(self, interaction: discord.Interaction, file: discord.Attachment):
        if not file.filename.endswith(".json"):
            await interaction.response.send_message("❌ Please upload a `.json` file.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            content = await file.read()
            import_data = json.loads(content)
            
            guild_id = interaction.guild_id or interaction.user.id
            channel_id = interaction.channel.id
            data = self.get_guild_tracker(guild_id, channel_id)
            
            # Merge combatants or overwrite? 
            # Overwrite for sector generation makes sense.
            data["combatants"] = import_data.get("combatants", [])
            data["grid_type"] = import_data.get("grid_type", "square")
            data["theme"] = import_data.get("theme", "default")
            data["drawings"] = import_data.get("drawings", [])
            
            self.save_guild_tracker(guild_id, data, channel_id)
            
            msg = f"🗺️ **Map Imported!** Added {len(data['combatants'])} characters and {len(data['drawings'])} features."
            await interaction.followup.send(msg)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to import sector: `{e}`")


    @app_commands.command(name="damage", description="Deal damage to a character on the tracker.")
    @app_commands.describe(target="The name of the character to damage", amount="Amount of damage to deal (use negative to heal)")
    @app_commands.autocomplete(target=target_autocomplete)
    @is_gm_check()
    async def damage(self, interaction: discord.Interaction, target: str, amount: int):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        combatant = next((c for c in data["combatants"] if c["name"].lower() == target.lower()), None)
        if not combatant:
            await interaction.response.send_message(f"❌ Combatant `{target}` not found.", ephemeral=True)
            return
            
        old_hp = combatant["current_hp"]
        combatant["current_hp"] -= amount
        
        # Don't let it go below 0 for display logic
        if combatant["current_hp"] < 0:
             combatant["current_hp"] = 0
             
        self.save_guild_tracker(guild_id, data, channel_id)
        
        status = self._get_status(combatant["current_hp"], combatant["max_hp"])
        
        msg = f"⚔️ Dealt **{amount}** damage to **{combatant['name']}**.\n"
        if amount < 0:
            msg = f"🩹 Healed **{abs(amount)}** damage on **{combatant['name']}**.\n"
            
        msg += f"Status: {status}"
        
        await interaction.response.send_message(msg)

    @app_commands.command(name="remove", description="Remove a character from the tracker.")
    @app_commands.describe(target="The name of the character to remove")
    @app_commands.autocomplete(target=target_autocomplete)
    @is_gm_check()
    async def remove(self, interaction: discord.Interaction, target: str):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        initial_count = len(data["combatants"])
        data["combatants"] = [c for c in data["combatants"] if c["name"].lower() != target.lower()]
        
        if len(data["combatants"]) < initial_count:
            self.save_guild_tracker(guild_id, data, channel_id)
            await interaction.response.send_message(f"🗑️ Removed **{target}** from the tracker.")
        else:
            await interaction.response.send_message(f"❌ Combatant `{target}` not found.", ephemeral=True)

    @app_commands.command(name="condition", description="Toggle a status condition on a combatant.")
    @app_commands.describe(target="The name of the enemy", condition="The status to add or remove (e.g. 'Stunned')")
    @app_commands.autocomplete(target=target_autocomplete)
    @is_gm_check()
    async def condition(self, interaction: discord.Interaction, target: str, condition: str):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        combatant = next((c for c in data["combatants"] if c["name"].lower() == target.lower()), None)
        if not combatant:
            await interaction.response.send_message(f"❌ Combatant `{target}` not found.", ephemeral=True)
            return
            
        if "conditions" not in combatant:
            combatant["conditions"] = []
            
        cond_lower = condition.lower()
        existing = next((c for c in combatant["conditions"] if c.lower() == cond_lower), None)
        
        if existing:
            combatant["conditions"].remove(existing)
            msg = f"✨ Removed condition **{existing}** from {combatant['name']}."
        else:
            combatant["conditions"].append(condition)
            msg = f"⚠️ Added condition **{condition}** to {combatant['name']}."
            
        self.save_guild_tracker(guild_id, data, channel_id)
        await interaction.response.send_message(msg)

    @app_commands.command(name="distance", description="Update a combatant's distance/position.")
    @app_commands.describe(target="The name of the enemy", distance="The new distance (e.g., '10m', 'Engaged', 'Far')")
    @app_commands.autocomplete(target=target_autocomplete)
    @is_gm_check()
    async def distance(self, interaction: discord.Interaction, target: str, distance: str):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        combatant = next((c for c in data["combatants"] if c["name"].lower() == target.lower()), None)
        if not combatant:
            await interaction.response.send_message(f"❌ Combatant `{target}` not found.", ephemeral=True)
            return
            
        combatant["distance"] = distance
        self.save_guild_tracker(guild_id, data, channel_id)
        await interaction.response.send_message(f"📏 Updated **{combatant['name']}** distance to: {distance}")

    @app_commands.command(name="move", description="Update a combatant's position on the map.")
    @app_commands.describe(target="The name of the enemy", coords="The new coordinates (e.g. 'A1', '5,5')")
    @app_commands.autocomplete(target=target_autocomplete)
    @is_gm_check()
    async def move(self, interaction: discord.Interaction, target: str, coords: str):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        combatant = next((c for c in data["combatants"] if c["name"].lower() == target.lower()), None)
        if not combatant:
            await interaction.response.send_message(f"❌ Combatant `{target}` not found.", ephemeral=True)
            return
            
        x, y = self.parse_coords(coords)
        if x is None:
            await interaction.response.send_message(f"❌ Invalid coordinates: `{coords}`. Use 'A1' or '1,1' format.", ephemeral=True)
            return
            
        combatant["x"] = x
        combatant["y"] = y
        self.save_guild_tracker(guild_id, data, channel_id)
        await interaction.response.send_message(f"📍 Moved **{combatant['name']}** to **{coords.upper()}**.")

    @app_commands.command(name="ac", description="Update a combatant's Armor Class.")
    @app_commands.describe(target="The name of the enemy")
    @app_commands.autocomplete(target=target_autocomplete)
    @is_gm_check()
    async def ac(self, interaction: discord.Interaction, target: str, ac: int):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        combatant = next((c for c in data["combatants"] if c["name"].lower() == target.lower()), None)
        if not combatant:
            await interaction.response.send_message(f"❌ Combatant `{target}` not found.", ephemeral=True)
            return
        combatant["ac"] = ac
        self.save_guild_tracker(guild_id, data, channel_id)
        await interaction.response.send_message(f"🛡️ Updated **{combatant['name']}** AC to **{ac}**.")

    @app_commands.command(name="hide", description="Toggle whether players can see this combatant's stats.")
    @app_commands.describe(target="The name of the enemy")
    @app_commands.autocomplete(target=target_autocomplete)
    @is_gm_check()
    async def hide(self, interaction: discord.Interaction, target: str):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        combatant = next((c for c in data["combatants"] if c["name"].lower() == target.lower()), None)
        if not combatant:
            await interaction.response.send_message(f"❌ Combatant `{target}` not found.", ephemeral=True)
            return
        combatant["hidden"] = not combatant.get("hidden", False)
        self.save_guild_tracker(guild_id, data, channel_id)
        status = "HIDDEN" if combatant["hidden"] else "VISIBLE"
        await interaction.response.send_message(f"👁️ **{combatant['name']}** stats are now **{status}**.")

    @app_commands.command(name="map", description="Show the tactical map for the current combat.")
    async def map(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        if not data["combatants"]:
            await interaction.response.send_message("The combat tracker is empty. Add combatants first.", ephemeral=True)
            return
            
        # Update active channel ID for Social Map sync
        data["active_channel_id"] = interaction.channel_id
        self.save_guild_tracker(guild_id, data, channel_id)
            
        await interaction.response.defer()
        
        try:
            theme = data.get("theme", "default")
            background_path = self._get_background_path(data)
            
            grid_type = data.get("grid_type", "square")
            buffer = self.map_renderer.render_map(data["combatants"], theme_name=theme, background_path=background_path, grid_type=grid_type)
            file = discord.File(fp=buffer, filename="map.png")
            
            embed = discord.Embed(title="🗺️ Tactical Map", color=discord.Color.blue())
            embed.set_image(url="attachment://map.png")
            
            # Add link to interactive map
            # Determine IP and port
            ip = "147.182.248.196"
            port = 8080
            link = f"http://{ip}:{port}/map?guild_id={guild_id}&channel_id={channel_id}"
            bg_notice = "\n🎨 *Custom Background Active*" if background_path else ""
            embed.description = f"🔗 [**Open Interactive Map**]({link})\nMove tokens with buttons or mouse!{bg_notice}"
            
            view = MapMovementView(self, guild_id, channel_id, data["combatants"])
            await interaction.followup.send(file=file, embed=embed, view=view)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to render map: `{e}`")

    @app_commands.command(name="controller", description="Open the Tactical Button Controller for the map.")
    async def controller(self, interaction: discord.Interaction):
        """Open the interactive tactical grid controller."""
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        if not data["combatants"] and not data.get("drawings"):
            await interaction.response.send_message("The combat tracker is empty. Add combatants first.", ephemeral=True)
            return
            
        # Update active channel ID for Social Map sync
        data["active_channel_id"] = interaction.channel_id
        self.save_guild_tracker(guild_id, data, channel_id)
            
        await interaction.response.defer()
        
        try:
            theme = data.get("theme", "default")
            background_path = self._get_background_path(data)
            vx, vy = data.get("viewport_x", 0), data.get("viewport_y", 0)
            sel_id = data.get("active_selection_id")
            drawings = data.get("drawings", [])
            
            buffer = self.map_renderer.render_map(
                data["combatants"], 
                theme_name=theme, 
                background_path=background_path,
                drawings=drawings,
                viewport=(vx, vy),
                selection_id=sel_id
            )
            file = discord.File(fp=buffer, filename="map.png")
            
            embed = discord.Embed(title="🎮 Tactical Controller", color=discord.Color.green())
            embed.set_image(url="attachment://map.png")
            mode = data.get("interaction_mode", "move").upper()
            embed.description = f"**Mode:** {mode}\nUse grid buttons to interact. Viewport: {chr(ord('A')+vx)}{vy+1} to {chr(ord('A')+vx+3)}{vy+4}"
            
            view = TacticalControllerView(self, guild_id, channel_id)
            await interaction.followup.send(file=file, embed=embed, view=view)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to launch controller: `{e}`")
    async def _handle_import_map(self, interaction: discord.Interaction, image: Optional[discord.Attachment] = None, reset: bool = False):
        """Shared handler for /tracker background and /importmap."""
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        if reset:
            data["background_url"] = None
            self.save_guild_tracker(guild_id, data, channel_id)
            await interaction.response.send_message("🧹 Custom background cleared. Reverting to theme.")
            return

        if not image:
            await interaction.response.send_message("❌ Please attach an image or use `reset: True`.", ephemeral=True)
            return

        if not any(image.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg"]):
            await interaction.response.send_message("❌ Invalid file type. Please upload a PNG or JPG.", ephemeral=True)
            return

        await interaction.response.defer()
        
        # Ensure maps dir exists
        map_dir = os.path.join("data", "maps")
        os.makedirs(map_dir, exist_ok=True)
        
        file_ext = os.path.splitext(image.filename)[1]
        file_path = os.path.join(map_dir, f"{guild_id}{file_ext}")
        
        await image.save(file_path)
        
        # Use a local path that the web server can serve
        data["background_url"] = f"/api/maps/{guild_id}{file_ext}"
        # Set theme to custom automatically
        data["theme"] = "custom"
        self.save_guild_tracker(guild_id, data, channel_id)
        
        await interaction.followup.send(f"🗺️ Custom map background uploaded! View it with `/tracker map`.")

    @app_commands.command(name="background", description="Upload a custom map background or reset to a theme.")
    @app_commands.describe(image="The map image to upload (PNG/JPG)", reset="Set to True to clear the custom background")
    @is_gm_check()
    async def background(self, interaction: discord.Interaction, image: Optional[discord.Attachment] = None, reset: bool = False):
        await self._handle_import_map(interaction, image, reset)

    @app_commands.command(name="theme", description="Change the tactical map theme.")
    @app_commands.choices(theme=[
        app_commands.Choice(name="Space / Void (Default)", value="default"),
        app_commands.Choice(name="Forest", value="forest"),
        app_commands.Choice(name="Cave", value="cave"),
        app_commands.Choice(name="Desert", value="desert"),
    ])
    @is_gm_check()
    async def theme(self, interaction: discord.Interaction, theme: str):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        data["theme"] = theme
        self.save_guild_tracker(guild_id, data, channel_id)
        await interaction.response.send_message(f"🎨 Map theme updated to **{theme.capitalize()}**. (Note: Custom backgrounds override themes)")

    @app_commands.command(name="list", description="Show the current combat tracker.")
    async def list(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        if not data["combatants"]:
            await interaction.response.send_message("The combat tracker is currently empty.")
            return
            
        embed = discord.Embed(title="⚔️ Combat Tracker", color=discord.Color.dark_purple())
        
        desc = ""
        for c in data["combatants"]:
            status = self._get_status(c["current_hp"], c["max_hp"])
            hidden_str = " 👁️‍🗨️" if c.get("hidden") else ""
            ac_str = f" 🛡️`{c.get('ac', 10)}`"
            conds = c.get("conditions", [])
            cond_str = f" *[{', '.join(conds)}]*" if conds else ""
            dist = c.get("distance", "")
            dist_str = f" 📍 `{dist}`" if dist else ""
            pos = f" ({chr(ord('A') + c['x'])}{c['y'] + 1})" if c.get("x") is not None else ""
            desc += f"**{c['name']}** - {status}{ac_str}{dist_str}{pos}{cond_str}{hidden_str}\n"
            
        embed.description = desc
        embed.set_footer(text="Use /tracker damage <target> <amount> to deal damage")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Clear all enemies from the tracker.")
    async def clear(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        self.save_guild_tracker(guild_id, {"combatants": [], "current_turn_index": -1}, channel_id)
        await interaction.response.send_message("🧹 The combat tracker has been cleared.")

    @app_commands.command(name="next", description="Move to the next combatant's turn.")
    async def next_turn(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        if not data["combatants"]:
            await interaction.response.send_message("❌ The tracker is empty. Add combatants first.", ephemeral=True)
            return
            
        data["current_turn_index"] += 1
        if data["current_turn_index"] >= len(data["combatants"]):
            data["current_turn_index"] = 0
            
        self.save_guild_tracker(guild_id, data, channel_id)
        current = data["combatants"][data["current_turn_index"]]
        
        status = self._get_status(current["current_hp"], current["max_hp"])
        conds = current.get("conditions", [])
        cond_str = f" *[{', '.join(conds)}]*" if conds else ""
        await interaction.response.send_message(f"▶️ **Next Turn:** It is now **{current['name']}**'s turn! (HP: {current['current_hp']}/{current['max_hp']} {status}){cond_str}")

    @app_commands.command(name="party", description="Add all players from the active Campaign to the tracker.")
    async def add_party(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or interaction.user.id
        tracker_channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        # Load campaign from database
        camp_data = self.bot.db.get_campaign(guild_id)
        if not camp_data:
            await interaction.response.send_message("❌ No active campaign found to import players from! Use `/campaign start`.", ephemeral=True)
            return
            
        players = camp_data.get("players", {})
        if not players:
            await interaction.response.send_message("❌ The campaign has no players to import.", ephemeral=True)
            return
            
        added = []
        for uid, p in players.items():
            new_id = 1
            if tracker_data["combatants"]:
                new_id = max([c["id"] for c in tracker_data["combatants"]]) + 1
            
            # Check if they already exist in the tracker to avoid dupes
            if not any(c["name"] == p["char_name"] for c in tracker_data["combatants"]):
                tracker_data["combatants"].append({
                    "id": new_id,
                    "name": p["char_name"],
                    "max_hp": p["max_hp"],
                    "current_hp": p["current_hp"],
                    "ac": p.get("ac", 10),
                    "hidden": False,
                    "conditions": [],
                    "is_enemy": False,
                    "x": None,
                    "y": None
                })
                added.append(p["char_name"])
                
        if added:
            self.save_guild_tracker(guild_id, tracker_data)
            await interaction.response.send_message(f"✅ Auto-added Party to tracker: **{', '.join(added)}**")
        else:
            await interaction.response.send_message("No new players to add (they might already be in the tracker).", ephemeral=True)


    @commands.group(name="tracker", invoke_without_command=True, help="Manage the combat tracker. Subcommands: add, damage, remove, clear, list.")
    async def tracker_text(self, ctx):
        await ctx.send("Use `!tracker add`, `!tracker damage`, `!tracker distance`, `!tracker list`, `!tracker remove`, or `!tracker clear`.")

    @tracker_text.command(name="add", help="Add enemies to the tracker. Usage: !tracker add <name> <hp> <ac> [quantity] [coords] [distance]")
    async def tracker_add(self, ctx, name: str, hp: int, ac: int = 10, quantity_or_coords: str = "1", coords_or_dist: str = "", *, distance: str = ""):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        # Determine quantity and coords
        quantity = 1
        coords = ""
        
        if quantity_or_coords.isdigit():
            quantity = int(quantity_or_coords)
            coords = coords_or_dist
        else:
            coords = quantity_or_coords
            if coords_or_dist:
                distance = f"{coords_or_dist} {distance}".strip()

        x, y = self.parse_coords(coords)
        
        added_names = []
        for _ in range(max(1, min(quantity, 50))):
            # Determine new ID (internal)
            new_id = 1
            if data["combatants"]: new_id = max([c["id"] for c in data["combatants"]]) + 1
                 
            # Handle duplicate names
            final_name = name
            count = 1
            existing_names = [c["name"].lower() for c in data["combatants"]]
            while final_name.lower() in existing_names:
                count += 1
                final_name = f"{name} {count}"
    
            data["combatants"].append({
                "id": new_id, "name": final_name,
                "max_hp": hp, "current_hp": hp, "ac": ac, "hidden": False,
                "conditions": [], "distance": distance,
                "x": x, "y": y, "is_enemy": True
            })
            added_names.append(final_name)

        self.save_guild_tracker(guild_id, data, channel_id)
        
        if quantity > 1:
            msg = f"✅ Added **{len(added_names)}x {name}** to the tracker: {', '.join(added_names[:5])}"
            if len(added_names) > 5: msg += f" and {len(added_names)-5} more."
        else:
            if not added_names:
                 await ctx.send("❌ No enemies added.")
                 return
            msg = f"✅ Added **{added_names[0]}** (HP: {hp}, AC: {ac}) to the tracker."
            if x is not None: msg += f" Position: ({coords.upper()})"
        await ctx.send(msg)

    @tracker_text.command(name="ac", help="Update AC. Usage: !tracker ac <name> <value>")
    async def tracker_ac(self, ctx, name: str, ac: int):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        combatant = next((c for c in data["combatants"] if c["name"].lower() == name.lower()), None)
        if not combatant:
            await ctx.send(f"❌ Combatant `{name}` not found.")
            return
        combatant["ac"] = ac
        self.save_guild_tracker(guild_id, data, channel_id)
        await ctx.send(f"🛡️ Updated **{combatant['name']}** AC to **{ac}**.")

    @tracker_text.command(name="hide", help="Toggle visibility. Usage: !tracker hide <name>")
    async def tracker_hide(self, ctx, name: str):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        combatant = next((c for c in data["combatants"] if c["name"].lower() == name.lower()), None)
        if not combatant:
            await ctx.send(f"❌ Combatant `{name}` not found.")
            return
        combatant["hidden"] = not combatant.get("hidden", False)
        self.save_guild_tracker(guild_id, data, channel_id)
        status = "HIDDEN" if combatant["hidden"] else "VISIBLE"
        await ctx.send(f"👁️ **{combatant['name']}** stats are now **{status}**.")

    @tracker_text.command(name="move", help="Move a combatant. Usage: !tracker move <name> <coords>")
    async def tracker_move(self, ctx, name: str, coords: str):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        combatant = next((c for c in data["combatants"] if c["name"].lower() == name.lower()), None)
        if not combatant:
            await ctx.send(f"❌ Combatant `{name}` not found.")
            return
            
        x, y = self.parse_coords(coords)
        if x is None:
            await ctx.send(f"❌ Invalid coordinates: `{coords}`.")
            return
            
        combatant["x"] = x
        combatant["y"] = y
        self.save_guild_tracker(guild_id, data, channel_id)
        await ctx.send(f"📍 Moved **{combatant['name']}** to **{coords.upper()}**.")
    @tracker_text.command(name="map", help="Show the tactical map.")
    async def tracker_map(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        if not data["combatants"]:
            await ctx.send("The combat tracker is empty.")
            return
            
        try:
            theme = data.get("theme", "default")
            background_url = data.get("background_url")
            background_path = None
            
            if background_url:
                filename = background_url.split("/")[-1]
                background_path = os.path.join("data", "maps", filename)
                if not os.path.exists(background_path):
                    background_path = None

            grid_type = data.get("grid_type", "square")
            buffer = self.map_renderer.render_map(data["combatants"], theme_name=theme, background_path=background_path, grid_type=grid_type)
            file = discord.File(fp=buffer, filename="map.png")
            embed = discord.Embed(title="🗺️ Tactical Map", color=discord.Color.blue())
            embed.set_image(url="attachment://map.png")
            
            # Add link to interactive map
            # Determine IP and port
            ip = "147.182.248.196"
            port = 8080
            link = f"http://{ip}:{port}/map?guild_id={guild_id}&channel_id={channel_id}"
            bg_notice = "\n🎨 *Custom Background Active*" if background_path else ""
            embed.description = f"🔗 [**Open Interactive Map**]({link})\nMove tokens with buttons or mouse!{bg_notice}"
            
            from cogs.tracker import MapMovementView
            view = MapMovementView(self, guild_id, channel_id, data["combatants"])
            await ctx.send(file=file, embed=embed, view=view)
        except Exception as e:
            await ctx.send(f"❌ Failed to render map: `{e}`")

    @tracker_text.command(name="controller", help="Open the Tactical Button Controller.")
    async def tracker_controller_cmd(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        if not data["combatants"] and not data.get("drawings"):
            await ctx.send("The combat tracker is empty. Add combatants first.")
            return
            
        try:
            theme = data.get("theme", "default")
            background_path = self._get_background_path(data)
            vx, vy = data.get("viewport_x", 0), data.get("viewport_y", 0)
            sel_id = data.get("active_selection_id")
            drawings = data.get("drawings", [])
            
            buffer = self.map_renderer.render_map(
                data["combatants"], 
                theme_name=theme, 
                background_path=background_path,
                drawings=drawings,
                viewport=(vx, vy),
                selection_id=sel_id
            )
            file = discord.File(fp=buffer, filename="map.png")
            
            embed = discord.Embed(title="🎮 Tactical Controller", color=discord.Color.green())
            embed.set_image(url="attachment://map.png")
            mode = data.get("interaction_mode", "move").upper()
            embed.description = f"**Mode:** {mode}\nUse grid buttons to interact. Viewport: {chr(ord('A')+vx)}{vy+1} to {chr(ord('A')+vx+3)}{vy+4}"
            
            from cogs.tracker import TacticalControllerView
            view = TacticalControllerView(self, guild_id, channel_id)
            await ctx.send(file=file, embed=embed, view=view)
        except Exception as e:
            await ctx.send(f"❌ Failed to launch controller: `{e}`")

    @tracker_text.command(name="damage", help="Deal damage to an enemy. Usage: !tracker damage <name> <amount>")
    async def tracker_damage(self, ctx, name: str, amount: int):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        combatant = next((c for c in data["combatants"] if c["name"].lower() == name.lower()), None)
        if not combatant:
            await ctx.send(f"❌ Combatant `{name}` not found.")
            return
            
        combatant["current_hp"] -= amount
        if combatant["current_hp"] < 0: combatant["current_hp"] = 0
             
        self.save_guild_tracker(guild_id, data, channel_id)
        status = self._get_status(combatant["current_hp"], combatant["max_hp"])
        
        msg = f"⚔️ Dealt **{amount}** damage to **{combatant['name']}**.\n"
        if amount < 0: msg = f"🩹 Healed **{abs(amount)}** damage on **{combatant['name']}**.\n"
        msg += f"Status: {status}"
        await ctx.send(msg)

    @tracker_text.command(name="remove", help="Remove an enemy from the tracker. Usage: !tracker remove <name>")
    async def tracker_remove(self, ctx, name: str):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        initial_count = len(data["combatants"])
        data["combatants"] = [c for c in data["combatants"] if c["name"].lower() != name.lower()]
        
        if len(data["combatants"]) < initial_count:
            self.save_guild_tracker(guild_id, data, channel_id)
            await ctx.send(f"🗑️ Removed **{name}** from the tracker.")
        else:
            await ctx.send(f"❌ Combatant `{name}` not found.")

    @tracker_text.command(name="condition", help="Toggle a condition. Usage: !tracker condition <name> <status>")
    async def tracker_condition(self, ctx, name: str, *, condition: str):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        combatant = next((c for c in data["combatants"] if c["name"].lower() == name.lower()), None)
        if not combatant:
            await ctx.send(f"❌ Combatant `{name}` not found.")
            return
            
        if "conditions" not in combatant:
            combatant["conditions"] = []
            
        cond_lower = condition.lower()
        existing = next((c for c in combatant["conditions"] if c.lower() == cond_lower), None)
        
        if existing:
            combatant["conditions"].remove(existing)
            msg = f"✨ Removed condition **{existing}** from {combatant['name']}."
        else:
            combatant["conditions"].append(condition)
            msg = f"⚠️ Added condition **{condition}** to {combatant['name']}."
            
        self.save_guild_tracker(guild_id, data, channel_id)
        await ctx.send(msg)

    @tracker_text.command(name="distance", help="Update a combatant's distance. Usage: !tracker distance <name> <distance>")
    async def tracker_distance(self, ctx, name: str, *, distance: str):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        combatant = next((c for c in data["combatants"] if c["name"].lower() == name.lower()), None)
        if not combatant:
            await ctx.send(f"❌ Combatant `{name}` not found.")
            return
            
        combatant["distance"] = distance
        self.save_guild_tracker(guild_id, data, channel_id)
        await ctx.send(f"📏 Updated **{combatant['name']}** distance to: {distance}")

    @tracker_text.command(name="list", help="Show the current combat tracker.")
    async def tracker_list(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        if not data["combatants"]:
            await ctx.send("The combat tracker is currently empty.")
            return
            
        embed = discord.Embed(title="⚔️ Combat Tracker", color=discord.Color.dark_purple())
        desc = ""
        for c in data["combatants"]:
            status = self._get_status(c["current_hp"], c["max_hp"])
            hidden_str = " 👁️‍🗨️" if c.get("hidden") else ""
            ac_str = f" 🛡️`{c.get('ac', 10)}`"
            conds = c.get("conditions", [])
            cond_str = f" *[{', '.join(conds)}]*" if conds else ""
            dist = c.get("distance", "")
            dist_str = f" 📍 `{dist}`" if dist else ""
            pos = f" ({chr(ord('A') + c['x'])}{c['y'] + 1})" if c.get("x") is not None else ""
            desc += f"**{c['name']}** - {status}{ac_str}{dist_str}{pos}{cond_str}{hidden_str}\n"
            
        embed.description = desc
        embed.set_footer(text="Use !tracker damage <name> <amount> to deal damage")
        await ctx.send(embed=embed)

    @tracker_text.command(name="clear", help="Clear the combat tracker.")
    async def tracker_clear(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        self.save_guild_tracker(guild_id, {"combatants": [], "current_turn_index": -1}, channel_id)
        await ctx.send("🧹 The combat tracker has been cleared.")

    @tracker_text.command(name="grid", help="Toggle between square and hex grid. Usage: !tracker grid <square|hex>")
    async def tracker_grid(self, ctx, grid_type: str):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        grid_type = grid_type.lower()
        if grid_type not in ["square", "hex"]:
            await ctx.send("❌ Invalid grid type. Use `square` or `hex`.")
            return
            
        data["grid_type"] = grid_type
        self.save_guild_tracker(guild_id, data, channel_id)
        await ctx.send(f"📏 Set grid type to **{grid_type.upper()}**.")

    @tracker_text.command(name="next", help="Move to the next combatant's turn.")
    async def tracker_next(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        if not data["combatants"]:
            await ctx.send("❌ The tracker is empty.")
            return
            
        data["current_turn_index"] += 1
        if data["current_turn_index"] >= len(data["combatants"]):
            data["current_turn_index"] = 0
            
        self.save_guild_tracker(guild_id, data, channel_id)
        current = data["combatants"][data["current_turn_index"]]
        status = self._get_status(current["current_hp"], current["max_hp"])
        conds = current.get("conditions", [])
        cond_str = f" *[{', '.join(conds)}]*" if conds else ""
        await ctx.send(f"▶️ **Next Turn:** It is now **{current['name']}**'s turn! ({status}){cond_str}")

    @tracker_text.command(name="party", help="Import all players from the campaign into the tracker.")
    async def tracker_party(self, ctx):
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        tracker_channel_id = interaction.channel.id if 'interaction' in locals() else ctx.channel.id
        data = self.get_guild_tracker(guild_id, channel_id)
        
        # Load campaign from database
        camp_data = self.bot.db.get_campaign(guild_id)
        if not camp_data:
            await ctx.send("❌ No active campaign found! A GM must `!campaign start` one.")
            return
            
        players = camp_data.get("players", {})
        if not players:
            await ctx.send("❌ The campaign has no players to import. Have them `!campaign join`!")
            return
            
        added = []
        for uid, p in players.items():
            new_id = 1
            if tracker_data["combatants"]:
                new_id = max([c["id"] for c in tracker_data["combatants"]]) + 1
            
            if not any(c["name"] == p["char_name"] for c in tracker_data["combatants"]):
                tracker_data["combatants"].append({
                    "id": new_id,
                    "name": p["char_name"],
                    "max_hp": p["max_hp"],
                    "current_hp": p["current_hp"],
                    "conditions": [],
                    "distance": "",
                    "is_enemy": False,
                    "x": None,
                    "y": None
                })
                added.append(p["char_name"])
                
        if added:
            self.save_guild_tracker(guild_id, tracker_data)
            await ctx.send(f"✅ Auto-added Party to tracker: **{', '.join(added)}**")
        else:
            await ctx.send("No new players to add (they might already be in the tracker).")

# Standalone /importmap command (outside the tracker group)
@app_commands.command(name="importmap", description="Upload a custom tactical map background image.")
@app_commands.describe(image="The map image to upload (PNG/JPG)", reset="Set to True to clear the current background")
async def importmap(interaction: discord.Interaction, image: Optional[discord.Attachment] = None, reset: bool = False):
    cog = interaction.client.get_cog("TrackerCog")
    if cog:
        await cog._handle_import_map(interaction, image, reset)
    else:
        await interaction.response.send_message("❌ Tracker system not loaded.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TrackerCog(bot))
    bot.tree.add_command(importmap)
