import json

from scripts import bot_watchdog


def test_bot_health_rejects_stale_heartbeat(tmp_path, monkeypatch):
    health_file = tmp_path / "health.json"
    health_file.write_text(json.dumps({"updated_at": 100, "ready": True}), encoding="utf-8")
    monkeypatch.setattr(bot_watchdog, "BOT_HEALTH_FILE", health_file)
    monkeypatch.setattr(bot_watchdog, "BOT_HEALTH_MAX_AGE", 90)

    healthy, details = bot_watchdog.bot_health(now=200)

    assert not healthy
    assert "100s old" in details


def test_bot_health_requires_discord_gateway_ready(tmp_path, monkeypatch):
    health_file = tmp_path / "health.json"
    health_file.write_text(json.dumps({"updated_at": 100, "ready": False}), encoding="utf-8")
    monkeypatch.setattr(bot_watchdog, "BOT_HEALTH_FILE", health_file)

    healthy, details = bot_watchdog.bot_health(now=110)

    assert not healthy
    assert details == "Discord gateway is not ready"
