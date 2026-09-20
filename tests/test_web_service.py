from unittest.mock import MagicMock

import pytest

from services.web_service import WebService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_server_starts_and_stops():
    # Mock bot and db
    bot = MagicMock()
    bot.db.get_tracker.return_value = {
        "combatants": [
            {"id": 1, "name": "Hero", "x": 2, "y": 3, "is_enemy": False},
            {"id": 2, "name": "Goblin", "x": 5, "y": 5, "is_enemy": True},
        ]
    }

    service = WebService(bot, port=0)
    await service.start()

    assert service.runner is not None

    await service.stop()


def test_characters_route_is_wired():
    service = WebService(MagicMock(), port=0)
    paths = [route.resource.canonical for route in service.app.router.routes()]
    assert "/characters" in paths


def test_character_hub_covers_live_builder_and_paste_preview():
    from pathlib import Path

    page = Path(__file__).resolve().parents[1] / "web" / "characters.html"
    text = page.read_text(encoding="utf-8")
    for path in (
        "swn-character-builder/",
        "cwn-character-builder/",
        "wwn-character-builder/",
        "awn-character-builder/",
        "build/?random=swn",
    ):
        assert path in text
    assert 'id="paste-box"' in text
    assert "Preview pasted sheet" in text
