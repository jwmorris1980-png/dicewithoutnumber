import asyncio
from types import SimpleNamespace

from bot import WithoutNumberBot


def test_unknown_word_is_not_treated_as_a_bare_command_suggestion():
    sent_messages = []
    message = SimpleNamespace(
        content="rol",
        channel=SimpleNamespace(send=lambda text: sent_messages.append(text)),
    )
    bot = object.__new__(WithoutNumberBot)
    bot.get_command = lambda _name: None

    handled = asyncio.run(bot._handle_bare_command(message))

    assert handled is False
    assert sent_messages == []


def test_normal_sentence_is_not_treated_as_a_bare_command_suggestion():
    sent_messages = []
    message = SimpleNamespace(
        content="I'm sorry part",
        channel=SimpleNamespace(send=lambda text: sent_messages.append(text)),
    )
    bot = object.__new__(WithoutNumberBot)
    bot.get_command = lambda _name: None

    handled = asyncio.run(bot._handle_bare_command(message))

    assert handled is False
    assert sent_messages == []
