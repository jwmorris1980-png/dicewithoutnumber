import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class CompendiumCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weapons = []
        self.armor = []
        self.gear = []
        self.ships = []
        self.foci = []
        self.rule_index = []
        self.load_data()

    def load_data(self):
        """Loads compendium data from standard JSON files."""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        
        equip_path = os.path.join(data_dir, 'equipment.json')
        if os.path.exists(equip_path):
            try:
                with open(equip_path, 'r', encoding='utf-8') as f:
                    equipment_data = json.load(f)
                    self.weapons = [item for item in equipment_data if item.get("type", "").lower() == "weapon"]
                    self.armor = [item for item in equipment_data if item.get("type", "").lower() == "armor"]
                    self.gear = [item for item in equipment_data if item.get("type", "").lower() not in ["weapon", "armor"]]
            except Exception as e:
                print(f"Failed to load equipment data: {e}")
                
        foci_path = os.path.join(data_dir, 'foci.json')
        if os.path.exists(foci_path):
            try:
                with open(foci_path, 'r', encoding='utf-8') as f:
                    self.foci = json.load(f)
            except Exception as e:
                print(f"Failed to load foci data: {e}")
                
        ships_path = os.path.join(data_dir, 'ships.json')
        if os.path.exists(ships_path):
            try:
                with open(ships_path, 'r', encoding='utf-8') as f:
                    self.ships = json.load(f)
            except Exception as e:
                print(f"Failed to load ships data: {e}")
                
        rules_path = os.path.join(data_dir, 'rules_index.json')
        if os.path.exists(rules_path):
            try:
                with open(rules_path, 'r', encoding='utf-8') as f:
                    self.rule_index = json.load(f)
            except Exception as e:
                print(f"Failed to load rules index: {e}")

    # Autocompletes
    async def weapon_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=i["name"], value=i["name"]) for i in self.weapons if current.lower() in i["name"].lower()][:25]

    async def armor_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=i["name"], value=i["name"]) for i in self.armor if current.lower() in i["name"].lower()][:25]

    async def gear_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=i["name"], value=i["name"]) for i in self.gear if current.lower() in i["name"].lower()][:25]

    async def shipinfo_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=i["name"], value=i["name"]) for i in self.ships if current.lower() in i["name"].lower()][:25]
        
    async def foci_autocomplete(self, interaction: discord.Interaction, current: str):
        current = current.lower()
        choices = []
        for focus in self.foci:
            label = self._foci_label(focus)
            if current in focus["name"].lower() or current in label.lower():
                choices.append(app_commands.Choice(name=label[:100], value=self._foci_value(focus)[:100]))
        return choices[:25]

    def _foci_label(self, focus):
        suffix = focus.get("source_book", "Unknown")
        if focus.get("category"):
            suffix = f"{suffix}, {focus['category']}"
        return f"{focus['name']} ({suffix})"

    def _foci_value(self, focus):
        return f"{focus.get('source_book', '')}|{focus.get('category', '')}|{focus['name']}"

    def _find_focus(self, name):
        if "|" in name:
            source_book, category, focus_name = (name.split("|", 2) + ["", "", ""])[:3]
            return next(
                (
                    f
                    for f in self.foci
                    if f["name"].lower() == focus_name.lower()
                    and f.get("source_book", "").lower() == source_book.lower()
                    and f.get("category", "").lower() == category.lower()
                ),
                None,
            )

        matches = [f for f in self.foci if f["name"].lower() == name.lower()]
        return matches[0] if matches else None

    # Helper method to render lists
    def _render_list_embed(self, title: str, items: list, color, description="Leave the name blank to see this list!"):
        embed = discord.Embed(title=title, description=description, color=color)
        
        item_list_lines = []
        for i in items:
            line = f"• **{i['name']}**"
            extras = []
            if "damage" in i: extras.append(f"Dmg: {i['damage']}")
            if "ac" in i: extras.append(f"AC: {i['ac']}")
            if "hp" in i: extras.append(f"HP: {i['hp']}")
            if "tech_level" in i: extras.append(f"TL{i['tech_level']}")
            
            if extras:
                line += f" *({', '.join(extras)})*"
            item_list_lines.append(line)
            
        item_list = "\n".join(item_list_lines)
        if not item_list:
            item_list = "No items found in this category."
        
        # Split logic into multiple fields if needed due to Discord limits (1024 chars per field)
        if len(item_list) > 1024:
            item_list = item_list[:1000] + "\n...and more."
            
        embed.add_field(name="Available Options", value=item_list, inline=False)
        return embed

    def _render_foci_list_embed(self):
        embed = discord.Embed(
            title="🌟 Focus List",
            description="Use `/foci name:` autocomplete for exact book-specific lookup.",
            color=discord.Color.purple(),
        )
        groups = {}
        for focus in self.foci:
            key = focus.get("source_book", "Unknown")
            if focus.get("category"):
                key = f"{key}, {focus['category']}"
            groups.setdefault(key, []).append(focus["name"])

        for group, names in groups.items():
            value = ", ".join(names)
            if len(value) > 1024:
                value = value[:1000].rsplit(",", 1)[0] + ", ..."
            embed.add_field(name=f"{group} ({len(names)})", value=value, inline=False)
        return embed

    # Slash Commands
    @app_commands.command(name="weapon", description="Browse or look up Weapons")
    @app_commands.autocomplete(name=weapon_autocomplete)
    async def weapon(self, interaction: discord.Interaction, name: str = None):
        if not name:
            await interaction.response.send_message(embed=self._render_list_embed("🔫 Weapons Catalog", self.weapons, discord.Color.red()))
            return
            
        item = next((i for i in self.weapons if i["name"].lower() == name.lower()), None)
        if not item:
            await interaction.response.send_message(f"Weapon `{name}` not found.", ephemeral=True)
            return
            
        embed = discord.Embed(title=item["name"], color=discord.Color.red())
        desc_lines = [
            f"**Damage:** {item.get('damage', 'N/A')}",
            f"**Range:** {item.get('range', 'N/A')}",
            f"**Attribute:** {item.get('attribute', 'N/A')}",
            f"**Magazine:** {item.get('magazine', 'N/A')}",
        ]
        embed.add_field(name="Stats", value="\n".join(desc_lines), inline=False)
        embed.add_field(name="Description", value=item.get("description", "No description available."), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="armor", description="Browse or look up Armor")
    @app_commands.autocomplete(name=armor_autocomplete)
    async def armor(self, interaction: discord.Interaction, name: str = None):
        if not name:
            await interaction.response.send_message(embed=self._render_list_embed("🛡️ Armor Catalog", self.armor, discord.Color.blue()))
            return
            
        item = next((i for i in self.armor if i["name"].lower() == name.lower()), None)
        if not item:
            await interaction.response.send_message(f"Armor `{name}` not found.", ephemeral=True)
            return
            
        embed = discord.Embed(title=item["name"], color=discord.Color.blue())
        embed.add_field(name="AC", value=str(item.get("ac", "N/A")), inline=True)
        embed.add_field(name="Encumbrance", value=str(item.get("encumbrance", "N/A")), inline=True)
        embed.add_field(name="Description", value=item.get("description", "No description available."), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="gear", description="Browse or look up Special Items and General Gear")
    @app_commands.autocomplete(name=gear_autocomplete)
    async def gear(self, interaction: discord.Interaction, name: str = None):
        if not name:
            await interaction.response.send_message(embed=self._render_list_embed("🎒 Gear & Special Items", self.gear, discord.Color.gold()))
            return
            
        item = next((i for i in self.gear if i["name"].lower() == name.lower()), None)
        if not item:
            await interaction.response.send_message(f"Gear `{name}` not found.", ephemeral=True)
            return
            
        embed = discord.Embed(title=item["name"], color=discord.Color.gold())
        embed.add_field(name="Encumbrance", value=str(item.get("encumbrance", "N/A")), inline=True)
        embed.add_field(name="Description", value=item.get("description", "No description available."), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shipinfo", description="Browse or look up Starship stats/types from the compendium.")
    @app_commands.autocomplete(name=shipinfo_autocomplete)
    async def shipinfo(self, interaction: discord.Interaction, name: str = None):
        if not name:
            await interaction.response.send_message(embed=self._render_list_embed("🚀 Starships", self.ships, discord.Color.dark_grey()))
            return
            
        ship = next((i for i in self.ships if i["name"].lower() == name.lower()), None)
        if not ship:
            await interaction.response.send_message(f"Ship `{name}` not found.", ephemeral=True)
            return
            
        embed = discord.Embed(title=ship["name"], description=ship.get("type", "Unknown Class"), color=discord.Color.dark_grey())
        stats = [
            f"**HP:** {ship.get('hp', 'N/A')}",
            f"**AC:** {ship.get('ac', 'N/A')}",
            f"**Armor:** {ship.get('armor', 'N/A')}",
            f"**Speed:** {ship.get('speed', 'N/A')}",
            f"**Crew (Min/Max):** {ship.get('crew', 'N/A')}",
            f"**Weapons:** {ship.get('weapons', 'N/A')}"
        ]
        embed.add_field(name="Ship Stats", value="\n".join(stats), inline=False)
        embed.add_field(name="Description", value=ship.get("description", "No description available."), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="foci", description="Browse or look up Foci")
    @app_commands.autocomplete(name=foci_autocomplete)
    async def foci(self, interaction: discord.Interaction, name: str = None):
        if not name:
            await interaction.response.send_message(embed=self._render_foci_list_embed())
            return
            
        focus = self._find_focus(name)
        if not focus:
            await interaction.response.send_message(f"Focus `{name}` not found.", ephemeral=True)
            return
            
        embed = discord.Embed(title=f"Focus: {focus['name']}", color=discord.Color.purple())
        embed.description = focus.get("description", "No description available.")
        embed.set_footer(text=self._foci_label(focus))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rule", description="Search the rulebooks for a specific keyword or phrase")
    async def rule(self, interaction: discord.Interaction, query: str):
        if not self.rule_index:
            await interaction.response.send_message("The rule index has not been built yet.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        query_lower = query.lower()
        
        results = []
        for page_data in self.rule_index:
            content_lower = page_data["content"].lower()
            if query_lower in content_lower:
                results.append(page_data)
        
        if not results:
             await interaction.followup.send(f"No rules found matching `{query}`.", ephemeral=True)
             return
             
        results.sort(key=lambda x: x["content"].lower().find(query_lower))
        top_match = results[0]
        match_idx = top_match["content"].lower().find(query_lower)
        
        start_idx = max(0, match_idx - 150)
        end_idx = min(len(top_match["content"]), match_idx + len(query) + 200)
        
        snippet = top_match["content"][start_idx:end_idx]
        if start_idx > 0: snippet = "..." + snippet
        if end_idx < len(top_match["content"]): snippet = snippet + "..."
            
        actual_case_query = top_match["content"][match_idx:match_idx+len(query)]
        snippet = snippet.replace(actual_case_query, f"**{actual_case_query}**")
        
        embed = discord.Embed(
            title=f"Rule Search: '{query}'", 
            description=f"Found **{len(results)}** pages containing this term.\n\nHere is the top match:\n\n> {snippet}",
            color=discord.Color.teal()
        )
        embed.set_footer(text=f"Book: {top_match['book']} | PDF Page: {top_match['page']}")
        await interaction.followup.send(embed=embed)

    @commands.command(name="weapon", help="Look up a weapon (e.g. !weapon Mag Rifle)")
    async def weapon_text(self, ctx, *, name: str = None):
        if not name:
            await ctx.send(embed=self._render_list_embed("🔫 Weapons Catalog", self.weapons, discord.Color.red()))
            return
            
        item = next((i for i in self.weapons if i["name"].lower() == name.lower()), None)
        if not item:
            await ctx.send(f"Weapon `{name}` not found.")
            return
            
        embed = discord.Embed(title=item["name"], color=discord.Color.red())
        desc_lines = [
            f"**Damage:** {item.get('damage', 'N/A')}",
            f"**Range:** {item.get('range', 'N/A')}",
            f"**Attribute:** {item.get('attribute', 'N/A')}",
            f"**Magazine:** {item.get('magazine', 'N/A')}",
        ]
        embed.add_field(name="Stats", value="\n".join(desc_lines), inline=False)
        embed.add_field(name="Description", value=item.get("description", "No description available."), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="armor", help="Look up armor (e.g. !armor Combat Field Uniform)")
    async def armor_text(self, ctx, *, name: str = None):
        if not name:
            await ctx.send(embed=self._render_list_embed("🛡️ Armor Catalog", self.armor, discord.Color.blue()))
            return
            
        item = next((i for i in self.armor if i["name"].lower() == name.lower()), None)
        if not item:
            await ctx.send(f"Armor `{name}` not found.")
            return
            
        embed = discord.Embed(title=item["name"], color=discord.Color.blue())
        embed.add_field(name="AC", value=str(item.get("ac", "N/A")), inline=True)
        embed.add_field(name="Encumbrance", value=str(item.get("encumbrance", "N/A")), inline=True)
        embed.add_field(name="Description", value=item.get("description", "No description available."), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="gear", help="Look up special items and gear")
    async def gear_text(self, ctx, *, name: str = None):
        if not name:
            await ctx.send(embed=self._render_list_embed("🎒 Gear & Special Items", self.gear, discord.Color.gold()))
            return
            
        item = next((i for i in self.gear if i["name"].lower() == name.lower()), None)
        if not item:
            await ctx.send(f"Gear `{name}` not found.")
            return
            
        embed = discord.Embed(title=item["name"], color=discord.Color.gold())
        embed.add_field(name="Encumbrance", value=str(item.get("encumbrance", "N/A")), inline=True)
        embed.add_field(name="Description", value=item.get("description", "No description available."), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="shipinfo", aliases=["si"], help="Look up starship types/stats from the compendium.")
    async def shipinfo_text(self, ctx, *, name: str = None):
        if not name:
            await ctx.send(embed=self._render_list_embed("🚀 Starships", self.ships, discord.Color.dark_grey()))
            return
            
        ship = next((i for i in self.ships if i["name"].lower() == name.lower()), None)
        if not ship:
            await ctx.send(f"Ship `{name}` not found.")
            return
            
        embed = discord.Embed(title=ship["name"], description=ship.get("type", "Unknown Class"), color=discord.Color.dark_grey())
        stats = [
            f"**HP:** {ship.get('hp', 'N/A')}",
            f"**AC:** {ship.get('ac', 'N/A')}",
            f"**Armor:** {ship.get('armor', 'N/A')}",
            f"**Speed:** {ship.get('speed', 'N/A')}",
            f"**Crew (Min/Max):** {ship.get('crew', 'N/A')}",
            f"**Weapons:** {ship.get('weapons', 'N/A')}"
        ]
        embed.add_field(name="Ship Stats", value="\n".join(stats), inline=False)
        embed.add_field(name="Description", value=ship.get("description", "No description available."), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="foci", aliases=["focus"], help="Look up Foci")
    async def foci_text(self, ctx, *, name: str = None):
        if not name:
            await ctx.send(embed=self._render_foci_list_embed())
            return
            
        focus = self._find_focus(name)
        if not focus:
            await ctx.send(f"Focus `{name}` not found.")
            return
            
        embed = discord.Embed(title=f"Focus: {focus['name']}", color=discord.Color.purple())
        embed.description = focus.get("description", "No description available.")
        embed.set_footer(text=self._foci_label(focus))
        await ctx.send(embed=embed)

    @commands.command(name="rule", help="Search the rulebooks for a specific keyword or phrase (e.g., !rule space combat)")
    async def rule_text(self, ctx, *, query: str):
        if not self.rule_index:
            await ctx.send("The rule index has not been built yet.")
            return

        query_lower = query.lower()
        results = []
        for page_data in self.rule_index:
            content_lower = page_data["content"].lower()
            if query_lower in content_lower:
                results.append(page_data)
        
        if not results:
             await ctx.send(f"No rules found matching `{query}`.")
             return
             
        results.sort(key=lambda x: x["content"].lower().find(query_lower))
        top_match = results[0]
        match_idx = top_match["content"].lower().find(query_lower)
        
        start_idx = max(0, match_idx - 150)
        end_idx = min(len(top_match["content"]), match_idx + len(query) + 200)
        
        snippet = top_match["content"][start_idx:end_idx]
        if start_idx > 0: snippet = "..." + snippet
        if end_idx < len(top_match["content"]): snippet = snippet + "..."
            
        actual_case_query = top_match["content"][match_idx:match_idx+len(query)]
        snippet = snippet.replace(actual_case_query, f"**{actual_case_query}**")
        
        embed = discord.Embed(
            title=f"Rule Search: '{query}'", 
            description=f"Found **{len(results)}** pages containing this term.\n\nHere is the top match:\n\n> {snippet}",
            color=discord.Color.teal()
        )
        embed.set_footer(text=f"Book: {top_match['book']} | PDF Page: {top_match['page']}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CompendiumCog(bot))
