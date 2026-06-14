import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from cogs.asset_library import AssetLibraryCog


def test_asset_library_finds_maps_and_voice_phrase():
    sent = []

    async def send(*args, **kwargs):
        sent.append((args, kwargs))

    cog = AssetLibraryCog(SimpleNamespace())
    entry = {
        "name": "Dark Forest",
        "description": "A dark forest battle map.",
        "source_page": "https://example.com/forest",
        "license": "CC0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "artist": "Test Artist",
        "attribution": "Test Artist, CC0",
        "url": "https://example.com/forest.png",
        "thumbnail_url": "",
        "tags": ["dark", "forest"],
        "system": ["WWN"],
    }
    cog.catalog.random_image = AsyncMock(return_value=entry)
    message = SimpleNamespace(content="find map forest", channel=SimpleNamespace(send=send))

    assert asyncio.run(cog.handle_message(message)) is True
    assert sent
    assert sent[0][1]["embed"].title == "Dark Forest — Image"
    cog.catalog.random_image.assert_awaited_once_with(image_type="map", tags="forest")
