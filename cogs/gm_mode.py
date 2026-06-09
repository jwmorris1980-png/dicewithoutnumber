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


class GameMasterSetupModal(discord.ui.Modal, title="Private Game Master Setup"):
    players = discord.ui.TextInput(
        label="How many players?",
        placeholder="Example: 4",
        max_length=2,
    )
    map_theme = discord.ui.TextInput(
        label="Existing map",
        placeholder="space, forest, cave, desert, or custom",
        max_length=20,
    )
    enemies = discord.ui.TextInput(
        label="Enemies: name, count, HP, AC",
        placeholder="guard, 3, 10, 12; boss, 1, 40, 16",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )
    initiative = discord.ui.TextInput(
        label="Roll initiative?",
        placeholder="yes or no",
        max_length=10,
    )

    def __init__(self, cog, guild_id, channel_id, user_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.user_id = user_id

    async def on_submit(self, interaction):
        error, session = self.cog._parse_modal_setup(
            self.guild_id,
            self.channel_id,
            self.user_id,
            str(self.players),
            str(self.map_theme),
            str(self.enemies),
            str(self.initiative),
        )
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await self.cog._finish(session)
        await interaction.followup.send(
            "Encounter posted. Your setup answers remained hidden.",
            ephemeral=True,
        )


class EnemyStatsModal(discord.ui.Modal, title="Private Enemy Stats"):
    hp = discord.ui.TextInput(label="Hit points for each enemy", placeholder="Example: 12", max_length=5)
    ac = discord.ui.TextInput(label="Armor Class (AC)", placeholder="Example: 14", max_length=3)

    def __init__(self, cog, user_id):
        super().__init__()
        self.cog = cog
        self.user_id = int(user_id)

    async def on_submit(self, interaction):
        session = self.cog.sessions.get(self.user_id)
        if not session or interaction.user.id != self.user_id:
            await interaction.response.send_message("This GM Mode session is no longer active.", ephemeral=True)
            return

        hp = self.cog._number(str(self.hp), 1, 10000)
        ac = self.cog._number(str(self.ac), 0, 100)
        if hp is None or ac is None:
            await interaction.response.send_message("HP and AC must be numbers.", ephemeral=True)
            return

        session["pending_enemy"]["hp"] = hp
        session["pending_enemy"]["ac"] = ac
        session["enemy_groups"].append(session.pop("pending_enemy"))
        session["step"] = "more_enemies"
        await interaction.response.send_message("Enemy HP and AC saved privately.", ephemeral=True)

        channel = self.cog.bot.get_channel(session["channel_id"]) or await self.cog.bot.fetch_channel(session["channel_id"])
        await channel.send("Enemy stats saved privately. Do you want to add another kind of enemy? Say `yes` or `no`.")


class EnemyStatsView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=900)
        self.cog = cog
        self.user_id = int(user_id)

    @discord.ui.button(label="Enter Enemy HP & AC Privately", style=discord.ButtonStyle.primary)
    async def enter_stats(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the GM who started this setup can enter these stats.", ephemeral=True)
            return
        await interaction.response.send_modal(EnemyStatsModal(self.cog, self.user_id))


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

    def _is_skip(self, text):
        return self._normalize(text) in {"skip", "skip it", "skip this", "next"}

    def _can_start(self, user, guild, channel):
        permissions = getattr(user, "guild_permissions", None)
        if permissions and (permissions.administrator or permissions.manage_guild):
            return True
        campaign = self.bot.db.get_campaign(guild.id) if guild else None
        if campaign and str(campaign.get("gm_id")) == str(user.id):
            return True
        gm_role_id = self.bot.db.get_setting(channel.id, "gm_role") if channel else None
        return bool(gm_role_id and guild and guild.get_role(int(gm_role_id)) in getattr(user, "roles", []))

    def _parse_modal_setup(self, guild_id, channel_id, user_id, players, map_theme, enemies, initiative):
        player_count = self._number(players, 1, 20)
        if player_count is None:
            return "Players must be a number from 1 to 20.", None

        normalized_theme = self._normalize(map_theme)
        theme = THEMES.get(normalized_theme)
        if not theme:
            return "Map must be `space`, `forest`, `cave`, `desert`, or `custom`.", None

        tracker = self.bot.get_cog("TrackerCog")
        current = tracker.get_guild_tracker(guild_id, channel_id)
        if theme == "custom" and not current.get("background_url"):
            return "This channel does not have an uploaded custom map.", None

        campaign = self.bot.db.get_campaign(guild_id) or {}
        joined = campaign.get("players", {})
        if len(joined) < player_count:
            return (
                f"I found **{len(joined)}** joined character sheet(s), but you entered **{player_count}** players. "
                "Have players import their sheets and use `/campaign join`, then run `/gmmode` again."
            ), None

        enemy_groups = []
        for raw_group in filter(None, (group.strip() for group in enemies.split(";"))):
            parts = [part.strip() for part in raw_group.split(",")]
            if len(parts) != 4:
                return "Each enemy must use `name, count, HP, AC`, separated from other enemies with `;`.", None
            name = parts[0][:50]
            count = self._number(parts[1], 1, 50)
            hp = self._number(parts[2], 1, 10000)
            ac = self._number(parts[3], 0, 100)
            if not name or count is None or hp is None or ac is None:
                return f"Invalid enemy entry: `{raw_group}`. Use `name, count, HP, AC`.", None
            enemy_groups.append({"name": name, "count": count, "hp": hp, "ac": ac})

        roll_initiative = self._yes_no(initiative)
        if roll_initiative is None:
            return "Roll initiative must be `yes` or `no`.", None

        return None, {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "player_count": player_count,
            "theme": theme,
            "enemy_groups": enemy_groups,
            "initiative": roll_initiative,
        }

    async def _reply_start(self, target, message):
        if isinstance(target, discord.Interaction):
            await target.response.send_message(message, ephemeral=True)
        else:
            await target.send(message)

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

        if not interaction:
            self.sessions[int(user.id)] = {
                "step": "players",
                "guild_id": guild.id,
                "channel_id": channel.id,
                "user_id": user.id,
                "started_at": datetime.datetime.now(datetime.timezone.utc),
                "enemy_groups": [],
            }
            await self._reply_start(
                target,
                "**Game Master Mode is starting.** How many players are in this encounter? "
                "Say `skip` at any question you do not need.",
            )
            return

        await interaction.response.send_modal(GameMasterSetupModal(self, guild.id, channel.id, user.id))

    async def handle_message(self, message):
        session = self.sessions.get(int(message.author.id))
        if not session:
            return False
        if message.guild is not None and (
            int(message.guild.id) != int(session["guild_id"])
            or int(message.channel.id) != int(session["channel_id"])
        ):
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
            if self._is_skip(text):
                campaign = self.bot.db.get_campaign(session["guild_id"]) or {}
                joined_count = len(campaign.get("players", {}))
                session["player_count"] = joined_count
                session["step"] = "map"
                await message.channel.send(
                    f"Using all **{joined_count}** joined character sheet(s). "
                    "What map do you want? Say `space`, `forest`, `cave`, `desert`, `custom`, or `skip`."
                )
                return True
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
            if self._is_skip(text):
                campaign = self.bot.db.get_campaign(session["guild_id"]) or {}
                session["player_count"] = len(campaign.get("players", {}))
                session["step"] = "map"
                await message.channel.send("Continuing with the joined sheets. What map do you want, or say `skip`?")
                return True
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
            if self._is_skip(text):
                session["theme"] = "default"
                session["step"] = "enemies"
                await message.channel.send("Using the default space map. Do you want enemies? Say `yes`, `no`, or `skip`.")
                return True
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
            if self._is_skip(text):
                session["step"] = "initiative"
                await message.channel.send("Skipping enemies. Should I roll and track initiative? Say `yes`, `no`, or `skip`.")
                return True
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
            if self._is_skip(text):
                session["step"] = "initiative"
                await message.channel.send("Skipping enemies. Should I roll and track initiative? Say `yes`, `no`, or `skip`.")
                return True
            if not text or len(text) > 50:
                await message.channel.send("Please give the enemy a short name.")
                return True
            session["pending_enemy"] = {"name": message.content.strip()[:50]}
            session["step"] = "enemy_count"
            await message.channel.send("How many of this enemy?")
            return True

        if step == "enemy_count":
            if self._is_skip(text):
                session.pop("pending_enemy", None)
                session["step"] = "more_enemies"
                await message.channel.send("Skipped that enemy. Add another kind of enemy? Say `yes`, `no`, or `skip`.")
                return True
            count = self._number(text, 1, 50)
            if count is None:
                await message.channel.send("Please say an enemy count from 1 to 50.")
                return True
            session["pending_enemy"]["count"] = count
            session["step"] = "enemy_stats"
            await message.channel.send(
                "Enter this enemy's HP and AC privately using the button below.",
                view=EnemyStatsView(self, message.author.id),
            )
            return True

        if step == "enemy_stats":
            if self._is_skip(text):
                session.pop("pending_enemy", None)
                session["step"] = "more_enemies"
                await message.channel.send("Skipped that enemy. Add another kind of enemy? Say `yes`, `no`, or `skip`.")
                return True
            await message.channel.send("Use the **Enter Enemy HP & AC Privately** button above so players cannot see those values.")
            return True

        if step == "more_enemies":
            if self._is_skip(text):
                session["step"] = "initiative"
                await message.channel.send("Should I roll and track initiative? Say `yes`, `no`, or `skip`.")
                return True
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
            if self._is_skip(text):
                session["initiative"] = False
                await message.channel.send("Skipping initiative. Posting the encounter now.")
                await self._finish(session)
                return True
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
            "hidden": enemy, "conditions": [], "distance": "", "x": x, "y": y,
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
