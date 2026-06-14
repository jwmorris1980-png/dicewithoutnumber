import discord
from discord import app_commands
from discord.ext import commands
from pathlib import Path
import random

from services.image_catalog_service import ImageCatalogService, _load_admin_key


class AssetLibraryCog(commands.Cog):
    LOCAL_LIBRARY = Path(__file__).resolve().parents[1] / "data" / "library"
    LOCAL_MAPS = {
        "cave": ("map_cave.png", {"cave", "cavern", "underground", "tunnel"}),
        "city": ("map_city.png", {"city", "urban", "street", "town"}),
        "desert": ("map_desert.png", {"desert", "wasteland", "arid"}),
        "dungeon": ("map_dungeon.png", {"dungeon", "ruin", "crypt", "temple"}),
        "forest": ("map_forest.png", {"forest", "woods", "wilderness"}),
        "space": ("map_space.png", {"space", "station", "ship", "starship", "sector"}),
    }

    def __init__(self, bot):
        self.bot = bot
        self.catalog = ImageCatalogService()

    async def cog_unload(self):
        await self.catalog.close()

    # ------------------------------------------------------------------
    # Core send helper
    # ------------------------------------------------------------------

    @classmethod
    def _find_local_map(cls, query: str):
        words = set(str(query or "").lower().replace("-", " ").split())
        for name, (filename, tags) in cls.LOCAL_MAPS.items():
            if name in words or words.intersection(tags):
                path = cls.LOCAL_LIBRARY / filename
                if path.is_file():
                    return name, path
        if not words:
            name = random.choice(sorted(cls.LOCAL_MAPS))
            path = cls.LOCAL_LIBRARY / cls.LOCAL_MAPS[name][0]
            if path.is_file():
                return name, path
        return None

    async def _send_local_map(self, target, name: str, path: Path):
        filename = path.name
        embed = discord.Embed(
            title=f"{name.title()} Map",
            description="Visible map from the DICEwithoutNumber built-in map library.",
            color=discord.Color.teal(),
        )
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text="Built-in DICEwithoutNumber map library")
        await _reply(target, embed=embed, file=discord.File(path, filename=filename))

    async def _send_catalog_result(self, target, entry: dict):
        """Build and send a Discord embed for a catalog entry."""
        data = ImageCatalogService.build_embed_data(entry)

        embed = discord.Embed(
            title=data["title"],
            description=data["description"],
            color=discord.Color.teal(),
            url=data["url"] or None,
        )
        for field in data["fields"]:
            embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])
        embed.set_footer(text=data["footer"])

        # If the entry has a direct image URL, show it inline
        if data.get("image_url"):
            embed.set_image(url=data["image_url"])

        # Source button
        view = discord.ui.View()
        if entry.get("source_page"):
            view.add_item(discord.ui.Button(
                label="View Source / Download",
                url=entry["source_page"],
                style=discord.ButtonStyle.link,
            ))
        if entry.get("license_url"):
            view.add_item(discord.ui.Button(
                label=entry.get("license", "License"),
                url=entry["license_url"],
                style=discord.ButtonStyle.link,
            ))

        await _reply(target, embed=embed, view=view)

    async def _search_and_send(self, target, kind: str, query: str):
        """Query the catalog and send the best match, or a clear 'not found' message."""
        await _defer(target)

        if kind == "map":
            local_map = self._find_local_map(query)
            if local_map:
                await self._send_local_map(target, *local_map)
                return

        # Parse query words into tags + free-text
        tags = query.replace(",", " ").strip() if query else None

        entry = await self.catalog.random_image(image_type=kind, tags=tags or None)

        if entry is None:
            # Try broader search without tag filter
            if tags:
                entry = await self.catalog.random_image(image_type=kind)

        if entry is None:
            msg = (
                f"No {kind} found"
                + (f" matching **{query}**" if query else "")
                + ".\n"
                "The image catalog has no match for that search. "
                "Images are never generated — only real free sources are used."
            )
            await _reply(target, msg)
            return

        if kind == "map" and not ImageCatalogService.displayable_image_url(entry):
            choices = ", ".join(sorted(self.LOCAL_MAPS))
            await _reply(
                target,
                f"I found a credited source for **{entry.get('name', query or 'that map')}**, but it "
                "does not provide an image Discord can display directly.\n"
                f"Ask for one of the visible built-in maps: **{choices}**.\n"
                f"Source: {entry.get('source_page') or entry.get('url')}",
            )
            return

        await self._send_catalog_result(target, entry)

    # ------------------------------------------------------------------
    # Slash commands
    # ------------------------------------------------------------------

    @app_commands.command(name="maplibrary", description="Find a free map from the SWN/CWN/WWN image catalog.")
    @app_commands.describe(query="Keywords to search for, e.g. 'space station' or 'ruins'")
    async def maplibrary_slash(self, interaction: discord.Interaction, query: str = ""):
        await self._search_and_send(interaction, "map", query)

    @app_commands.command(name="portraitlibrary", description="Find a free portrait from the SWN/CWN/WWN image catalog.")
    @app_commands.describe(query="Keywords to search for, e.g. 'psychic female' or 'corporate npc'")
    async def portraitlibrary_slash(self, interaction: discord.Interaction, query: str = ""):
        await self._search_and_send(interaction, "portrait", query)

    @app_commands.command(name="randomimage", description="Get a random free map or portrait from the catalog.")
    @app_commands.describe(
        image_type="map or portrait (leave blank for either)",
        system="SWN, CWN, or WWN (leave blank for all)",
    )
    async def randomimage_slash(
        self,
        interaction: discord.Interaction,
        image_type: str = "",
        system: str = "",
    ):
        await _defer(interaction)
        entry = await self.catalog.random_image(
            image_type=image_type or None,
            system=system.upper() or None,
        )
        if entry is None:
            await _reply(interaction, "No images found in the catalog for those filters.")
            return
        await self._send_catalog_result(interaction, entry)

    # ------------------------------------------------------------------
    # Admin: add image
    # ------------------------------------------------------------------

    @app_commands.command(name="addimage", description="[Admin] Add a free image to the catalog.")
    @app_commands.describe(
        image_id="Unique ID, e.g. swn-map-042",
        image_type="map or portrait",
        name="Display name",
        url="Direct image URL (must be a free/licensed image)",
        source_page="Page where the image lives / can be downloaded",
        artist="Artist or creator name",
        license="License name, e.g. CC BY 4.0 or CC0",
        license_url="URL to the license text",
        attribution="Full attribution string to display to users",
        tags="Comma-separated tags, e.g. space,station,interior",
        systems="Comma-separated systems, e.g. SWN,CWN",
        description="Short description of the image",
    )
    async def addimage_slash(
        self,
        interaction: discord.Interaction,
        image_id: str,
        image_type: str,
        name: str,
        url: str,
        source_page: str,
        artist: str,
        license: str,
        license_url: str,
        attribution: str,
        tags: str = "",
        systems: str = "SWN,CWN",
        description: str = "",
    ):
        admin_key = _load_admin_key()
        if not admin_key:
            await interaction.response.send_message(
                "Image admin key is not configured on this server. Cannot add images.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        entry = {
            "id": image_id.strip(),
            "type": image_type.lower().strip(),
            "name": name.strip(),
            "description": description.strip(),
            "url": url.strip(),
            "thumbnail_url": "",
            "source_page": source_page.strip(),
            "artist": artist.strip(),
            "license": license.strip(),
            "license_url": license_url.strip(),
            "attribution": attribution.strip(),
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "system": [s.strip().upper() for s in systems.split(",") if s.strip()],
            "added": "",
        }

        try:
            result = await self.catalog.add_image(entry, admin_key)
            await interaction.followup.send(
                f"Added **{name}** (`{image_id}`) to the catalog.", ephemeral=True
            )
        except Exception as exc:
            await interaction.followup.send(
                f"Failed to add image: {exc}", ephemeral=True
            )

    # ------------------------------------------------------------------
    # Prefix commands
    # ------------------------------------------------------------------

    @commands.command(name="maplibrary", aliases=["findmap"])
    async def maplibrary_prefix(self, ctx, *, query: str = ""):
        await self._search_and_send(ctx, "map", query)

    @commands.command(name="portraitlibrary", aliases=["findportrait"])
    async def portraitlibrary_prefix(self, ctx, *, query: str = ""):
        await self._search_and_send(ctx, "portrait", query)

    # ------------------------------------------------------------------
    # Natural-language message handler (called from bot.py if wired up)
    # ------------------------------------------------------------------

    async def handle_message(self, message):
        text = " ".join(str(message.content or "").strip().split())
        lower = text.lower()
        for prefix, kind in (
            ("find map ", "map"),
            ("show map ", "map"),
            ("map ", "map"),
            ("give me a map ", "map"),
            ("find portrait ", "portrait"),
            ("show portrait ", "portrait"),
        ):
            if lower.startswith(prefix):
                await self._search_and_send(message.channel, kind, text[len(prefix):])
                return True
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _defer(target):
    if isinstance(target, discord.Interaction) and not target.response.is_done():
        await target.response.defer()


async def _reply(target, content=None, **kwargs):
    kwargs["allowed_mentions"] = discord.AllowedMentions.none()
    if isinstance(target, discord.Interaction):
        if not target.response.is_done():
            await target.response.send_message(content, **kwargs)
        else:
            await target.followup.send(content, **kwargs)
    else:
        await target.send(content, **kwargs)


async def setup(bot):
    await bot.add_cog(AssetLibraryCog(bot))
