import json
import os
import re

import discord
from discord import app_commands
from discord.ext import commands


SHIP_KEYS = ("hullId", "hullType", "hullClass", "shipClass")


def _pretty_label(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if " " in text or "(" in text:
        return text
    text = re.sub(r"^(swn|cwn|wwn|awn)[-_]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[-_]+", " ", text)
    return " ".join(part.capitalize() if part.lower() != "ai" else "AI" for part in text.split() if part)


def _unwrap_ship_payload(data):
    if isinstance(data, list):
        data = next((item for item in data if isinstance(item, dict)), None)
    if not isinstance(data, dict):
        return None
    for key in ("ship", "starship", "vessel", "data"):
        nested = data.get(key)
        if isinstance(nested, dict) and (nested.get("hullId") or nested.get("name")):
            merged = {**data, **nested}
            merged.pop(key, None)
            return merged
    return data


def looks_like_ship_payload(data):
    payload = _unwrap_ship_payload(data)
    if not isinstance(payload, dict):
        return False
    if any(payload.get(key) for key in SHIP_KEYS):
        return True
    if payload.get("classId") or payload.get("attributes") or payload.get("skills") or payload.get("hitPointsCurrent"):
        return False
    fittings = payload.get("fittings")
    return bool(payload.get("name") and isinstance(fittings, list) and fittings)


class ShipsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _coerce_int(self, value, default=0):
        if value in (None, ""):
            return default
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        match = re.search(r"-?\d+", str(value))
        return int(match.group(0)) if match else default

    def _first(self, data, keys, default=None):
        for key in keys:
            if data.get(key) not in (None, ""):
                return data.get(key)
        return default

    def _named_list(self, raw, id_keys=("fittingId", "weaponId", "defenseId", "id", "name")):
        items = []
        for entry in raw or []:
            if isinstance(entry, str):
                label = _pretty_label(entry)
                if label:
                    items.append(label)
                continue
            if not isinstance(entry, dict):
                continue
            label = None
            for key in id_keys:
                if entry.get(key):
                    label = _pretty_label(entry.get(key))
                    break
            if not label:
                continue
            count = self._coerce_int(entry.get("count"), 1)
            items.append(f"{label} x{count}" if count > 1 else label)
        return items

    def parse_swn_ship_json(self, data: dict):
        """Parse starship JSON from characterswithoutnumber.app or Sectors Without Number."""
        payload = _unwrap_ship_payload(data)
        if not looks_like_ship_payload(payload):
            return None, "Not a starship JSON export."

        hull_stats = {}
        try:
            ships_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ships.json")
            if os.path.exists(ships_path):
                with open(ships_path, "r", encoding="utf-8") as handle:
                    for item in json.load(handle):
                        hull_stats[str(item.get("name") or "").lower().replace(" ", "-")] = item
        except Exception as exc:
            print(f"Error loading hull fallbacks: {exc}")

        hull_id = str(
            self._first(payload, ("hullId", "hullType", "hullClass", "shipClass"), "unknown")
        ).lower()
        fallback = hull_stats.get(hull_id, {})
        hp = self._coerce_int(
            self._first(payload, ("hp", "hitPoints", "hullPoints", "hitPointsCurrent"), fallback.get("hp", 0)),
            fallback.get("hp", 0),
        )
        hp_max = self._coerce_int(
            self._first(payload, ("maxHp", "hitPointsMax", "hullPointsMax", "hp_max"), hp),
            hp,
        )

        fittings = []
        for entry in payload.get("fittings") or []:
            if isinstance(entry, dict):
                name = _pretty_label(entry.get("fittingId") or entry.get("name") or entry.get("id"))
                if name:
                    fittings.append({"name": name, "count": self._coerce_int(entry.get("count"), 1)})
            elif isinstance(entry, str) and entry.strip():
                fittings.append({"name": _pretty_label(entry), "count": 1})

        ship_data = {
            "name": payload.get("name") or "Unknown Ship",
            "hull_id": hull_id,
            "hp": hp,
            "max_hp": hp_max,
            "ac": self._coerce_int(self._first(payload, ("ac", "armorClass"), fallback.get("ac", 10)), fallback.get("ac", 10)),
            "armor": self._coerce_int(self._first(payload, ("armor",), fallback.get("armor", 0)), fallback.get("armor", 0)),
            "speed": self._coerce_int(self._first(payload, ("speed",), fallback.get("speed", 0)), fallback.get("speed", 0)),
            "power": self._coerce_int(payload.get("power"), None) if payload.get("power") not in (None, "") else None,
            "mass": self._coerce_int(payload.get("mass"), None) if payload.get("mass") not in (None, "") else None,
            "cost": payload.get("cost"),
            "crew": payload.get("crew") or payload.get("crewComplement"),
            "fittings": fittings,
            "weapons": self._named_list(payload.get("weapons"), ("weaponId", "name", "id")),
            "defenses": self._named_list(payload.get("defenses") or payload.get("defences"), ("defenseId", "name", "id")),
            "modifications": self._named_list(payload.get("modifications") or payload.get("mods"), ("modId", "name", "id")),
            "cargo": [],
            "notes": payload.get("notes") or payload.get("description") or "",
            "type": "Starship",
            "source": "characterswithoutnumber.app",
        }

        for item in payload.get("cargo") or []:
            if isinstance(item, dict):
                ship_data["cargo"].append({
                    "name": item.get("name") or _pretty_label(item.get("itemId")),
                    "tons": self._coerce_int(item.get("tons") or item.get("quantity"), 0),
                })
            elif isinstance(item, str):
                ship_data["cargo"].append({"name": item, "tons": 0})

        return ship_data, None

    async def _send_target(self, target, content=None, *, embed=None, ephemeral=False):
        kwargs = {}
        if embed is not None:
            kwargs["embed"] = embed
        if isinstance(target, discord.Interaction):
            try:
                if not target.response.is_done():
                    return await target.response.send_message(content, ephemeral=ephemeral, **kwargs)
                return await target.followup.send(content, ephemeral=ephemeral, **kwargs)
            except discord.NotFound:
                return await target.user.send(content, **kwargs)
        destination = target if hasattr(target, "send") else target.channel
        return await destination.send(content, **kwargs)

    def save_ship(self, user_id, ship_data):
        name = "".join(ch for ch in str(ship_data.get("name") or "Imported Ship") if ch.isalnum() or ch == " ").strip()
        if not name:
            name = "Imported Ship"
        existing = self.bot.db.get_ships(user_id)
        is_update = name in existing
        self.bot.db.save_ship(user_id, name, ship_data)
        return name, is_update

    async def import_ship_payload(self, target, data, source_name="starship JSON"):
        ship_data, error = self.parse_swn_ship_json(data)
        if error:
            await self._send_target(target, f"❌ {error}")
            return False
        is_int = isinstance(target, discord.Interaction)
        user_id = target.user.id if is_int else target.author.id
        name, is_update = self.save_ship(user_id, ship_data)
        verb = "Updated" if is_update else "Imported"
        weapons = ", ".join(ship_data["weapons"][:4]) or "no guns mounted"
        msg = (
            f"{verb} starship **{name}** from {source_name} and made it active on this Discord bot.\n"
            f"Hull {_pretty_label(ship_data['hull_id'])} · HP {ship_data['hp']}/{ship_data['max_hp']} · "
            f"AC {ship_data['ac']} · {weapons}.\n"
            f"Say `ship` anytime. Drop a new JSON export to sync changes."
        )
        await self._send_target(target, msg)
        return True

    async def import_ship_source(self, target, url=None, attachment=None):
        sheet_cog = self.bot.get_cog("CharacterSheetCog")
        text = None
        error = None
        if attachment:
            text, error = await sheet_cog._read_attachment_text(attachment)
        elif url:
            payload, error = await sheet_cog.fetch_json_payload(url)
            if error:
                await self._send_target(target, f"❌ {error}")
                return False
            return await self.import_ship_payload(target, payload, source_name=url)
        else:
            error = "Attach a ship JSON export or provide a JSON URL."
        if error:
            await self._send_target(target, f"❌ {error}")
            return False
        try:
            data = json.loads(text)
        except Exception as exc:
            await self._send_target(target, f"❌ Invalid JSON: {exc}")
            return False
        return await self.import_ship_payload(target, data, source_name=attachment.filename if attachment else "JSON")

    async def _send_ship_view(self, ctx_or_interaction):
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        ship = self.bot.db.get_active_ship(user_id)
        if not ship:
            msg = (
                "❌ No active starship on this Discord bot yet. "
                "Export JSON from https://characterswithoutnumber.app/ship-builder/ and drop the file here."
            )
            await self._send_target(ctx_or_interaction, msg, ephemeral=isinstance(ctx_or_interaction, discord.Interaction))
            return

        embed = discord.Embed(title=f"🚀 Starship: {ship['name']}", color=discord.Color.dark_blue())
        embed.set_author(name=f"Hull: {_pretty_label(ship.get('hull_id', 'Unknown'))}")
        stats = f"**HP:** {ship.get('hp', ship.get('max_hp', 0))}/{ship.get('max_hp', 0)}  |  **AC:** {ship.get('ac', 10)}  |  **Armor:** {ship.get('armor', 0)}  |  **Speed:** {ship.get('speed', 0)}"
        extra = []
        if ship.get("power") not in (None, ""):
            extra.append(f"**Power:** {ship['power']}")
        if ship.get("mass") not in (None, ""):
            extra.append(f"**Mass:** {ship['mass']}")
        if extra:
            stats += "  |  " + "  |  ".join(extra)
        embed.description = stats

        if ship.get("fittings"):
            f_text = "\n".join([f"• {item['name']} (x{item.get('count', 1)})" for item in ship["fittings"]])
            embed.add_field(name="Fittings", value=f_text if len(f_text) < 1024 else f_text[:1020] + "...", inline=False)

        if ship.get("weapons"):
            w_text = "\n".join([f"• {weapon}" for weapon in ship["weapons"]])
            embed.add_field(name="Weapons", value=w_text if len(w_text) < 1024 else w_text[:1020] + "...", inline=False)

        if ship.get("defenses"):
            d_text = "\n".join([f"• {item}" for item in ship["defenses"]])
            embed.add_field(name="Defenses", value=d_text[:1024], inline=False)

        if ship.get("notes"):
            embed.add_field(name="Notes", value=ship["notes"][:1024], inline=False)

        embed.set_footer(text="Synced from characterswithoutnumber.app · drop a new JSON to update")
        await self._send_target(ctx_or_interaction, embed=embed)

    @app_commands.command(name="ship", description="View the starship currently synced to this Discord bot.")
    async def ship_view(self, interaction: discord.Interaction):
        await self._send_ship_view(interaction)

    @commands.command(name="ship", help="View the starship currently synced to this Discord bot.")
    async def ship_view_text(self, ctx):
        await self._send_ship_view(ctx)

    async def _send_ship_list(self, ctx_or_interaction):
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        ships = self.bot.db.get_ships(user_id)
        if not ships:
            msg = "❌ No imported starships. Drop a ship JSON from characterswithoutnumber.app."
            await self._send_target(ctx_or_interaction, msg, ephemeral=isinstance(ctx_or_interaction, discord.Interaction))
            return

        desc = "\n".join([f"• {name}" for name in ships])
        embed = discord.Embed(title="🛸 Your Starships", description=desc, color=discord.Color.blue())
        await self._send_target(ctx_or_interaction, embed=embed)

    @app_commands.command(name="shiplist", description="List starships imported to this Discord bot.")
    async def ship_list(self, interaction: discord.Interaction):
        await self._send_ship_list(interaction)

    @commands.command(name="shiplist", help="List starships imported to this Discord bot.")
    async def ship_list_text(self, ctx):
        await self._send_ship_list(ctx)

    @app_commands.command(name="importship", description="Import a characterswithoutnumber.app starship JSON.")
    @app_commands.describe(url="Optional JSON URL", file="Optional uploaded ship JSON")
    async def importship_slash(self, interaction: discord.Interaction, url: str = None, file: discord.Attachment = None):
        await interaction.response.defer()
        await self.import_ship_source(interaction, url=url, attachment=file)

    @commands.command(name="importship", aliases=["uploadship"])
    async def importship_prefix(self, ctx, url: str = None):
        attachment = ctx.message.attachments[0] if ctx.message.attachments else None
        await self.import_ship_source(ctx, url=url, attachment=attachment)


async def setup(bot):
    await bot.add_cog(ShipsCog(bot))
