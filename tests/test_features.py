import asyncio
from types import SimpleNamespace

from cogs.features import FeaturesCog


class FakeDatabase:
    def __init__(self):
        self.settings = {}

    def get_setting(self, target_id, key, default=None):
        return self.settings.get((str(target_id), key), default)

    def set_setting(self, target_id, key, value):
        self.settings[(str(target_id), key)] = str(value)

    def delete_setting(self, target_id, key):
        self.settings.pop((str(target_id), key), None)


def make_message(db, content=""):
    sent = []

    async def send(text):
        sent.append(text)

    message = SimpleNamespace(
        content=content,
        author=SimpleNamespace(id=12),
        guild=SimpleNamespace(id=34),
        channel=SimpleNamespace(send=send),
    )
    return FeaturesCog(SimpleNamespace(db=db)), message, sent


def test_conversational_feature_switch_disables_voice_for_user():
    db = FakeDatabase()
    cog, message, sent = make_message(db, "I don't want voice commands")

    assert asyncio.run(cog.handle_message(message)) is True
    assert cog.is_enabled("voice", message) is False
    assert sent and "set to **off**" in sent[0]


def test_user_setting_overrides_server_feature_default():
    db = FakeDatabase()
    cog, message, _sent = make_message(db)
    db.set_setting("guild:34", "feature:automatic_sheet_imports", "off")

    assert cog.is_enabled("sheets", message) is False
    db.set_setting("user:12", "feature:automatic_sheet_imports", "on")
    assert cog.is_enabled("sheets", message) is True


def test_default_removes_personal_override():
    db = FakeDatabase()
    cog, message, _sent = make_message(db)
    db.set_setting("guild:34", "feature:voice_commands", "off")
    db.set_setting("user:12", "feature:voice_commands", "on")

    asyncio.run(cog._configure(message, "default", "voice", "me"))

    assert cog.is_enabled("voice", message) is False
