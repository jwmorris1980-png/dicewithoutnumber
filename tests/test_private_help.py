import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

from cogs.help import HelpCog, HelpIndexView


def test_text_help_uses_temporary_embed_not_dm():
    sent = []

    async def send(*args, **kwargs):
        sent.append((args, kwargs))

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
    assert sent[0][1]["embed"].title == "DICEwithoutNumber — Help"
    assert isinstance(sent[0][1]["view"], HelpIndexView)
    assert sent[0][1]["delete_after"] == 60
