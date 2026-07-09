import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from cogs.campaign import CampaignCog


def test_campaign_character_uses_sheet_cog_resolution():
    character = {"name": "Pavel Petrovich", "hp": 6}
    sheet_cog = SimpleNamespace(get_active_character_data=AsyncMock(return_value=character))
    bot = SimpleNamespace(db=MagicMock(), get_cog=MagicMock(return_value=sheet_cog))
    cog = CampaignCog(bot)
    interaction = SimpleNamespace(user=SimpleNamespace(id=123), channel=SimpleNamespace(id=456, category_id=789))

    result = asyncio.run(cog._get_campaign_character(interaction))

    assert result == character
    sheet_cog.get_active_character_data.assert_awaited_once_with(interaction, allow_none=True)
    bot.db.get_active_character.assert_not_called()


def test_campaign_character_falls_back_to_scoped_database_lookup():
    character = {"name": "Pavel Petrovich", "hp": 6}
    db = MagicMock()
    db.get_active_character.return_value = character
    bot = SimpleNamespace(db=db, get_cog=MagicMock(return_value=None))
    cog = CampaignCog(bot)
    ctx = SimpleNamespace(author=SimpleNamespace(id=123), channel=SimpleNamespace(id=456, category_id=789))

    result = asyncio.run(cog._get_campaign_character(ctx))

    assert result == character
    db.get_active_character.assert_called_once_with(123, "456", "789")
