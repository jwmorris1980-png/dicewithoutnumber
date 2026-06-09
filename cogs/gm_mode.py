import datetime
import random
import re

import discord
from discord import app_commands
from discord.ext import commands

from cogs.tracker import MapMovementView


THEMES = {
    "space": "default",
    "void": "default",
    "default": "default",
    "forest": "forest",
    "woods": "forest",
    "cave": "cave",
    "dungeon": "cave",
    "desert": "desert",
    "sand": "desert",
    "custom": "custom",
}

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}


class GameMasterModeCog(commands.Cog):
    """Private, deterministic, voice-first encounter setup."""

    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    def _normalize(self, text):
        return " ".join(re.sub(r"[^\w\s]", " ", str(text).lower()).split())

    def _number(self, text, minimum=0, maximum=1000):
        normalized = self._normalize(text)
        match = re.search(r"\b(\d+)\b", normalized)
        value = int(match.group(1)) if match else WORD_NUMBERS.get(normalized)
        if value is None:
            value = next((number for word, number in WORD_NUMBERS.items() if re.search(rf"\b{word}\b", normalized)), None)
        return value if value is not None and minimum <= value <= maximum else None

    def _yes_no(self, text):
        normalized = self._normalize(text)
        if re.search(r"\b(yes|yeah|yep|sure)\b", normalized):
            return True
        if re.search(r"\b(no|nope|none)\b", normalized):
            return False
        return None

    def _can_start(self, user, guild, channel):
        permissions = getattr(user, "guild_permissions", None)
        if permissions and (permissions.administrator or permissions.manage_guild):
            return True
        campaign = self.bot.db.get_campaign(guild.id) if guild else None
        if campaign and str(campaign.get("gm_id")) == str(user.id):
            return True
        gm_role_id = self.bot.db.get_setting(channel.id, "gm_role") if channel else None
        return bool(gm_role_id and guild and guild.get_role(int(gm_role_id)) in getattr(user, "roles", []))

    async def _reply_start(self, target, message):
        if isinstance(target, discord.Interaction):
            await target.response.send_message(message, ephemeral=True)
        else:
            try:
                await target.message.delete()
            except Exception:
                pass
            await target.send(message, delete_after=12)

    async def _start(self, target):
        interaction = isinstance(target, discord.Interaction)
        user = target.user if interaction else target.author
        guild = target.guild
        channel = target.channel
        if not guild:
            await self._reply_start(target, "Game Master Mode must be started inside a server channel.")
            return
        if not self._can_start(user, guild, channel):
            await self._reply_start(target, "You need GM, Manage Server, or Administrator permission to start Game Master Mode.")
            return

        try:
            dm = await user.create_dm()
            await dm.send(
                "**Private Game Master Mode started.** Your setup answers stay here in DMs. "
                "Only the finished encounter and optional initiative order will appear in the server.\n\n"
                "How many players are in this encounter? Say a number from 1 to 20.\n"
                "Each player should first import their sheet and use `/campaign join` in the server.\n"
                "Say `cancel game master mode` at any time."
            )
        except discord.Forbidden:
            await self._reply_start(target, "I could not DM you. Enable direct messages from server members, then start Game Master Mode again.")
            return

        self.sessions[int(user.id)] = {
            "step": "players",
            "guild_id": guild.id,
            "channel_id": channel.id,
            "user_id": user.id,
            "started_at": datetime.datetime.now(datetime.timezone.utc),
            "enemy_groups": [],
        }
        await self._reply_start(target, "Game Master Mode moved to your DMs so the players cannot see your setup answers.")

    async def handle_message(self, message):
        session = self.sessions.get(int(message.author.id))
        if not session or message.guild is not None:
            return False

        age = datetime.datetime.now(datetime.timezone.utc) - session["started_at"]
        if age.total_seconds() > 1800:
            self.sessions.pop(int(message.author.id), None)
            await message.channel.send("Game Master Mode timed out. Start it again in the server channel.")
            return True

        text = self._normalize(message.content)
        if text in {"cancel", "cancel game master mode", "stop game master mode", "stop"}:
            self.sessions.pop(int(message.author.id), None)
            await message.channel.send("Game Master Mode cancelled.")
            return True

        step = session["step"]
        if step == "players":
            count = self._number(text, 1, 20)
            if count is None:
                await message.channel.send("Please say the number of players, from 1 to 20.")
                return True
            session["player_count"] = count
            campaign = self.bot.db.get_campaign(session["guild_id"]) or {}
            joined = campaign.get("players", {})
            if len(joined) < count:
                await message.channel.send(
                    f"I found **{len(joined)}** joined character sheet(s), but you said **{count}** players.\n"
                    "Have the remaining players import their sheets and use `/campaign join`, then say `ready`."
                )
                session["step"] = "players_ready"
                return True
            session["step"] = "map"
            await message.channel.send("What map do you want? Say `space`, `forest`, `cave`, `desert`, or `custom`.")
            return True

        if step == "players_ready":
            if text != "ready":
                await message.channel.send("Say `ready` after the players have imported their sheets and used `/campaign join`.")
                return True
            campaign = self.bot.db.get_campaign(session["guild_id"]) or {}
            joined = campaign.get("players", {})
            if len(joined) < session["player_count"]:
                await message.channel.send(f"I still found only **{len(joined)}** joined sheet(s).")
                return True
            session["step"] = "map"
            await message.channel.send("What map do you want? Say `space`, `forest`, `cave`, `desert`, or `custom`.")
            return True

        if step == "map":
            theme = next((value for word, value in THEMES.items() if re.search(rf"\b{word}\b", text)), None)
            if not theme:
                await message.channel.send("Please choose `space`, `forest`, `cave`, `desert`, or `custom`.")
                return True
            tracker = self.bot.get_cog("TrackerCog")
            current = tracker.get_guild_tracker(session["guild_id"], session["channel_id"])
            if theme == "custom" and not current.get("background_url"):
                await message.channel.send("That channel has no uploaded custom map. Choose another map.")
                return True
            session["theme"] = theme
            session["step"] = "enemies"
            await message.channel.send("Do you want enemies? Say `yes` or `no`.")
            return True

        if step == "enemies":
            answer = self._yes_no(text)
            if answer is None:
                await message.channel.send("Please say `yes` or `no`.")
                return True
            if not answer:
                session["step"] = "initiative"
                await message.channel.send("Should I roll and track initiative? Say `yes` or `no`.")
                return True
            session["step"] = "enemy_name"
            await message.channel.send("What is this enemy called? For example, `guard` or `space pirate`.")
            return True

        if step == "enemy_name":
            if not text or len(text) > 50:
                await message.channel.send("Please give the enemy a short name.")
                return True
            session["pending_enemy"] = {"name": message.content.strip()[:50]}
            session["step"] = "enemy_count"
            await message.channel.send("How many of this enemy?")
            return True

        if step == "enemy_count":
            count = self._number(text, 1, 50)
            if count is None:
                await message.channel.send("Please say an enemy count from 1 to 50.")
                return True
            session["pending_enemy"]["count"] = count
            session["step"] = "enemy_hp"
            await message.channel.send("How many hit points does each one have?")
            return True

        if step == "enemy_hp":
            hp = self._number(text, 1, 10000)
            if hp is None:
                await message.channel.send("Please say their hit points as a number.")
                return True
            session["pending_enemy"]["hp"] = hp
            session["step"] = "enemy_ac"
            await message.channel.send("What is their AC?")
            return True

        if step == "enemy_ac":
            ac = self._number(text, 0, 100)
            if ac is None:
                await message.channel.send("Please say their AC as a number.")
                return True
            session["pending_enemy"]["ac"] = ac
            session["enemy_groups"].append(session.pop("pending_enemy"))
            session["step"] = "more_enemies"
            await message.channel.send("Do you want to add another kind of enemy? Say `yes` or `no`.")
            return True

        if step == "more_enemies":
            answer = self._yes_no(text)
            if answer is None:
                await message.channel.send("Please say `yes` or `no`.")
                return True
            if answer:
                session["step"] = "enemy_name"
                await message.channel.send("What is the next enemy called?")
                return True
            session["step"] = "initiative"
            await message.channel.send("Should I roll and track initiative? Say `yes` or `no`.")
            return True

        if step == "initiative":
            answer = self._yes_no(text)
            if answer is None:
                await message.channel.send("Please say `yes` or `no`.")
                return True
            session["initiative"] = answer
            await message.channel.send("Setup complete. Posting the encounter in the server channel now.")
            await self._finish(session)
            return True

        return False

    def _combatant(self, token_id, name, hp, ac, x, y, enemy):
        return {
            "id": token_id, "name": name, "max_hp": hp, "current_hp": hp, "ac": ac,
            "hidden": False, "conditions": [], "distance": "", "x": x, "y": y,
            "is_enemy": enemy,
        }

    def _player_combatants(self, session):
        campaign = self.bot.db.get_campaign(session["guild_id"]) or {}
        players = list(campaign.get("players", {}).items())[:session["player_count"]]
        result = []
        for index, (user_id, player) in enumerate(players):
            sheet = self.bot.db.get_active_character(user_id) or {}
            hp = sheet.get("max_hp", sheet.get("hp", player.get("max_hp", 1)))
            ac = sheet.get("ac", player.get("ac", 10))
            name = sheet.get("name", player.get("char_name", f"Player {index + 1}"))
            result.append(self._combatant(index + 1, name, int(hp or 1), int(ac or 10), index % 5, index // 5, False))
        return result

    async def _finish(self, session):
        tracker = self.bot.get_cog("TrackerCog")
        current = tracker.get_guild_tracker(session["guild_id"], session["channel_id"])
        combatants = self._player_combatants(session)
        token_id = len(combatants) + 1
        enemy_index = 0
        for group in session["enemy_groups"]:
            for number in range(group["count"]):
                enemy_index += 1
                name = group["name"] if group["count"] == 1 else f"{group['name']} {number + 1}"
                combatants.append(self._combatant(
                    token_id, name, group["hp"], group["ac"],
                    9 - (enemy_index - 1) % 5, 9 - (enemy_index - 1) // 5, True,
                ))
                token_id += 1

        initiative_lines = []
        if session.get("initiative"):
            for combatant in combatants:
                combatant["initiative"] = random.randint(1, 20)
            combatants.sort(key=lambda item: item["initiative"], reverse=True)
            initiative_lines = [
                f"{index}. **{combatant['name']}** - {combatant['initiative']}"
                for index, combatant in enumerate(combatants, 1)
            ]

        current.update({
            "combatants": combatants,
            "current_turn_index": -1,
            "theme": session["theme"],
            "grid_type": current.get("grid_type", "square"),
        })
        if session["theme"] != "custom":
            current["background_url"] = None
        tracker.save_guild_tracker(session["guild_id"], current, session["channel_id"])
        self.sessions.pop(int(session["user_id"]), None)

        channel = self.bot.get_channel(int(session["channel_id"])) or await self.bot.fetch_channel(int(session["channel_id"]))
        background_path = tracker._get_background_path(current)
        image = tracker.map_renderer.render_map(
            combatants, theme_name=current["theme"], background_path=background_path,
            grid_type=current.get("grid_type", "square"),
        )
        file = discord.File(fp=image, filename="gm-mode-map.png")
        map_url = f"https://dicewithoutnumber.duckdns.org/map?guild_id={session['guild_id']}&channel_id={session['channel_id']}"
        enemy_total = sum(group["count"] for group in session["enemy_groups"])
        embed = discord.Embed(
            title="Game Master Mode Encounter",
            description=(
                f"Map: **{session['theme'].title()}**\n"
                f"Players from character sheets: **{session['player_count']}**\n"
                f"Enemies: **{enemy_total}**\n"
                f"[Open interactive map]({map_url})"
            ),
            color=discord.Color.blue(),
        )
        embed.set_image(url="attachment://gm-mode-map.png")
        await channel.send(embed=embed, file=file, view=MapMovementView(tracker, session["guild_id"], session["channel_id"], combatants))
        if initiative_lines:
            await channel.send("**Initiative Order**\n" + "\n".join(initiative_lines) + "\nUse `tracker next` to advance turns.")

    @app_commands.command(name="gmmode", description="Start private voice-first Game Master encounter setup.")
    async def gm_mode_slash(self, interaction: discord.Interaction):
        await self._start(interaction)

    @commands.command(name="gmmode", aliases=["gamemaster", "gmaster"])
    async def gm_mode_prefix(self, ctx):
        await self._start(ctx)


async def setup(bot):
    await bot.add_cog(GameMasterModeCog(bot))
