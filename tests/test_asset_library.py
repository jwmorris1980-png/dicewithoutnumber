import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord

from cogs.asset_library import AssetLibraryCog
from services.image_catalog_service import ImageCatalogService


def test_asset_library_finds_maps_and_voice_phrase():
    sent = []

    async def send(*args, **kwargs):
        sent.append((args, kwargs))

    cog = AssetLibraryCog(SimpleNamespace())
    message = SimpleNamespace(
        content="find map forest",
        guild=SimpleNamespace(id=1437247431560400928),
        channel=SimpleNamespace(send=send, guild=SimpleNamespace(id=1437247431560400928)),
    )

    with patch.dict("os.environ", {"TEST_GUILD_ID": "1437247431560400928"}):
        assert asyncio.run(cog.handle_message(message)) is True
        assert sent
        assert sent[0][1]["embed"].title == "Forest Map"
        assert sent[0][1]["embed"].image.url == "attachment://map_forest.png"
        assert isinstance(sent[0][1]["file"], discord.File)


def test_collection_page_is_not_treated_as_displayable_image():
    assert AssetLibraryCog._find_local_map("show me a city") is not None
    assert ImageCatalogService.displayable_image_url({"url": "https://example.com/maps/"}) is None
    assert ImageCatalogService.displayable_image_url(
        {"url": "https://example.com/maps/forest.png"}
    ) == "https://example.com/maps/forest.png"


def test_visible_map_feature_is_not_enabled_in_other_servers(monkeypatch):
    monkeypatch.setenv("TEST_GUILD_ID", "1437247431560400928")
    other_server = SimpleNamespace(guild=SimpleNamespace(id=999))

    assert AssetLibraryCog._is_test_area(other_server) is False
