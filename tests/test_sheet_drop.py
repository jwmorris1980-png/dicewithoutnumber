import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from cogs.sheets import CharacterSheetCog


class FakeDatabase:
    def get_character(self, _user_id, _name):
        return None

    def save_character(self, *_args):
        return None

    def bind_character(self, *_args):
        return None

    def register_server_character(self, *_args):
        return None


def test_dropped_sheet_result_is_sent_to_message_channel():
    sent = []

    async def send(content=None, **_kwargs):
        sent.append(content)

    bot = SimpleNamespace(db=FakeDatabase())
    cog = CharacterSheetCog(bot)
    message = SimpleNamespace(
        author=SimpleNamespace(id=12),
        channel=SimpleNamespace(id=34, category_id=None, send=send),
        guild=SimpleNamespace(id=56),
    )
    character = {"name": "Austin Krow"}

    asyncio.run(cog._save_imported_character(message, character, source_name="dropped character sheet"))

    assert sent
    assert "Imported **Austin Krow**" in sent[0]


def test_copy_text_drop_is_detected_by_the_bot():
    from bot import WithoutNumberBot

    sent = []

    async def send(content=None, **_kwargs):
        sent.append(content)

    bot = object.__new__(WithoutNumberBot)
    cog = CharacterSheetCog(SimpleNamespace(db=FakeDatabase()))
    bot.get_cog = lambda _name: cog
    message = SimpleNamespace(
        content="Zion Kim [SWN] Level 1 Warrior HP: 11/11 SKILLS Punch-1, Notice-0",
        author=SimpleNamespace(id=12),
        channel=SimpleNamespace(id=34, category_id=None, send=send),
        guild=SimpleNamespace(id=56),
        attachments=[],
    )

    handled = asyncio.run(bot._handle_character_sheet_drop(message))

    assert handled is True
    assert any(item and "export detected" in str(item) for item in sent)
    assert any(item and "Zion Kim" in str(item) for item in sent)


def test_sheet_response_omits_missing_optional_view_and_embed():
    sent = []

    async def send(content=None, **kwargs):
        sent.append((content, kwargs))

    target = SimpleNamespace(send=send)
    cog = CharacterSheetCog(SimpleNamespace(db=FakeDatabase()))

    with patch("cogs.sheets.discord.Interaction", type("FakeInteraction", (), {})):
        asyncio.run(cog._send_target(target, "Imported"))

    assert sent == [("Imported", {})]


def test_slash_sheet_response_omits_missing_optional_view_and_embed():
    sent = []

    class FakeResponse:
        def is_done(self):
            return False

        async def send_message(self, content=None, **kwargs):
            sent.append((content, kwargs))

    class FakeInteraction:
        def __init__(self):
            self.response = FakeResponse()
            self.followup = SimpleNamespace()
            self.user = SimpleNamespace()

    cog = CharacterSheetCog(SimpleNamespace(db=FakeDatabase()))
    with patch("cogs.sheets.discord.Interaction", FakeInteraction):
        asyncio.run(cog._send_target(FakeInteraction(), "Imported"))

    assert sent == [("Imported", {"ephemeral": False})]
