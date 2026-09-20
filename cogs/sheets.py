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

CWN_APP_HOST = "characterswithoutnumber.app"
CWN_APP_BUILDERS = {
    "SWN": "https://characterswithoutnumber.app/swn-character-builder/",
    "CWN": "https://characterswithoutnumber.app/cwn-character-builder/",
    "WWN": "https://characterswithoutnumber.app/wwn-character-builder/",
    "AWN": "https://characterswithoutnumber.app/awn-character-builder/",
}
ATTR_KEYS = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")
ATTR_ALIASES = {
    "strength": "strength", "str": "strength",
    "dexterity": "dexterity", "dex": "dexterity",
    "constitution": "constitution", "con": "constitution",
    "intelligence": "intelligence", "int": "intelligence",
    "wisdom": "wisdom", "wis": "wisdom",
    "charisma": "charisma", "cha": "charisma",
}
WEAPON_HINTS = (
    "pistol", "rifle", "shotgun", "smg", "carbine", "revolver", "cannon",
    "sword", "blade", "knife", "dagger", "axe", "spear", "bow", "crossbow",
    "staff", "club", "mace", "hammer", "whip", "stun", "laser", "mag ",
    "monoblade", "monowhip", "unarmed", "punch", "grenade", "launcher",
)

class ImportTextModal(discord.ui.Modal, title='Import from characterswithoutnumber.app'):
    character_text = discord.ui.TextInput(
        label='Paste "Copy Text" Output Here',
        style=discord.TextStyle.paragraph,
        placeholder='e.g. Rey Chen [SWN] Level 1 Expert | Spacer Background\nHP: 8/8 | AC: 13 | AB: +0\n...',
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
        self.cog.bot.db.register_server_character(interaction.guild_id, interaction.user.id, safe_name)
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

    def _sheet_import_error(self, error):
        return (
            f"**Character import could not finish:** {error}\n"
            "**Try these checks:**\n"
            "1. In Google Sheets, set General access to **Anyone with the link - Viewer**.\n"
            "2. Send the full Google Sheets URL, not a shortened or Drive-folder link.\n"
            "3. Use an AWN-compatible sheet, or attach a CSV/TXT/character JSON file.\n"
            "4. If it still fails, send `ticket importsheet failed` and include the link."
        )

    async def _send_target(self, target, content=None, *, embed=None, view=None, ephemeral=False):
        kwargs = {}
        if embed is not None:
            kwargs["embed"] = embed
        if view is not None:
            kwargs["view"] = view

        if not isinstance(target, discord.Interaction):
            destination = target if hasattr(target, "send") else target.channel
            return await destination.send(content, **kwargs)

        interaction_kwargs = {**kwargs, "ephemeral": ephemeral}
        try:
            if not target.response.is_done():
                return await target.response.send_message(content, **interaction_kwargs)
            return await target.followup.send(content, **interaction_kwargs)
        except discord.NotFound:
            # Interaction webhooks expire; preserve the result by sending it privately.
            return await target.user.send(content, **kwargs)

    async def _read_attachment_text(self, attachment):
        try:
            raw = await attachment.read()
            return raw.decode("utf-8-sig"), None
        except Exception as e:
            return None, str(e)

    async def _load_sheet_source(self, url=None, attachment=None):
        if attachment:
            text, error = await self._read_attachment_text(attachment)
            if error:
                return None, error, None

            filename = (attachment.filename or "").lower()
            if filename.endswith(".json"):
                data, error = self._parse_json_text(text)
            elif self._looks_like_cwn_app_text(text):
                data, error = self.parse_cwn_app_text(text, "SWN")
            else:
                data, error = self.parse_awn_google_sheet(text)
            return data, error, None

        if not url:
            return None, "Provide a Google Sheet URL or attach a .csv/.txt/.json file.", None

        if self._is_cwn_app_url(url):
            return await self._load_json_source(url, None)

        data, error = await self.fetch_and_parse_sheet(url)
        return data, error, url

    async def _load_json_source(self, url=None, attachment=None):
        if attachment:
            text, error = await self._read_attachment_text(attachment)
            if error:
                return None, error, None
            return self._parse_json_text(text) + (None,)

        if not url:
            return None, "Provide a JSON URL or attach a .json file.", None

        data, error = await self.fetch_json_character(url)
        return data, error, url

    def _parse_json_text(self, text):
        data, error = self._decode_json_text(text)
        if error:
            return None, error
        return self._normalize_character_data(data)

    def _decode_json_text(self, text):
        try:
            data = json.loads(text)
        except Exception as e:
            return None, f"Invalid JSON: {e}"
        if isinstance(data, list):
            data = next((item for item in data if isinstance(item, dict)), None)
        if not isinstance(data, dict):
            return None, "JSON did not contain a character or ship object."
        return data, None

    async def load_export_payload(self, url=None, attachment=None):
        """Return (kind, payload, error, source_url) for a CWN/SWN JSON export."""
        from cogs.ships import looks_like_ship_payload

        source_url = None
        if attachment:
            text, error = await self._read_attachment_text(attachment)
            if error:
                return None, None, error, None
            data, error = self._decode_json_text(text)
            if error:
                return None, None, error, None
        elif url:
            source_url = url
            data, error = await self.fetch_json_payload(url)
            if error:
                return None, None, error, None
        else:
            return None, None, "Provide a JSON URL or attach a .json file.", None

        if looks_like_ship_payload(data):
            return "ship", data, None, source_url
        character, error = self._normalize_character_data(data)
        return "character", character, error, source_url

    def _coerce_int(self, value, default=0):
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        match = re.search(r"-?\d+", str(value))
        return int(match.group(0)) if match else default

    def _swn_modifier(self, score):
        if score is None:
            return 0
        try:
            score = int(score)
        except (TypeError, ValueError):
            return 0
        if score <= 3:
            return -2
        if score <= 7:
            return -1
        if score <= 13:
            return 0
        if score <= 17:
            return 1
        if score <= 18:
            return 2
        return 3

    def _pretty_label(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        text = re.sub(r'^(swn|cwn|wwn|awn)[-_]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[-_]+', ' ', text)
        return " ".join(part.capitalize() if part.lower() != "ai" else "AI" for part in text.split() if part)

    def _unwrap_character_payload(self, data):
        if isinstance(data, list) and data:
            data = next((item for item in data if isinstance(item, dict)), None)
        if not isinstance(data, dict):
            return None
        for key in ('character', 'sheet', 'data', 'actor'):
            nested = data.get(key)
            if isinstance(nested, dict) and (nested.get('name') or nested.get('classId') or nested.get('system')):
                merged = {**data, **nested}
                merged.pop(key, None)
                data = merged
                break
        foundry = data.get('system')
        if isinstance(foundry, dict) and isinstance(foundry.get('health'), dict) and 'classId' not in data:
            health = foundry.get('health') or {}
            data = {
                **data,
                'name': data.get('name'),
                'hp': health.get('value'),
                'hp_max': health.get('max'),
                'hitPointsCurrent': health.get('value'),
                'hitPointsMax': health.get('max'),
                'attackBonus': foundry.get('ab') or foundry.get('meleeAb'),
                'ac': foundry.get('ac') or foundry.get('baseAc'),
                'system': data.get('gameSystem') or 'SWN',
            }
        return data

    def _looks_like_cwn_app_text(self, text):
        if not text or len(text) > 8000:
            return False
        has_hp = re.search(r'\bHP:\s*\d+', text, re.IGNORECASE)
        has_system = re.search(r'\[(?:SWN|CWN|WWN|AWN)\]', text, re.IGNORECASE)
        has_level = re.search(r'\bLevel\s+\d+', text, re.IGNORECASE)
        has_skills = re.search(r'\bSKILLS\b', text, re.IGNORECASE)
        return bool(has_hp and (has_system or (has_level and has_skills)))

    def _is_cwn_app_url(self, url):
        if not url:
            return False
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            return False
        host = (parsed.hostname or "").lower()
        return host == CWN_APP_HOST or host.endswith("." + CWN_APP_HOST)

    def _cwn_app_share_help(self):
        return (
            "That characterswithoutnumber.app link is a live page, not a JSON file.\n"
            "**Sync it to this Discord bot:**\n"
            "1. Open the character or ship → **Export → JSON**, then drop the file in this channel.\n"
            "2. Or **Export → Copy Text** and paste it here (or use `/importtext`).\n"
            "3. A raw `.json` URL still works with `/importjson` or `/importship`.\n"
            "The bot already in this server will use it for `sheet`, `skill`, `attack`, and `ship`."
        )

    def _equipment_lookup(self, name):
        if not hasattr(self, "_equipment_by_name"):
            index = {}
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "equipment.json")
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    for item in json.load(handle):
                        item_name = str(item.get("name") or "").strip()
                        if item_name:
                            index[item_name.lower()] = item
            except Exception:
                index = {}
            self._equipment_by_name = index
        return self._equipment_by_name.get(str(name or "").strip().lower())

    def _split_attribute(self, raw):
        score = None
        modifier = None
        if isinstance(raw, dict):
            score = raw.get("score") or raw.get("value") or raw.get("base")
            modifier = raw.get("mod") or raw.get("modifier")
        else:
            score = raw
        score = self._coerce_int(score, None)
        modifier = self._coerce_int(modifier, None)
        if score is not None and (isinstance(raw, dict) or abs(score) > 5):
            if modifier is None:
                modifier = self._swn_modifier(score)
            return score, modifier
        if modifier is None:
            modifier = score if score is not None else 0
            score = None
        return score, modifier

    def _normalize_attributes(self, attributes):
        scores = {}
        modifiers = {key: 0 for key in ATTR_KEYS}
        if not isinstance(attributes, dict):
            return scores, modifiers

        parsed = {}
        for raw_key, raw_value in attributes.items():
            key = ATTR_ALIASES.get(str(raw_key).strip().lower())
            if not key:
                continue
            parsed[key] = raw_value

        treat_as_scores = any(isinstance(value, dict) for value in parsed.values())
        if not treat_as_scores:
            numbers = [self._coerce_int(value, None) for value in parsed.values()]
            numbers = [value for value in numbers if value is not None]
            if any(abs(value) > 5 for value in numbers):
                treat_as_scores = True
            elif numbers and min(numbers) >= 3 and max(numbers) <= 18 and len(numbers) >= 4:
                treat_as_scores = True

        for key, raw_value in parsed.items():
            if treat_as_scores:
                score, modifier = self._split_attribute(raw_value if isinstance(raw_value, dict) else {"score": raw_value})
            else:
                score, modifier = self._split_attribute(raw_value)
            if score is not None:
                scores[key] = score
            modifiers[key] = modifier if modifier is not None else 0
        return scores, modifiers

    def _normalize_skills(self, raw_skills):
        skills = {}
        if isinstance(raw_skills, dict):
            for name, value in raw_skills.items():
                label = self._pretty_label(name) or str(name).strip()
                if label:
                    skills[label] = self._coerce_int(value, 0)
            return skills
        if not isinstance(raw_skills, list):
            return skills
        for skill in raw_skills:
            if isinstance(skill, str):
                match = re.match(r'(.+?)[-:](-?\d+)$', skill.strip())
                if match:
                    skills[self._pretty_label(match.group(1)) or match.group(1).strip()] = int(match.group(2))
                continue
            if not isinstance(skill, dict):
                continue
            skill_name = str(
                skill.get("name")
                or skill.get("skill")
                or skill.get("skillId")
                or skill.get("id")
                or ""
            ).strip()
            if not skill_name:
                continue
            skill_value = skill.get("rank")
            if skill_value is None:
                skill_value = skill.get("level")
            if skill_value is None:
                skill_value = skill.get("value")
            skills[self._pretty_label(skill_name) or skill_name] = self._coerce_int(skill_value, 0)
        return skills

    def _normalize_name_list(self, values, id_keys=("name", "id", "focusId", "edgeId")):
        names = []
        if isinstance(values, str) and values.strip():
            return [values.strip()]
        if not isinstance(values, list):
            return names
        for item in values:
            if isinstance(item, str) and item.strip():
                if " " in item or "(" in item:
                    names.append(item.strip())
                else:
                    names.append(self._pretty_label(item) or item.strip())
                continue
            if not isinstance(item, dict):
                continue
            label = None
            for key in id_keys:
                if item.get(key):
                    label = self._pretty_label(item.get(key)) or str(item.get(key)).strip()
                    break
            if not label:
                continue
            level = item.get("level") or item.get("rank")
            if level not in (None, "", 0, "0"):
                label = f"{label} (Lvl {self._coerce_int(level, 1)})"
            names.append(label)
        return names

    def _normalize_weapons(self, data, attack_bonus=0):
        weapons = []
        raw_weapons = data.get("weapons")
        if isinstance(raw_weapons, list):
            for weapon in raw_weapons:
                if isinstance(weapon, str) and weapon.strip():
                    catalog = self._equipment_lookup(weapon)
                    weapons.append({
                        "name": weapon.strip(),
                        "to_hit": attack_bonus,
                        "damage": (catalog or {}).get("damage") or "1d6",
                        "range": (catalog or {}).get("range") or "",
                    })
                    continue
                if not isinstance(weapon, dict):
                    continue
                name = str(weapon.get("name") or weapon.get("itemId") or "").strip()
                if not name:
                    continue
                catalog = self._equipment_lookup(self._pretty_label(name) or name)
                weapons.append({
                    "name": self._pretty_label(name) or name,
                    "to_hit": self._coerce_int(weapon.get("to_hit") or weapon.get("ab") or weapon.get("attackBonus"), attack_bonus),
                    "damage": weapon.get("damage") or weapon.get("customDamage") or (catalog or {}).get("damage") or "1d6",
                    "range": weapon.get("range") or (catalog or {}).get("range") or "",
                    "shock": weapon.get("shock") or "",
                    "trauma_die": weapon.get("trauma_die") or weapon.get("traumaDie") or "",
                    "trauma_rating": weapon.get("trauma_rating") or weapon.get("traumaRating") or "",
                })

        inventory = data.get("inventory")
        if isinstance(inventory, list):
            existing = {weapon["name"].lower() for weapon in weapons}
            for item in inventory:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("customName") or item.get("name") or item.get("itemId") or "").strip()
                pretty = self._pretty_label(name) or name
                if not pretty or pretty.lower() in existing:
                    continue
                catalog = self._equipment_lookup(pretty)
                category = str(item.get("customCategory") or item.get("category") or (catalog or {}).get("type") or "").lower()
                damage = item.get("customDamage") or item.get("damage") or (catalog or {}).get("damage")
                looks_like_weapon = (
                    category in {"weapon", "weapons"}
                    or bool(damage)
                    or any(hint in pretty.lower() for hint in WEAPON_HINTS)
                )
                if not looks_like_weapon:
                    continue
                weapons.append({
                    "name": pretty,
                    "to_hit": attack_bonus,
                    "damage": damage or "1d6",
                    "range": item.get("range") or (catalog or {}).get("range") or "",
                    "shock": item.get("shock") or "",
                    "trauma_die": item.get("traumaDie") or "",
                    "trauma_rating": item.get("traumaRating") or "",
                })
                existing.add(pretty.lower())
        return weapons

    def _first_present(self, data, keys):
        for key in keys:
            if key in data and data[key] not in (None, ""):
                return data[key]
        return None

    def _hp_values(self, data):
        current = self._first_present(data, (
            "hp", "hit_points", "hitPoints", "hitPointsCurrent", "currentHp", "currentHP",
        ))
        maximum = self._first_present(data, ("hp_max", "max_hp", "maxHp", "hitPointsMax", "maxHP"))
        if isinstance(current, dict):
            maximum = maximum if maximum not in (None, "") else current.get("max")
            current = self._first_present(current, ("current", "value", "max"))
        if isinstance(maximum, dict):
            maximum = self._first_present(maximum, ("max", "value"))
        current = self._coerce_int(current, 0)
        maximum = self._coerce_int(maximum, current)
        return current, maximum if maximum else current

    def _class_label(self, data):
        raw = data.get("class") or data.get("role") or data.get("classId") or data.get("class_id")
        background = data.get("background") or data.get("backgroundId")
        label = self._pretty_label(raw) if raw else ""
        if isinstance(data.get("partialClasses"), list) and data.get("partialClasses"):
            parts = [self._pretty_label(part) for part in data["partialClasses"] if part]
            if parts:
                label = "/".join(parts)
        if not label and background:
            label = self._pretty_label(background)
        return label or "Hero"

    def _system_code(self, data):
        raw = str(data.get("system") or data.get("gameSystem") or data.get("ruleset") or "SWN").strip()
        raw = re.sub(r'[^A-Za-z]', '', raw).upper()
        if raw in {"SWN", "CWN", "WWN", "AWN"}:
            return raw
        lowered = str(data.get("gameSystem") or data.get("system") or "").lower()
        for code in ("swn", "cwn", "wwn", "awn"):
            if code in lowered:
                return code.upper()
        return "SWN"

    def _strain_text(self, data):
        strain = data.get("strain") or data.get("system_strain") or data.get("systemStrain")
        if isinstance(strain, dict):
            current = strain.get("current") or strain.get("value") or strain.get("systemStrainCurrent")
            maximum = strain.get("max") or strain.get("maximum") or strain.get("systemStrainMax")
            current = self._coerce_int(current, 0)
            maximum = self._coerce_int(maximum, current)
            return f"{current}/{maximum}" if maximum else str(current)
        if strain not in (None, ""):
            return str(strain)
        current = data.get("systemStrainCurrent")
        maximum = data.get("systemStrainMax")
        if current is None and maximum is None:
            return None
        current = self._coerce_int(current, 0)
        maximum = self._coerce_int(maximum, current)
        return f"{current}/{maximum}" if maximum else str(current)

    def _normalize_character_data(self, data):
        data = self._unwrap_character_payload(data)
        if not isinstance(data, dict):
            return None, "Character data must be a JSON object."

        if "character_name" in data and "name" not in data:
            data["name"] = data["character_name"]
        if "Name" in data and "name" not in data:
            data["name"] = data["Name"]

        name = str(data.get("name") or "").strip()
        if not name:
            return None, "I could not find a character name. Add a `name` field or use the AWN character sheet template."

        attributes = data.get("attributes") or data.get("stats") or {}
        scores, modifiers = self._normalize_attributes(attributes)
        stress = data.get("stress") or {}
        if isinstance(stress, str):
            stress = {"general": stress}
        if not isinstance(stress, dict):
            stress = {}

        hp_value, hp_max = self._hp_values(data)
        attack_bonus = self._coerce_int(
            self._first_present(data, ("attack_bonus", "attackBonus", "ab")),
            0,
        )
        skills = self._normalize_skills(data.get("skills"))
        foci = self._normalize_name_list(data.get("foci") or data.get("selectedFoci"), ("name", "focusId", "id"))
        edges = self._normalize_name_list(data.get("edges") or data.get("selectedEdges"), ("name", "edgeId", "id"))
        equipment = data.get("equipment")
        if not isinstance(equipment, list):
            equipment = []
        equipment = [self._pretty_label(item) if isinstance(item, str) else str(item.get("name") or item.get("itemId") or "") for item in equipment]
        equipment = [item for item in equipment if item]
        if not equipment and isinstance(data.get("inventory"), list):
            for item in data["inventory"]:
                if isinstance(item, dict):
                    label = self._pretty_label(item.get("customName") or item.get("name") or item.get("itemId"))
                    if label:
                        equipment.append(label)

        melee_ac = data.get("melee_ac") or data.get("meleeArmorClass") or data.get("meleeAc")
        normalized = {
            **data,
            "name": name,
            "level": self._coerce_int(data.get("level"), 1),
            "class": self._class_label(data),
            "background": self._pretty_label(data.get("background") or data.get("backgroundId")) or data.get("background"),
            "hp": hp_value,
            "hp_max": hp_max,
            "ac": self._coerce_int(data.get("ac") or data.get("armor_class") or data.get("armorClass"), 10),
            "melee_ac": self._coerce_int(melee_ac, None) if melee_ac not in (None, "") else None,
            "attack_bonus": attack_bonus,
            "attribute_scores": scores,
            "attributes": modifiers,
            "skills": skills,
            "foci": foci,
            "edges": edges,
            "equipment": equipment,
            "weapons": self._normalize_weapons(data, attack_bonus),
            "saves": data.get("saves") or data.get("savingThrows") or {},
            "credits": self._coerce_int(data.get("credits") or data.get("experience"), None) if data.get("credits") is not None else data.get("credits"),
            "strain": self._strain_text(data),
            "stress": stress,
            "system": self._system_code(data),
        }
        return normalized, None
        
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
            
            msg = (
                "❌ You have no characters yet. Fastest path: build at "
                "https://characterswithoutnumber.app then drop the JSON export here, "
                "paste Copy Text, or use `/importjson`."
            )
            await self._send_target(ctx_or_int, msg, ephemeral=is_int)
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
            await self._send_target(ctx_or_int, prompt, view=view, ephemeral=True)
        else:
            await ctx_or_int.send(prompt, view=view)

        await view.wait()
        if view.selected_value:
            target_id = category_id if view.selected_scope == 'category' else channel_id
            self.bot.db.bind_character(user_id, target_id, view.selected_scope, view.selected_value)
            return self.bot.db.get_character(user_id, view.selected_value)
        return None

    def save_character(self, user_id, char_data, name_override=None, source_url=None):
        char_data, error = self._normalize_character_data(char_data)
        if error:
            raise ValueError(error)
        char_name = name_override or char_data.get('name', 'Unknown')
        safe_name = "".join([c for c in char_name if c.isalpha() or c.isdigit() or c==' ']).strip()
        if not safe_name:
            safe_name = "Imported Character"
        is_update = self.bot.db.get_character(user_id, safe_name) is not None
        self.bot.db.save_character(user_id, safe_name, char_data.get('system', 'SWN'), char_data, source_url)
        return safe_name, is_update

    async def _save_imported_character(self, target, char_data, source_url=None, source_name="sheet"):
        is_int = isinstance(target, discord.Interaction)
        user_id = target.user.id if is_int else target.author.id
        try:
            safe_name, is_update = self.save_character(user_id, char_data, source_url=source_url)
        except ValueError as e:
            msg = f"Error: {e}"
            await self._send_target(target, msg)
            return

        verb = "Updated" if is_update else "Imported"
        channel = target.channel
        category_id = getattr(channel, "category_id", None)
        target_id = category_id or channel.id
        target_type = "category" if category_id else "channel"
        self.bot.db.bind_character(user_id, target_id, target_type, safe_name)
        self.bot.db.register_server_character(getattr(getattr(target, "guild", None), "id", None), user_id, safe_name)
        hp_text = self._hp_display(char_data)
        skill_count = len(char_data.get("skills") or {})
        msg = (
            f"{verb} **{safe_name}** from {source_name} and synced them to this Discord bot for this {target_type}.\n"
            f"HP {hp_text} · AC {char_data.get('ac', 10)} · {skill_count} skills ready.\n"
            f"Say `sheet`, `skill notice`, or `attack`. Drop a new JSON export (same name) to sync changes."
        )
        await self._send_target(target, msg)

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

    def _hp_display(self, char_data):
        current = char_data.get("hp", 0)
        maximum = char_data.get("hp_max")
        if maximum not in (None, "", current):
            return f"{current}/{maximum}"
        if maximum not in (None, ""):
            return f"{current}/{maximum}"
        return str(current)

    def _attribute_display(self, char_data):
        modifiers = char_data.get("attributes") or {}
        scores = char_data.get("attribute_scores") or {}
        parts = []
        for key in ATTR_KEYS:
            modifier = self._coerce_int(modifiers.get(key), 0)
            score = scores.get(key)
            if score not in (None, ""):
                parts.append(f"**{key[:3].upper()}**: {score} ({modifier:+d})")
            else:
                parts.append(f"**{key[:3].upper()}**: {modifier:+d}")
        return ", ".join(parts)

    async def _send_sheet_embed(self, target, char_data, view):
        system_display = str(char_data.get('system', 'SWN')).upper()
        color = discord.Color.blue()
        if system_display == "WWN": color = discord.Color.dark_red()
        elif system_display == "CWN": color = discord.Color.dark_grey()
        elif system_display == "AWN": color = discord.Color.dark_gold()
            
        embed = discord.Embed(title=f"Character Sheet: {char_data['name']}", color=color)
        class_label = char_data.get('class', 'Hero')
        background = char_data.get('background')
        author = f"Level {char_data['level']} {class_label} ({system_display})"
        if background and str(background).lower() not in str(class_label).lower():
            author = f"Level {char_data['level']} {class_label} · {background} ({system_display})"
        embed.set_author(name=author)
        if char_data.get('portrait_url'): embed.set_thumbnail(url=char_data['portrait_url'])
        
        hp_text = self._hp_display(char_data)
        ac_text = str(char_data.get('ac', 10))
        if char_data.get('melee_ac') not in (None, "", char_data.get('ac')):
            ac_text = f"{ac_text} (Melee {char_data['melee_ac']})"
        combat_parts = [
            f"**HP:** {hp_text}",
            f"**AC:** {ac_text}",
            f"**Attack Bonus:** +{char_data.get('attack_bonus', 0)}",
        ]
        if char_data.get('strain'):
            combat_parts.append(f"**Strain:** {char_data['strain']}")
        stress = char_data.get('stress') or {}
        if stress:
            stress_text = ", ".join([f"{str(k).title()} {v}" for k, v in stress.items() if v not in (None, "")])
            if stress_text:
                combat_parts.append(f"**Stress:** {stress_text}")
        embed.add_field(name="Combat", value="  |  ".join(combat_parts), inline=False)
        embed.add_field(name="Attributes", value=self._attribute_display(char_data), inline=False)
        
        trained = {k: v for k, v in (char_data.get('skills') or {}).items() if self._coerce_int(v, -99) >= 0}
        if trained: embed.add_field(name="Skills", value=", ".join([f"{k} {v:+d}" for k, v in trained.items()]), inline=False)

        if char_data.get('edges'):
            embed.add_field(name="Edges", value=", ".join(char_data['edges'])[:1024], inline=False)
        
        weapons = char_data.get('weapons') or []
        if weapons:
            lines = []
            for weapon in weapons:
                if isinstance(weapon, str):
                    lines.append(f"• **{weapon}**")
                    continue
                name = weapon.get('name', 'Weapon')
                to_hit = self._coerce_int(weapon.get('to_hit'), 0)
                damage = weapon.get('damage') or '?'
                lines.append(f"• **{name}**: To Hit {to_hit:+d}, Dmg {damage}")
            embed.add_field(name="Weapons", value="\n".join(lines)[:1024], inline=False)
            
            weapon_details = []
            for weapon in weapons:
                if not isinstance(weapon, dict):
                    continue
                detail_parts = []
                if weapon.get('range'):
                    detail_parts.append(f"Range {weapon['range']}")
                if weapon.get('shock'):
                    detail_parts.append(f"Shock {weapon['shock']}")
                if weapon.get('trauma_die'):
                    detail_parts.append(f"Trauma Die {weapon['trauma_die']}")
                if weapon.get('trauma_rating'):
                    detail_parts.append(f"Trauma Rating {weapon['trauma_rating']}")
                if weapon.get('trauma'):
                    detail_parts.append(f"Trauma {weapon['trauma']}")
                if detail_parts:
                    weapon_details.append(f"**{weapon.get('name', 'Weapon')}**: " + ", ".join(detail_parts))
            if weapon_details:
                embed.add_field(name="Weapon Details", value="\n".join(weapon_details)[:1024], inline=False)

        if view == "full":
            if char_data.get('foci'): embed.add_field(name="Foci", value=", ".join(char_data['foci'])[:1024], inline=False)
            if char_data.get('equipment'):
                eq_text = ", ".join(str(item) for item in char_data['equipment'])
                embed.add_field(name="Equipment", value=eq_text[:1020] + "..." if len(eq_text)>1024 else eq_text, inline=False)
            builder = CWN_APP_BUILDERS.get(system_display)
            if builder:
                embed.set_footer(text=f"Update anytime from {CWN_APP_HOST} · {builder}")

        await self._send_target(target, embed=embed)

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
            await self._send_target(target, msg, ephemeral=is_int)
            return
        char_data = self.bot.db.get_character(target.user.id if is_int else target.author.id, char_name)
        char_data['portrait_url'] = image_url
        self.bot.db.save_character(target.user.id if is_int else target.author.id, char_name, char_data.get('system', 'SWN'), char_data)
        embed = discord.Embed(title=f"✅ Portrait Set for {char_name}", color=discord.Color.green())
        embed.set_thumbnail(url=image_url)
        await self._send_target(target, embed=embed)

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
            await self._send_target(target, msg, ephemeral=is_int)
            return
        target_char = name
        if not target_char:
            view = CharacterSelectorView(user.id, char_names, has_category=True)
            prompt = "🎭 Bind which character?"
            await self._send_target(target, prompt, view=view, ephemeral=is_int)
            await view.wait()
            if not view.selected_value: return
            target_char, scope = view.selected_value, view.selected_scope
        
        target_id = target.channel.id if not scope=="category" else (target.channel.category_id or target.channel.id)
        real_scope = scope if (scope=="category" and target.channel.category_id) else "channel"
        self.bot.db.bind_character(user.id, target_id, real_scope, target_char)
        if is_int:
            await self._send_target(target, f"Bound **{target_char}** to {real_scope}.", ephemeral=True)
            return
        await target.send(f"✅ Bound **{target_char}** to {real_scope}.")

    @app_commands.command(name="importtext", description="Paste Copy Text from characterswithoutnumber.app")
    @app_commands.describe(system="SWN, CWN, WWN, or AWN")
    @app_commands.choices(system=[
        app_commands.Choice(name="Stars Without Number", value="SWN"),
        app_commands.Choice(name="Cities Without Number", value="CWN"),
        app_commands.Choice(name="Worlds Without Number", value="WWN"),
        app_commands.Choice(name="Ashes Without Number", value="AWN"),
    ])
    async def importtext(self, interaction: discord.Interaction, system: str = "SWN"):
        await interaction.response.send_modal(ImportTextModal(self, system))

    @app_commands.command(name="importsheet", description="Import a character from a Google Sheet or characterswithoutnumber.app")
    @app_commands.describe(url="Google Sheet, JSON, or characterswithoutnumber.app URL", file="Optional uploaded CSV/JSON file")
    async def importsheet_slash(self, interaction: discord.Interaction, url: str = None, file: discord.Attachment = None):
        await interaction.response.defer()
        char_data, error, source_url = await self._load_sheet_source(url, file)
        if error:
            await interaction.followup.send(self._sheet_import_error(error))
            return

        await self._save_imported_character(interaction, char_data, source_url=source_url, source_name="Google Sheets")

    @commands.command(name="importsheet", aliases=["uploadsheet", "sheetupload"])
    async def importsheet_prefix(self, ctx, url: str = None):
        attachment = ctx.message.attachments[0] if ctx.message.attachments else None
        char_data, error, source_url = await self._load_sheet_source(url, attachment)
        if error:
            await ctx.send(self._sheet_import_error(error))
            return

        await self._save_imported_character(ctx, char_data, source_url=source_url, source_name="Google Sheets")

    @app_commands.command(name="sync", description="Refresh your active character from its linked URL or tell you how to re-drop JSON.")
    async def sync_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._refresh_active_character(interaction)

    @app_commands.command(name="update", description="Refresh your active character from its stored source URL.")
    async def update_slash(self, interaction: discord.Interaction):
        await self.sync_slash(interaction)

    @commands.command(name="update", aliases=["up"])
    async def update_prefix(self, ctx):
        await self.sync_prefix(ctx)

    @commands.command(name="sync")
    async def sync_prefix(self, ctx):
        await self._refresh_active_character(ctx)

    async def _refresh_active_character(self, target):
        char_data = await self.get_active_character_data(target)
        if not char_data:
            return
        source_url = char_data.get("source_url")
        if not source_url:
            await self._send_target(
                target,
                f"**{char_data.get('name', 'That character')}** is already on this Discord bot, but it was imported from a file or Copy Text, so there is no live URL to pull.\n"
                "Export JSON again from https://characterswithoutnumber.app and drop it here (same name updates the sheet).\n"
                "`sheet`, `skill`, and `attack` keep using this character. Or `/link` a raw JSON URL if you host the file.",
            )
            return

        new_data, error, _ = await self._load_character_url(source_url)
        if error:
            await self._send_target(target, f"❌ Sync failed: {error}")
            return

        user_id = target.user.id if isinstance(target, discord.Interaction) else target.author.id
        self.save_character(user_id, new_data, source_url=source_url)
        await self._send_target(
            target,
            f"🔄 Synced **{char_data.get('name')}** from the linked source. "
            "`sheet`, `skill`, and `attack` now use the updated stats.",
        )

    @app_commands.command(name="importjson", description="Import a characterswithoutnumber.app JSON export or URL.")
    @app_commands.describe(url="JSON URL or characterswithoutnumber.app link", file="Optional uploaded JSON file")
    async def importjson_slash(self, interaction: discord.Interaction, url: str = None, file: discord.Attachment = None):
        await interaction.response.defer()
        kind, payload, error, source_url = await self.load_export_payload(url, file)
        if error:
            await interaction.followup.send(self._json_import_error(error))
            return
        if kind == "ship":
            ships_cog = self.bot.get_cog("ShipsCog")
            await ships_cog.import_ship_payload(interaction, payload, source_name=file.filename if file else "JSON")
            return
        await self._save_imported_character(interaction, payload, source_url=source_url, source_name="JSON")

    @commands.command(name="importjson", aliases=["uploadjson"])
    async def importjson_prefix(self, ctx, url: str = None):
        attachment = ctx.message.attachments[0] if ctx.message.attachments else None
        kind, payload, error, source_url = await self.load_export_payload(url, attachment)
        if error:
            await ctx.send(self._json_import_error(error))
            return
        if kind == "ship":
            ships_cog = self.bot.get_cog("ShipsCog")
            await ships_cog.import_ship_payload(ctx, payload, source_name=attachment.filename if attachment else "JSON")
            return
        await self._save_imported_character(ctx, payload, source_url=source_url, source_name="JSON")

    def _json_import_error(self, error):
        if error and "characterswithoutnumber.app" in str(error).lower():
            return str(error)
        return (
            f"**Could not import that JSON:** {error}\n"
            "Drop a characterswithoutnumber.app **Export → JSON** file, paste Copy Text, "
            "or send a direct `.json` URL."
        )

    @app_commands.command(name="link", description="Attach a sheet URL to your active character, or import from it.")
    @app_commands.describe(url="Google Sheet, JSON, or characterswithoutnumber.app URL")
    async def link_slash(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        await self._link_character_source(interaction, url)

    @commands.command(name="link")
    async def link_prefix(self, ctx, url: str = None):
        if not url:
            await ctx.send("Usage: `!link <google sheet, JSON, or characterswithoutnumber.app URL>`")
            return
        await self._link_character_source(ctx, url)

    async def _link_character_source(self, target, url):
        if self._is_cwn_app_url(url) or url.lower().endswith(".json") or "json" in url.lower():
            kind, payload, error, source_url = await self.load_export_payload(url, None)
            if error:
                await self._send_target(target, self._json_import_error(error))
                return
            if kind == "ship":
                ships_cog = self.bot.get_cog("ShipsCog")
                await ships_cog.import_ship_payload(target, payload, source_name=url)
                return
            await self._save_imported_character(target, payload, source_url=source_url or url, source_name="linked sheet")
            return
        char_data, error, source_url = await self._load_sheet_source(url, None)
        if error:
            await self._send_target(target, self._sheet_import_error(error))
            return
        await self._save_imported_character(target, char_data, source_url=source_url or url, source_name="linked sheet")

    async def _load_character_url(self, url):
        if not url:
            return None, "Provide a Google Sheet, JSON, or characterswithoutnumber.app URL.", None
        if self._is_cwn_app_url(url) or url.lower().endswith(".json") or "json" in url.lower():
            return await self._load_json_source(url, None)
        return await self._load_sheet_source(url, None)

    async def fetch_json_payload(self, url):
        try:
            headers = {"Accept": "application/json,text/plain,*/*"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        if self._is_cwn_app_url(url):
                            return None, self._cwn_app_share_help()
                        return None, f"Failed to download JSON (Status {resp.status})."
                    content_type = (resp.headers.get("Content-Type") or "").lower()
                    text = await resp.text()
                    if "json" not in content_type:
                        try:
                            data = json.loads(text)
                        except Exception:
                            if self._is_cwn_app_url(url) or "<html" in text[:200].lower():
                                return None, self._cwn_app_share_help()
                            return None, "That URL did not return JSON."
                    else:
                        try:
                            data = json.loads(text)
                        except Exception as e:
                            return None, f"Invalid JSON: {e}"
                    if isinstance(data, list):
                        data = next((item for item in data if isinstance(item, dict)), None)
                    if not isinstance(data, dict):
                        return None, "JSON did not contain a character or ship object."
                    return data, None
        except Exception as e:
            if self._is_cwn_app_url(url):
                return None, self._cwn_app_share_help()
            return None, str(e)

    async def fetch_json_character(self, url):
        data, error = await self.fetch_json_payload(url)
        if error:
            return None, error
        from cogs.ships import looks_like_ship_payload
        if looks_like_ship_payload(data):
            return None, "That JSON is a starship. Drop it in this channel or use `/importship`."
        return self._normalize_character_data(data)

    async def fetch_and_parse_sheet(self, url):
        # Extract Sheet ID and GID
        if self._is_cwn_app_url(url) or url.endswith('.json') or 'json' in url.lower():
            return await self.fetch_json_character(url)

        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not match: return None, "Invalid Google Sheet URL."
        sheet_id = match.group(1)
        
        gid = None
        gid_match = re.search(r'gid=([0-9]+)', url)
        if gid_match: gid = gid_match.group(1)
        
        # AWN template specific: If user provides the Welcome tab GID, switch to Character Sheet GID
        if gid == "1671565117": gid = self.awn_sheet_gid

        candidate_gids = []
        if gid:
            candidate_gids.append(gid)
        else:
            candidate_gids.append("0")
        for fallback_gid in (self.awn_sheet_gid, "0"):
            if fallback_gid not in candidate_gids:
                candidate_gids.append(fallback_gid)
        
        errors = []
        try:
            async with aiohttp.ClientSession() as session:
                for candidate_gid in candidate_gids:
                    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={candidate_gid}"
                    async with session.get(csv_url) as resp:
                        if resp.status != 200:
                            errors.append(f"gid {candidate_gid}: download status {resp.status}")
                            continue
                        content = await resp.text()
                    data, error = self.parse_awn_google_sheet(content)
                    if not error:
                        return data, None
                    errors.append(f"gid {candidate_gid}: {error}")

                if errors:
                    return None, "Could not parse any visible sheet tab. " + " | ".join(errors[:3])
                return None, "Could not find a visible sheet tab to import."
        except Exception as e:
            return None, str(e)

    def parse_awn_google_sheet(self, csv_text):
        try:
            f = io.StringIO(csv_text)
            reader = list(csv.reader(f))

            first_cell = (reader[0][0] if reader and reader[0] else "").lower()
            if "cities without number" in first_cell:
                return self.parse_cwn_google_sheet(reader)

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

            return self._normalize_character_data(char_data)
        except Exception as e:
            return None, f"Parsing error: {str(e)}"

    def parse_cwn_google_sheet(self, reader):
        def get_val(r, c, default=""):
            try: return reader[r][c].strip()
            except: return default

        def row_values(r):
            try: return [str(cell).strip() for cell in reader[r]]
            except: return []

        def find_after(label, default=""):
            label = label.lower()
            for row in reader[:40]:
                for i, cell in enumerate(row):
                    text = str(cell).strip()
                    lower = text.lower()
                    if lower == label:
                        for value in row[i + 1:]:
                            value = str(value).strip()
                            if value:
                                return value
                    if lower.startswith(label + " "):
                        value = text[len(label):].strip()
                        if value:
                            return value
            return default

        def find_resource(label):
            label = label.lower()
            for row in reader[:40]:
                for i, cell in enumerate(row):
                    if str(cell).strip().lower() != label:
                        continue
                    values = [str(v).strip() for v in row[i + 1:i + 12] if str(v).strip()]
                    numbers = [self._coerce_int(v, None) for v in values]
                    numbers = [n for n in numbers if n is not None]
                    if len(numbers) >= 2:
                        return f"{numbers[0]}/{numbers[-1]}"
                    if len(numbers) == 1:
                        return str(numbers[0])
            return ""

        attributes = {}
        attr_labels = {
            "strength": "strength",
            "dexterity": "dexterity",
            "constitution": "constitution",
            "intelligence": "intelligence",
            "wisdom": "wisdom",
            "charisma": "charisma",
        }
        for r, row in enumerate(reader):
            for i, cell in enumerate(row):
                label = str(cell).strip().lower()
                if label in attr_labels:
                    modifier = get_val(r, i + 7) or get_val(r, i + 6) or "0"
                    attributes[attr_labels[label]] = self._coerce_int(modifier, 0)

        skills = {}
        skill_start = None
        for r, row in enumerate(reader):
            if any(str(cell).strip().lower() == "skills" for cell in row):
                skill_start = r + 1
                break
        if skill_start:
            for r in range(skill_start, min(skill_start + 30, len(reader))):
                name = get_val(r, 1).lower()
                if not name or name in {"funds", "weapons"}:
                    continue
                value = None
                for cell in row_values(r)[2:12]:
                    if re.fullmatch(r"[+-]?\d+", cell):
                        value = int(cell)
                if value is not None:
                    skills[name] = value

        weapons = []
        for r, row in enumerate(reader[:35]):
            for i, cell in enumerate(row):
                name = str(cell).strip()
                if not name or name.lower() in {"ranged weapons", "melee weapons", "armour"}:
                    continue
                if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", name):
                    continue
                if "/" in name or " ac" in name.lower():
                    continue
                damage = get_val(r, i + 5)
                if re.search(r"\d+d\d+", damage):
                    trauma = get_val(r, i + 14)
                    trauma_parts = [part.strip() for part in re.split(r"[;；]", trauma) if part.strip()]
                    weapons.append({
                        "name": name,
                        "to_hit": self._coerce_int(get_val(r, i + 12), 0),
                        "damage": damage,
                        "range": get_val(r, i + 7),
                        "trauma_die": trauma_parts[0] if trauma_parts else "",
                        "trauma_rating": trauma_parts[1] if len(trauma_parts) > 1 else "",
                        "trauma": trauma if len(trauma_parts) <= 1 else "",
                        "shock": get_val(r, i + 3) if "shock" in " ".join(row_values(max(r - 1, 0))).lower() else "",
                    })

        # The standard CWN sheet places the character name in B4 without a
        # nearby "Name" label, while some variants use a labeled field.
        character_name = find_after("name") or get_val(3, 1) or "Unknown Operator"
        char_data = {
            "name": character_name,
            "level": self._coerce_int(find_after("level"), 1),
            "class": find_after("background", "Operator"),
            "hp": self._coerce_int(find_after("current hp") or find_after("hp"), 0),
            "ac": self._coerce_int(find_after("ranged ac") or find_after("melee ac"), 10),
            "attack_bonus": self._coerce_int(find_after("attack bonus"), 0),
            "attributes": attributes,
            "skills": skills,
            "weapons": weapons,
            "strain": find_resource("system strain"),
            "stress": {
                "mental": find_resource("mental"),
                "physical": find_resource("physical"),
            },
            "system": "CWN",
        }
        return self._normalize_character_data(char_data)

    def parse_cwn_app_text(self, text, system):
        lines = text.split('\n')
        char_data = {
            'name': lines[0].strip() if lines else 'Unknown',
            'level': 1,
            'class': 'Expert',
            'hp': 0,
            'ac': 10,
            'attack_bonus': 0,
            'attributes': {},
            'skills': {},
            'weapons': [],
            'foci': [],
            'equipment': [],
            'system': system,
        }
        try:
            system_match = re.search(r'\[(SWN|CWN|WWN|AWN)\]', text, re.IGNORECASE)
            if system_match:
                char_data['system'] = system_match.group(1).upper()
            normalized_text = re.sub(
                r'\s+(?=(?:HP|AC|AB|ATTRIBUTES|SAVING THROWS|SKILLS|FOCI|EDGES|CONTACTS|EQUIPMENT|WEAPONS)\s*:?)',
                '\n',
                text,
                flags=re.IGNORECASE,
            )
            lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
            char_data['name'] = re.sub(r'\s+\[(?:SWN|CWN|WWN|AWN)\].*$', '', lines[0], flags=re.IGNORECASE).strip()

            section = None
            for line in lines:
                upper = line.upper()
                for heading in ('ATTRIBUTES', 'SAVING THROWS', 'SKILLS', 'FOCI', 'EDGES', 'CONTACTS', 'EQUIPMENT', 'WEAPONS'):
                    if upper == heading or upper.startswith(heading + ' '):
                        section = heading
                        line = line[len(heading):].strip()
                        upper = line.upper()
                        break
                if not line:
                    continue
                if match := re.search(r'\bLevel\s+(\d+)\s+(.+?)(?:\s*\||$)', line, re.IGNORECASE):
                    char_data['level'] = int(match.group(1))
                    class_text = match.group(2).strip()
                    class_text = re.sub(r'\s*\|\s*.+$', '', class_text).strip()
                    char_data['class'] = re.sub(r'\s+Background$', '', class_text, flags=re.IGNORECASE).strip()
                if match := re.search(r'\|\s*([A-Za-z][A-Za-z ]+?)\s+Background\b', line, re.IGNORECASE):
                    char_data['background'] = match.group(1).strip()
                if match := re.search(r'\bHP:\s*(\d+)(?:/(\d+))?', line, re.IGNORECASE):
                    char_data['hp'] = int(match.group(1))
                    if match.group(2):
                        char_data['hp_max'] = int(match.group(2))
                if match := re.search(r'\bAC:\s*(\d+)', line, re.IGNORECASE):
                    char_data['ac'] = int(match.group(1))
                if match := re.search(r'\b(?:AB|Attack Bonus):\s*\+?(-?\d+)', line, re.IGNORECASE):
                    char_data['attack_bonus'] = int(match.group(1))
                if match := re.search(r'\bStrain:\s*(\d+(?:/\d+)?)', line, re.IGNORECASE):
                    char_data['strain'] = match.group(1)
                if section == 'ATTRIBUTES':
                    for attr, score, modifier in re.findall(
                        r'\b(STR|DEX|CON|INT|WIS|CHA)[A-Z]*:\s*(\d+)\s*(?:\(([+-]?\d+)\))?',
                        line,
                        re.IGNORECASE,
                    ):
                        key = ATTR_ALIASES[attr.lower()[:3]]
                        char_data['attributes'][key] = {
                            'score': int(score),
                            'mod': int(modifier) if modifier != '' else self._swn_modifier(int(score)),
                        } if modifier != '' else int(score)
                if section == 'SKILLS':
                    for skill_name, skill_value in re.findall(r'([A-Za-z][A-Za-z ]*?)-(-?\d+)(?=,|$)', line):
                        char_data['skills'][skill_name.strip()] = int(skill_value)
                if section == 'FOCI' and line:
                    char_data['foci'] = [part.strip() for part in re.split(r',\s*', line) if part.strip()]
                if section == 'EDGES' and line:
                    char_data['edges'] = [part.strip() for part in re.split(r',\s*', line) if part.strip()]
                if section == 'EQUIPMENT' and line:
                    char_data['equipment'] = [part.strip() for part in re.split(r',\s*', line) if part.strip()]

            return self._normalize_character_data(char_data)
        except Exception as e: return None, str(e)

async def setup(bot):
    await bot.add_cog(CharacterSheetCog(bot))
