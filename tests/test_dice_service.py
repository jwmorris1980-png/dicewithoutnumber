import asyncio
from unittest.mock import AsyncMock, MagicMock

from services.dice_service import DiceService
from cogs.dice import DiceCog


def test_fuzzy_two_digit_roll_does_not_raise():
    total, details, err, repeats, end_idx = DiceService().parse_and_roll("26")

    assert err is None
    assert 2 <= total <= 12
    assert details
    assert repeats == 1
    assert end_idx == 3


def test_keep_highest_is_deterministic_with_patched_rolls(monkeypatch):
    rolls = iter([1, 4, 6, 2])
    monkeypatch.setattr("services.dice_service.random.randint", lambda _low, _high: next(rolls))

    total, details, err, repeats, end_idx = DiceService().parse_and_roll("4d6kh3")

    assert total == 12
    assert details == "(~~1~~, 4, 6, 2)"
    assert err is None
    assert repeats == 1
    assert end_idx == 6


def test_specialist_3d6kh_defaults_to_keep_two(monkeypatch):
    rolls = iter([2, 5, 3])
    monkeypatch.setattr("services.dice_service.random.randint", lambda _low, _high: next(rolls))

    total, details, err, repeats, end_idx = DiceService().parse_and_roll("3d6kh")

    assert total == 8
    assert details == "(~~2~~, 5, 3)"
    assert err is None
    assert repeats == 1
    assert end_idx == 5


def test_repetition_prefix_is_reported_separately(monkeypatch):
    monkeypatch.setattr("services.dice_service.random.randint", lambda _low, _high: 10)

    total, details, err, repeats, end_idx = DiceService().parse_and_roll("3x 1d20+5")

    assert total == 15
    assert details == "(10) +5"
    assert err is None
    assert repeats == 3
    assert end_idx == 6


def test_roll_prefix_handles_fuzzy_roll_without_raising(monkeypatch):
    monkeypatch.setattr("services.dice_service.random.randint", lambda _low, _high: 4)

    bot = MagicMock()
    bot.dice_service = DiceService()
    bot.get_cog.return_value = None

    ctx = MagicMock()
    ctx.author.mention = "@devinb"
    ctx.send = AsyncMock()

    cog = DiceCog(bot)
    asyncio.run(DiceCog.roll_prefix.callback(cog, ctx, expression="26"))

    ctx.send.assert_awaited_once()
    sent_message = ctx.send.await_args.args[0]
    assert "@devinb" in sent_message
    assert "**26**" in sent_message
    assert "**8**" in sent_message
