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
