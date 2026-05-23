from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SECRETS_DIR = Path.home() / ".dicewithoutnumber"


def get_secrets_dir() -> Path:
    override = os.getenv("DICEWITHOUTNUMBER_SECRETS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_SECRETS_DIR


def get_secret_path(filename: str, env_var: str | None = None) -> Path:
    if env_var is None:
        base = Path(filename).stem.upper().replace("-", "_")
        env_var = f"DICEWITHOUTNUMBER_{base}_PATH"

    override = os.getenv(env_var, "").strip()
    if override:
        return Path(override).expanduser()

    return get_secrets_dir() / filename


def load_project_env() -> None:
    candidates = []

    env_override = os.getenv("DICEWITHOUTNUMBER_ENV_FILE", "").strip()
    if env_override:
        candidates.append(Path(env_override).expanduser())

    secrets_dir = get_secrets_dir()
    candidates.extend(
        [
            secrets_dir / ".env",
            secrets_dir / ".env_actual",
            PROJECT_ROOT / ".env",
            PROJECT_ROOT / ".env_actual",
        ]
    )

    seen = set()
    for path in candidates:
        if path.is_file() and path not in seen:
            load_dotenv(path, override=False)
            seen.add(path)
