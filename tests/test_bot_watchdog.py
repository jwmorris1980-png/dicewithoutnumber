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


def test_update_marker_has_limited_grace_period(tmp_path, monkeypatch):
    marker = tmp_path / "update.json"
    monkeypatch.setattr(bot_watchdog, "UPDATE_MARKER_FILE", marker)
    monkeypatch.setattr(bot_watchdog, "UPDATE_GRACE_SECONDS", 180)

    bot_watchdog.mark_update(now=100)

    assert bot_watchdog.update_in_progress(now=280)
    assert not bot_watchdog.update_in_progress(now=281)


def test_watchdog_does_not_repair_during_planned_update(tmp_path, monkeypatch):
    marker = tmp_path / "update.json"
    state = tmp_path / "state.json"
    monkeypatch.setattr(bot_watchdog, "UPDATE_MARKER_FILE", marker)
    monkeypatch.setattr(bot_watchdog, "STATE_FILE", state)
    monkeypatch.setattr(bot_watchdog, "load_env", lambda: None)
    monkeypatch.setattr(bot_watchdog, "service_status", lambda: (True, 0))
    monkeypatch.setattr(bot_watchdog, "bot_health", lambda: (False, "starting"))
    monkeypatch.setattr(bot_watchdog, "restart_and_verify", lambda: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(bot_watchdog, "notify", lambda message: (_ for _ in ()).throw(AssertionError()))
    marker.write_text(json.dumps({"started_at": 100}), encoding="utf-8")
    monkeypatch.setattr(bot_watchdog.time, "time", lambda: 110)

    assert bot_watchdog.main() == 0
