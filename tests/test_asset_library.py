import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord

from cogs.asset_library import AssetLibraryCog
from services.image_catalog_service import ImageCatalogService, _google_map_candidate


def test_explicit_builtin_map_shows_generated_map():
    sent = []

    async def send(*args, **kwargs):
        sent.append((args, kwargs))

    cog = AssetLibraryCog(SimpleNamespace())
    message = SimpleNamespace(
        content="find map built in forest",
        guild=SimpleNamespace(id=1437247431560400928),
        channel=SimpleNamespace(send=send, guild=SimpleNamespace(id=1437247431560400928)),
    )

    with patch.dict("os.environ", {"TEST_GUILD_ID": "1437247431560400928"}):
        assert asyncio.run(cog.handle_message(message)) is True
        assert sent
        assert sent[0][1]["embed"].title == "Forest Map"
        assert sent[0][1]["embed"].image.url == "attachment://map_forest.png"
    assert isinstance(sent[0][1]["file"], discord.File)


def test_named_map_does_not_silently_use_builtin(monkeypatch):
    cog = AssetLibraryCog(SimpleNamespace())
    monkeypatch.setenv("TEST_GUILD_ID", "1437247431560400928")

    assert cog._find_local_map("forest") is not None
    assert not "forest".startswith(("built in ", "builtin ", "generated "))


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


def test_openverse_map_requires_direct_image_and_open_license():
    direct = {
        "url": "https://example.com/map.png",
        "license": "cc0",
    }
    source_only = {
        "url": "https://example.com/maps/",
        "license": "cc0",
    }

    assert ImageCatalogService.displayable_image_url(direct) == direct["url"]
    assert ImageCatalogService.displayable_image_url(source_only) is None


def test_openverse_relevance_rejects_unrelated_results():
    dungeon = {"title": "Hand Drawn Dungeon Map", "tags": []}
    florida = {"title": "Florida Tour, August 2006", "tags": []}
    wrong_subject = {"title": "City Map of New Orleans", "tags": []}
    reference_map = {"title": "Pacific salmon temperate rain forest map", "tags": []}

    assert ImageCatalogService.relevant_openverse_map(dungeon, "dungeon") is True
    assert ImageCatalogService.relevant_openverse_map(florida, "fantasy") is False
    assert ImageCatalogService.relevant_openverse_map(wrong_subject, "space station") is False
    assert ImageCatalogService.relevant_openverse_map(reference_map, "forest") is False


def test_google_candidate_requires_rpg_map_language():
    items = [
        {
            "title": "Forest reference map",
            "link": "https://example.com/forest.jpg",
            "image": {"contextLink": "https://example.com/reference"},
        },
        {
            "title": "Forest Battlemap for VTT",
            "link": "https://example.com/forest-battlemap.jpg",
            "image": {"contextLink": "https://example.com/rpg"},
        },
    ]

    candidate = _google_map_candidate(items, "forest")

    assert candidate is not None
    assert candidate["license"] == "Needs review"
    assert candidate["url"].endswith("forest-battlemap.jpg")
