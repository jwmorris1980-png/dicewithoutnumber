import json
from pathlib import Path

from cogs.accessibility import AccessibilityCog, QuickMenuView
from cogs.help import CATEGORIES, _category_embed, _index_embed
from cogs.voice_access import VoiceAccessCog


SYNC_NEEDLES = (
    "build",
    "export",
    "json",
    "copy text",
    "drop",
    "sheet",
    "skill",
    "attack",
    "ship",
    "characterswithoutnumber.app",
)


def _sheets_blob():
    cat = CATEGORIES["sheets"]
    parts = [cat.get("description") or "", cat.get("hint") or ""]
    parts.extend(f"{name} {value}" for name, value in cat["fields"])
    return "\n".join(parts)


def test_sheets_help_explains_build_drop_play():
    blob = _sheets_blob().lower()
    for needle in SYNC_NEEDLES:
        assert needle in blob, needle
    assert "**1." in _sheets_blob()
    assert "**2." in _sheets_blob()
    assert "**3." in _sheets_blob()
    assert "**4." in _sheets_blob()
    assert "share-page" in blob
    assert "no command" in blob


def test_help_index_mentions_the_sync_path():
    embed = _index_embed()
    description = embed.description.lower()
    for needle in ("characterswithoutnumber.app", "json", "copy text", "drop", "sheet", "ship"):
        assert needle in description, needle
    hints = " ".join(field.value for field in embed.fields).lower()
    assert "drop json" in hints
    assert "`sheet`" in hints


def test_help_embed_fields_fit_discord_limits():
    for key in CATEGORIES:
        embed = _category_embed(key)
        if embed.description:
            assert len(embed.description) <= 4096
        for field in embed.fields:
            assert len(field.name) <= 256, field.name
            assert 0 < len(field.value) <= 1024, field.name
    index = _index_embed()
    assert len(index.description) <= 4096
    for field in index.fields:
        assert len(field.name) <= 256
        assert 0 < len(field.value) <= 1024


def test_english_intro_and_locale_help_cover_the_drop_path():
    locales = json.loads((Path(__file__).resolve().parents[1] / "locales" / "en.json").read_text(encoding="utf-8"))
    for system in ("swn", "wwn", "cwn"):
        intro = locales["intro"][system]
        blob = " ".join(intro.values()).lower()
        for needle in ("characterswithoutnumber.app", "export", "json", "copy text", "drop"):
            assert needle in blob, (system, needle)
        assert "sheet" in locales["intro"][system]["step3_desc"].lower()
    help_copy = locales["help"]
    blob = f"{help_copy['description']} {help_copy['char_imports_body']}".lower()
    for needle in SYNC_NEEDLES:
        assert needle in blob, needle
    assert "sheets & characters" in locales["intro"]["footer"].lower()


def test_tutorial_and_menu_explain_the_sync_path():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import asyncio

    sent = []

    async def send(message, **kwargs):
        sent.append(message)

    cog = AccessibilityCog(SimpleNamespace())
    ctx = SimpleNamespace(send=send)
    asyncio.run(cog._tutorial(ctx))
    tutorial = sent[0].lower()
    for needle in ("characterswithoutnumber.app", "json", "copy text", "drop", "sheet", "ship", "sheets & characters"):
        assert needle in tutorial, needle

    view = QuickMenuView()
    interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))
    asyncio.run(view.characters.callback(interaction))
    tip = interaction.response.send_message.await_args.args[0].lower()
    for needle in ("build", "export", "json", "drop", "sheet", "ship", "sheets & characters"):
        assert needle in tip, needle


def test_voice_help_mentions_drop_and_play():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import asyncio

    cog = VoiceAccessCog(SimpleNamespace())
    interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))
    asyncio.run(cog._send_voice_help(interaction))
    text = interaction.response.send_message.await_args.args[0].lower()
    assert "json" in text
    assert "copy text" in text
    assert "sheet" in text
    assert "ship" in text
