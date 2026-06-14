import asyncio
from types import SimpleNamespace

from cogs.asset_library import AssetLibraryCog


def test_asset_library_finds_maps_and_voice_phrase():
    sent = []

    async def send(*args, **kwargs):
        sent.append((args, kwargs))

    cog = AssetLibraryCog(SimpleNamespace())
    assert cog._find("map", "dark forest") == "forest"
    message = SimpleNamespace(content="find map forest", channel=SimpleNamespace(send=send))

    assert asyncio.run(cog.handle_message(message)) is True
    assert sent
    assert sent[0][1]["file"].filename == "map_forest.png"
