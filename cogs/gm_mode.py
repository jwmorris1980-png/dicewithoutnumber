import datetime
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

ENEMY_PRESETS = {
    "minion": {"hp": 5, "ac": 10},
    "soldier": {"hp": 10, "ac": 12},
    "elite": {"hp": 20, "ac": 14},
    "boss": {"hp": 40, "ac": 16},
}

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}


class GameMasterModeCog(commands.Cog):
    """Deterministic voice-first encounter setup using existing map themes."""

    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    def _key(self, user_id, channel_id):
        return int(user_id), int(channel_id)

    def _normalize(self, text):
        return " ".join(re.sub(r"[^\w\s]", " ", str(text).lower()).split())

    def _number(self, text, minimum=0, maximum=20):
        normalized = self._normalize(text)
        match = re.search(r"\b(\d+)\b", normalized)
        value = int(match.group(1)) if match else WORD_NUMBERS.get(normalized)
        if value is None:
            value = next((number for word, number in WORD_NUMBERS.items() if re.search(rf"\b{word}\b", normalized)), None)
        if value is None or not minimum <= value <= maximum:
            return None
        return value

    def _yes_no(self, text):
        normalized = self._normalize(text)
        if re.search(r"\b(yes|yeah|yep|sure)\b", normalized) or normalized in {"add enemies", "with enemies"}:
            return True
        if re.search(r"\b(no|nope|none)\b", normalized) or normalized == "without enemies":
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

    async def _start(self, target):
        interaction = isinstance(target, discord.Interaction)
        user = target.user if interaction else target.author
        guild = target.guild
        channel = target.channel
        if not guild:
            message = "Game Master Mode must be started inside a server channel."
            if interaction:
                await target.response.send_message(message, ephemeral=True)
            else:
                await target.send(message)
            return
        if not self._can_start(user, guild, channel):
            message = "You need GM, Manage Server, or Administrator permission to start Game Master Mode."
            if interaction:
                await target.response.send_message(message, ephemeral=True)
            else:
                await target.send(message)
            return

        self.sessions[self._key(user.id, channel.id)] = {
            "step": "pieces",
            "guild_id": guild.id,
            "channel_id": channel.id,
            "user_id": user.id,
            "started_at": datetime.datetime.now(datetime.timezone.utc),
        }
        prompt = (
            "**Game Master Mode started.** I will only use fixed choices and existing maps.\n"
            "How many player pieces do you have? Say a number from 1 to 20.\n"
            "Say `cancel game master mode` at any time."
        )
        if interaction:
            await target.response.send_message(prompt)
        else:
            await target.send(prompt)

    async def handle_message(self, message):
        key = self._key(message.author.id, message.channel.id)
        session = self.sessions.get(key)
        if not session:
            return False

        age = datetime.datetime.now(datetime.timezone.utc) - session["started_at"]
        if age.total_seconds() > 900:
            self.sessions.pop(key, None)
            await message.channel.send("Game Master Mode timed out. Say `game master mode` to start again.")
            return True

        text = self._normalize(message.content)
        if text in {"cancel", "cancel game master mode", "stop game master mode", "stop"}:
            self.sessions.pop(key, None)
            await message.channel.send("Game Master Mode cancelled.")
            return True

        step = session["step"]
        if step == "pieces":
            pieces = self._number(text, 1, 20)
            if pieces is None:
                await message.channel.send("Please say the number of player pieces, from 1 to 20.")
                return True
            session["pieces"] = pieces
            session["step"] = "map"
            await message.channel.send("What kind of map do you want? Say `space`, `forest`, `cave`, `desert`, or `custom`.")
            return True

        if step == "map":
            theme = next((value for word, value in THEMES.items() if re.search(rf"\b{word}\b", text)), None)
            if not theme:
                await message.channel.send("Please choose `space`, `forest`, `cave`, `desert`, or `custom`.")
                return True
            tracker = self.bot.get_cog("TrackerCog")
            current = tracker.get_guild_tracker(session["guild_id"], session["channel_id"])
            if theme == "custom" and not current.get("background_url"):
                await message.channel.send("This channel has no uploaded custom map. Choose `space`, `forest`, `cave`, or `desert`.")
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
                session["enemy_count"] = 0
                await self._finish(message, session)
                return True
            session["step"] = "enemy_count"
            await message.channel.send("How many enemies do you want? Say a number from 1 to 20.")
            return True

        if step == "enemy_count":
            count = self._number(text, 1, 20)
            if count is None:
                await message.channel.send("Please say the number of enemies, from 1 to 20.")
                return True
            session["enemy_count"] = count
            session["step"] = "enemy_type"
            await message.channel.send("What kind of enemies? Say `minion`, `soldier`, `elite`, or `boss`.")
            return True

        if step == "enemy_type":
            enemy_type = next((name for name in ENEMY_PRESETS if re.search(rf"\b{name}s?\b", text)), None)
            if not enemy_type:
                await message.channel.send("Please choose `minion`, `soldier`, `elite`, or `boss`.")
                return True
            session["enemy_type"] = enemy_type
            await self._finish(message, session)
            return True

        return False

    def _combatant(self, token_id, name, hp, ac, x, y, enemy):
        return {
            "id": token_id,
            "name": name,
            "max_hp": hp,
            "current_hp": hp,
            "ac": ac,
            "hidden": False,
            "conditions": [],
            "distance": "",
            "x": x,
            "y": y,
            "is_enemy": enemy,
        }

    async def _finish(self, message, session):
        tracker = self.bot.get_cog("TrackerCog")
        current = tracker.get_guild_tracker(session["guild_id"], session["channel_id"])
        combatants = []
        token_id = 1
        for index in range(session["pieces"]):
            combatants.append(self._combatant(token_id, f"Player Piece {index + 1}", 10, 10, index % 5, index // 5, False))
            token_id += 1

        enemy_type = session.get("enemy_type", "minion")
        preset = ENEMY_PRESETS[enemy_type]
        for index in range(session.get("enemy_count", 0)):
            combatants.append(self._combatant(token_id, f"{enemy_type.title()} {index + 1}", preset["hp"], preset["ac"], 9 - (index % 5), 9 - (index // 5), True))
            token_id += 1

        current.update({
            "combatants": combatants,
            "current_turn_index": -1,
            "theme": session["theme"],
            "grid_type": current.get("grid_type", "square"),
        })
        if session["theme"] != "custom":
            current["background_url"] = None
        tracker.save_guild_tracker(session["guild_id"], current, session["channel_id"])
        self.sessions.pop(self._key(session["user_id"], session["channel_id"]), None)

        background_path = tracker._get_background_path(current)
        image = tracker.map_renderer.render_map(
            current["combatants"],
            theme_name=current["theme"],
            background_path=background_path,
            grid_type=current.get("grid_type", "square"),
        )
        file = discord.File(fp=image, filename="gm-mode-map.png")
        map_url = f"https://dicewithoutnumber.duckdns.org/map?guild_id={session['guild_id']}&channel_id={session['channel_id']}"
        embed = discord.Embed(
            title="Game Master Mode Encounter",
            description=(
                f"Map: **{session['theme'].title()}**\n"
                f"Player pieces: **{session['pieces']}**\n"
                f"Enemies: **{session.get('enemy_count', 0)}**"
                + (f" {enemy_type.title()}" if session.get("enemy_count", 0) else "")
                + f"\n[Open interactive map]({map_url})"
            ),
            color=discord.Color.blue(),
        )
        embed.set_image(url="attachment://gm-mode-map.png")
        await message.channel.send(
            embed=embed,
            file=file,
            view=MapMovementView(tracker, session["guild_id"], session["channel_id"], combatants),
        )

    @app_commands.command(name="gmmode", description="Start deterministic voice-first Game Master encounter setup.")
    async def gm_mode_slash(self, interaction: discord.Interaction):
        await self._start(interaction)

    @commands.command(name="gmmode", aliases=["gamemaster", "gmaster"])
    async def gm_mode_prefix(self, ctx):
        await self._start(ctx)


async def setup(bot):
    await bot.add_cog(GameMasterModeCog(bot))
