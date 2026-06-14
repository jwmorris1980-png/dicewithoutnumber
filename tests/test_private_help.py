import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cogs.help import HelpCog, HelpIndexView


def test_text_help_uses_temporary_embed_not_dm():
    sent = []

    async def send(*args, **kwargs):
        sent.append((args, kwargs))
        return SimpleNamespace(delete=AsyncMock())

    ctx = SimpleNamespace(
        author=SimpleNamespace(id=123, send=AsyncMock()),
        guild=SimpleNamespace(id=1437247431560400928),
        message=SimpleNamespace(delete=AsyncMock()),
        send=send,
    )
    cog = HelpCog(SimpleNamespace())

    with patch.dict("os.environ", {"TEST_GUILD_ID": "1437247431560400928"}):
        asyncio.run(cog._send_help(ctx))

    ctx.author.send.assert_not_awaited()
    ctx.message.delete.assert_awaited_once()
    assert not sent[0][0]
    assert sent[0][1]["embed"].title.startswith("DICEwithoutNumber")
    assert isinstance(sent[0][1]["view"], HelpIndexView)
    assert "delete_after" not in sent[0][1]
    assert sent[0][1]["view"].session.idle_seconds == 60
    sent[0][1]["view"].session._task.cancel()


def test_clicking_help_category_resets_idle_timer():
    async def run():
        session = SimpleNamespace(touch=__import__("unittest").mock.Mock())
        view = HelpIndexView(session=session)
        interaction = SimpleNamespace(response=SimpleNamespace(edit_message=AsyncMock()))

        await view.children[0].callback(interaction)

        session.touch.assert_called_once()

    asyncio.run(run())
