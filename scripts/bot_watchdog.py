"""Independent health monitor for the Discord bot systemd service."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


SERVICE = os.getenv("WATCHDOG_SERVICE", "dicewithoutnumber.service")
STATE_FILE = Path(os.getenv("WATCHDOG_STATE_FILE", "/var/lib/dicewithoutnumber-watchdog/state.json"))
PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_FILES = (
    Path.home() / ".dicewithoutnumber" / ".env",
    Path.home() / ".dicewithoutnumber" / ".env_actual",
    Path("/home/ubuntu/.dicewithoutnumber/.env"),
    Path("/home/ubuntu/.dicewithoutnumber/.env_actual"),
    PROJECT_DIR / ".env",
    PROJECT_DIR / ".env_actual",
)


def load_env() -> None:
    for path in ENV_FILES:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def systemctl(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["systemctl", *args],
        check=check,
        capture_output=True,
        text=True,
        timeout=30,
    )


def service_status() -> tuple[bool, int]:
    active = systemctl("is-active", "--quiet", SERVICE).returncode == 0
    result = systemctl("show", SERVICE, "--property=NRestarts", "--value")
    try:
        restarts = int(result.stdout.strip())
    except ValueError:
        restarts = 0
    return active, restarts


def api_request(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "DICEwithoutNumber-Watchdog/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def owner_id(token: str) -> str:
    configured = os.getenv("DISCORD_OWNER_ID", "").strip()
    if configured.isdigit():
        return configured
    application = api_request("GET", "/oauth2/applications/@me", token)
    return str((application.get("owner") or {}).get("id") or "")


def notify(message: str) -> None:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        print("Watchdog alert not sent: DISCORD_TOKEN is unavailable.")
        return

    errors: list[str] = []
    try:
        recipient = owner_id(token)
        if recipient:
            dm = api_request("POST", "/users/@me/channels", token, {"recipient_id": recipient})
            api_request("POST", f"/channels/{dm['id']}/messages", token, {"content": message[:2000]})
            return
    except (KeyError, OSError, urllib.error.HTTPError) as exc:
        errors.append(f"owner DM failed: {exc}")

    channel_id = os.getenv("LOG_CHANNEL_ID", "").strip()
    if channel_id.isdigit():
        try:
            api_request("POST", f"/channels/{channel_id}/messages", token, {"content": message[:2000]})
            return
        except (OSError, urllib.error.HTTPError) as exc:
            errors.append(f"log channel failed: {exc}")

    print("Watchdog alert not sent: " + "; ".join(errors or ["no owner or log channel available"]))


def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def restart_and_verify() -> tuple[bool, int, str]:
    restart = systemctl("restart", SERVICE)
    details = (restart.stderr or restart.stdout or "No systemd error details.").strip()[-800:]
    time.sleep(12)
    first_active, first_restarts = service_status()
    if not first_active:
        return False, first_restarts, details

    # A crash-looping process can briefly appear active, so verify it remains stable.
    time.sleep(12)
    stable_active, stable_restarts = service_status()
    return stable_active and stable_restarts == first_restarts, stable_restarts, details


def main() -> int:
    load_env()
    state = read_state()
    active, restarts = service_status()
    previous_restarts = int(state.get("restarts", restarts))

    if active:
        if restarts > previous_restarts:
            restart_delta = restarts - previous_restarts
            if restart_delta > 1:
                notify(
                    "DICEwithoutNumber is repeatedly crashing. The Oracle watchdog is attempting "
                    "a controlled restart now."
                )
                recovered, restarts, details = restart_and_verify()
                if recovered:
                    notify("DICEwithoutNumber stabilized after automatic recovery and is back online.")
                else:
                    notify(
                        "DICEwithoutNumber could not stabilize automatically. Immediate manual repair "
                        f"is needed.\nSystemd: `{details}`"
                    )
                write_state({"restarts": restarts, "active": recovered, "checked_at": int(time.time())})
                return 0 if recovered else 1
            notify(
                "DICEwithoutNumber restarted after a crash and recovered automatically. "
                f"New automatic restarts: {restart_delta}."
            )
        write_state({"restarts": restarts, "active": True, "checked_at": int(time.time())})
        return 0

    notify("DICEwithoutNumber is down. The Oracle watchdog is attempting an automatic restart now.")
    recovered, new_restarts, details = restart_and_verify()

    if recovered:
        notify("DICEwithoutNumber recovered automatically and is back online.")
    else:
        notify(
            "DICEwithoutNumber could not recover automatically. Immediate manual repair is needed.\n"
            f"Systemd: `{details}`"
        )

    write_state({"restarts": new_restarts, "active": recovered, "checked_at": int(time.time())})
    return 0 if recovered else 1


if __name__ == "__main__":
    raise SystemExit(main())
