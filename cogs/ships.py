import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class ShipsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_swn_ship_json(self, data: dict):
        """Parses starship JSON from Sectors Without Number."""
        # Detect SWN Ship JSON by presence of hullId or fittings
        if "hullId" not in data and "fittings" not in data:
            return None, "Not a valid Sectors Without Number ship JSON."

        # Load hull fallbacks from data/ships.json
        hull_stats = {}
        try:
            ships_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'ships.json')
            if os.path.exists(ships_path):
                with open(ships_path, 'r', encoding='utf-8') as f:
                    ships_list = json.load(f)
                    for s in ships_list:
                        hull_stats[s['name'].lower().replace(" ", "-")] = s
        except Exception as e:
            print(f"Error loading hull fallbacks: {e}")

        hull_id = data.get("hullId", "unknown").lower()
        fallback = hull_stats.get(hull_id, {})

        ship_data = {
            "name": data.get("name", "Unknown Ship"),
            "hull_id": hull_id,
            "hp": data.get("hp") or fallback.get("hp", 0),
            "max_hp": data.get("hp") or fallback.get("hp", 0),
            "ac": data.get("ac") or fallback.get("ac", 10),
            "armor": data.get("armor") or fallback.get("armor", 0),
            "speed": data.get("speed") or fallback.get("speed", 0),
            "fittings": [],
            "weapons": [],
            "defenses": [],
            "cargo": [],
            "notes": data.get("notes", ""),
            "type": "Starship"
        }

        # Parse fittings
        for f in data.get("fittings", []):
            if isinstance(f, dict):
                fname = f.get("fittingId", "Unknown Fitting").replace("-", " ").title()
                ship_data["fittings"].append({"name": fname, "count": f.get("count", 1)})

        # Parse weapons
        for w in data.get("weapons", []):
            if isinstance(w, str):
                ship_data["weapons"].append(w.replace("-", " ").title())
            elif isinstance(w, dict):
                ship_data["weapons"].append(w.get("name", "Unknown Weapon"))

        # Parse defenses
        for d in data.get("defenses", []):
            if isinstance(d, str):
                ship_data["defenses"].append(d.replace("-", " ").title())

        # Parse cargo
        for c in data.get("cargo", []):
            if isinstance(c, dict):
                ship_data["cargo"].append({
                    "name": c.get("name", "Unknown Item"),
                    "tons": c.get("tons", 0)
                })

        return ship_data, None

    async def _send_ship_view(self, ctx_or_interaction):
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        ship = self.bot.db.get_active_ship(user_id)
        if not ship:
            msg = "❌ You don't have an active starship. Upload a ship JSON to load one."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        embed = discord.Embed(title=f"🚀 Starship: {ship['name']}", color=discord.Color.dark_blue())
        embed.set_author(name=f"Hull: {ship['hull_id'].title()}")

        stats = f"**HP:** {ship['max_hp']}  |  **AC:** {ship['ac']}  |  **Armor:** {ship['armor']}  |  **Speed:** {ship['speed']}"
        embed.description = stats

        if ship['fittings']:
            f_text = "\n".join([f"• {f['name']} (x{f['count']})" for f in ship['fittings']])
            embed.add_field(name="Fittings", value=f_text if len(f_text) < 1024 else f_text[:1020] + "...", inline=False)

        if ship['weapons']:
            w_text = "\n".join([f"• {w}" for w in ship['weapons']])
            embed.add_field(name="Weapons", value=w_text if len(w_text) < 1024 else w_text[:1020] + "...", inline=False)

        if ship['notes']:
            embed.add_field(name="Notes", value=ship['notes'], inline=False)

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    @app_commands.command(name="ship", description="View your active starship.")
    async def ship_view(self, interaction: discord.Interaction):
        await self._send_ship_view(interaction)

    @commands.command(name="ship", help="View your active starship.")
    async def ship_view_text(self, ctx):
        await self._send_ship_view(ctx)

    async def _send_ship_list(self, ctx_or_interaction):
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        ships = self.bot.db.get_ships(user_id)
        if not ships:
            msg = "❌ You have no imported starships."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return

        desc = "\n".join([f"• {s}" for s in ships])
        embed = discord.Embed(title="🛸 Your Starships", description=desc, color=discord.Color.blue())
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    @app_commands.command(name="shiplist", description="List all your imported starships.")
    async def ship_list(self, interaction: discord.Interaction):
        await self._send_ship_list(interaction)

    @commands.command(name="shiplist", help="List all your imported starships.")
    async def ship_list_text(self, ctx):
        await self._send_ship_list(ctx)

async def setup(bot):
    await bot.add_cog(ShipsCog(bot))
