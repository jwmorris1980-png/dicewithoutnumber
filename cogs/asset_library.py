import os
import random

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw


ASSETS = {
    "map": {
        "forest": ("forest woodland trees green", (43, 82, 48), (79, 125, 70)),
        "cave": ("cave cavern underground stone", (45, 44, 49), (92, 86, 82)),
        "desert": ("desert dunes wasteland sand", (174, 126, 65), (222, 177, 101)),
        "space": ("space stars void galaxy", (9, 17, 38), (70, 107, 156)),
        "city": ("city streets urban cyberpunk", (48, 57, 65), (105, 120, 130)),
        "dungeon": ("dungeon rooms stone corridors", (55, 52, 47), (121, 111, 93)),
    },
    "portrait": {
        "operative": ("operative agent cyberpunk human", (35, 57, 77), (91, 170, 199)),
        "warrior": ("warrior soldier fighter human", (76, 38, 34), (192, 89, 72)),
        "explorer": ("explorer scout traveler human", (42, 69, 48), (111, 176, 105)),
        "mystic": ("mystic psychic mage human", (59, 44, 77), (151, 112, 190)),
    },
}


class AssetLibraryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.library_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "library")
        os.makedirs(self.library_dir, exist_ok=True)
        self._create_starter_assets()

    def _create_starter_assets(self):
        for kind, assets in ASSETS.items():
            for name, (_tags, background, accent) in assets.items():
                path = self._path(kind, name)
                if os.path.exists(path):
                    continue
                if kind == "map":
                    self._draw_map(path, name, background, accent)
                else:
                    self._draw_portrait(path, name, background, accent)

    def _path(self, kind, name):
        return os.path.join(self.library_dir, f"{kind}_{name}.png")

    def _draw_map(self, path, name, background, accent):
        rng = random.Random(name)
        image = Image.new("RGB", (1024, 1024), background)
        draw = ImageDraw.Draw(image)
        for x in range(0, 1025, 64):
            draw.line((x, 0, x, 1024), fill=tuple(max(0, c - 18) for c in background), width=2)
        for y in range(0, 1025, 64):
            draw.line((0, y, 1024, y), fill=tuple(max(0, c - 18) for c in background), width=2)
        for _ in range(75):
            x, y = rng.randrange(20, 980), rng.randrange(20, 980)
            size = rng.randrange(12, 55)
            draw.ellipse((x - size, y - size, x + size, y + size), fill=accent, outline=(20, 25, 25), width=3)
        draw.rectangle((20, 20, 300, 70), fill=(15, 18, 20))
        draw.text((35, 35), f"{name.title()} Map | 64px grid", fill="white")
        image.save(path, optimize=True)

    def _draw_portrait(self, path, name, background, accent):
        image = Image.new("RGB", (768, 768), background)
        draw = ImageDraw.Draw(image)
        draw.ellipse((244, 110, 524, 390), fill=accent)
        draw.rounded_rectangle((150, 360, 618, 760), radius=180, fill=accent)
        draw.rectangle((20, 20, 310, 70), fill=(15, 18, 20))
        draw.text((35, 35), f"{name.title()} Portrait", fill="white")
        image.save(path, optimize=True)

    def _find(self, kind, query):
        words = set((query or "").lower().split())
        matches = []
        for name, (tags, _background, _accent) in ASSETS[kind].items():
            score = len(words & set(tags.split()))
            if not words or score:
                matches.append((score, name))
        matches.sort(key=lambda item: (-item[0], item[1]))
        return matches[0][1] if matches else None

    async def _send_asset(self, target, kind, query):
        name = self._find(kind, query)
        if not name:
            available = ", ".join(ASSETS[kind])
            await self._send(target, f"No {kind} matched `{query}`. Available: {available}")
            return
        filename = f"{kind}_{name}.png"
        embed = discord.Embed(
            title=f"{name.title()} {kind.title()}",
            description="Download, copy, or repost this file freely.",
            color=discord.Color.green(),
        )
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text="Creator: DICEwithoutNumber | License: CC0 / public domain dedication")
        await self._send(target, embed=embed, file=discord.File(self._path(kind, name), filename=filename))

    async def _send(self, target, content=None, **kwargs):
        kwargs["allowed_mentions"] = discord.AllowedMentions.none()
        if isinstance(target, discord.Interaction):
            if not target.response.is_done():
                await target.response.send_message(content, **kwargs)
            else:
                await target.followup.send(content, **kwargs)
        else:
            await target.send(content, **kwargs)

    async def handle_message(self, message):
        text = " ".join(str(message.content or "").strip().split())
        lower = text.lower()
        for prefix, kind in (("find map ", "map"), ("show map ", "map"), ("find portrait ", "portrait"), ("show portrait ", "portrait")):
            if lower.startswith(prefix):
                await self._send_asset(message.channel, kind, text[len(prefix):])
                return True
        return False

    @app_commands.command(name="maplibrary", description="Find a free downloadable map from the bot library.")
    async def maplibrary_slash(self, interaction: discord.Interaction, query: str = ""):
        await self._send_asset(interaction, "map", query)

    @commands.command(name="maplibrary", aliases=["findmap"])
    async def maplibrary_prefix(self, ctx, *, query: str = ""):
        await self._send_asset(ctx, "map", query)

    @app_commands.command(name="portraitlibrary", description="Find a free downloadable portrait from the bot library.")
    async def portraitlibrary_slash(self, interaction: discord.Interaction, query: str = ""):
        await self._send_asset(interaction, "portrait", query)

    @commands.command(name="portraitlibrary", aliases=["findportrait"])
    async def portraitlibrary_prefix(self, ctx, *, query: str = ""):
        await self._send_asset(ctx, "portrait", query)


async def setup(bot):
    await bot.add_cog(AssetLibraryCog(bot))
