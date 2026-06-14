import asyncio
from types import SimpleNamespace

from cogs.features import FeaturesCog
from bot import WithoutNumberBot


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


def test_ignore_me_fully_mutes_and_listen_to_me_restores_user():
    db = FakeDatabase()
    cog, message, _sent = make_message(db, "ignore me")

    assert asyncio.run(cog.handle_message(message)) is True
    assert cog.is_user_muted(message.author.id) is True

    message.content = "listen to me"
    assert asyncio.run(cog.handle_message(message)) is True
    assert cog.is_user_muted(message.author.id) is False


def test_muted_user_can_only_use_features_slash_command():
    db = FakeDatabase()
    db.set_setting("user:12", "feature:bot_interactions", "off")
    features = FeaturesCog(SimpleNamespace(db=db))
    bot = object.__new__(WithoutNumberBot)
    bot.get_cog = lambda name: features if name == "FeaturesCog" else None

    async def send_message(_text, **_kwargs):
        return None

    interaction = SimpleNamespace(
        user=SimpleNamespace(id=12),
        data={"name": "roll"},
        response=SimpleNamespace(is_done=lambda: False, send_message=send_message),
    )
    assert asyncio.run(bot._feature_interaction_check(interaction)) is False

    interaction.data = {"name": "features"}
    assert asyncio.run(bot._feature_interaction_check(interaction)) is True
