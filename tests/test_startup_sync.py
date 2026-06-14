from pathlib import Path


def test_production_startup_does_not_bulk_sync_global_commands():
    source = Path("bot.py").read_text(encoding="utf-8")

    assert "await self.tree.sync()" not in source
    assert "use sync_global_safe.py" in source
