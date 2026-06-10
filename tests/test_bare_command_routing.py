import asyncio
from types import SimpleNamespace

from bot import WithoutNumberBot
from discord.ext import commands


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


def test_single_word_group_and_incomplete_command_are_ignored():
    async def callback(_ctx, expression):
        return expression

    async def group_callback(_ctx):
        return None

    roll = commands.Command(callback, name="roll")
    party = commands.Group(group_callback, name="party")
    registered = {"roll": roll, "party": party}
    bot = object.__new__(WithoutNumberBot)
    bot.get_command = registered.get

    for content in ("Roll", "Party"):
        message = SimpleNamespace(content=content)
        handled = asyncio.run(bot._handle_bare_command(message))
        assert handled is False


def test_complete_and_no_argument_bare_commands_still_dispatch():
    processed = []

    async def callback(_ctx, expression=None):
        return expression

    roll = commands.Command(callback, name="roll")
    help_command = commands.Command(callback, name="help")
    registered = {"roll": roll, "help": help_command}
    bot = object.__new__(WithoutNumberBot)
    bot.get_command = registered.get

    async def process_commands(message):
        processed.append(message.content)

    bot.process_commands = process_commands
    for content in ("roll 1d20", "help"):
        message = SimpleNamespace(content=content, author="tester")
        handled = asyncio.run(bot._handle_bare_command(message))
        assert handled is True

    assert processed == ["!roll 1d20", "!help"]
