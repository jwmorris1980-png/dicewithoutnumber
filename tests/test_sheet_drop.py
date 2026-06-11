import asyncio
from types import SimpleNamespace

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
