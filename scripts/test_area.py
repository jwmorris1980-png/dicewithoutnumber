"""Run the isolated local test area before any production deployment."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], env: dict[str, str]) -> None:
    print(f"[test-area] {' '.join(command)}")
    subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=True)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="dicewithoutnumber-test-area-") as temp_dir:
        env = os.environ.copy()
        env.update(
            {
                "DICEWITHOUTNUMBER_TESTING": "1",
                "DICEWITHOUTNUMBER_TEST_DIR": temp_dir,
                "DICEWITHOUTNUMBER_TEST_DB": str(Path(temp_dir) / "bot_database.db"),
                "DISCORD_TOKEN": "",
                "TEST_GUILD_ID": "",
            }
        )

        try:
            run(
                [
                    sys.executable,
                    "-m",
                    "compileall",
                    "-q",
                    "bot.py",
                    "cogs",
                    "services",
                    "scripts",
                ],
                env,
            )
            run([sys.executable, "-m", "pytest", "-q"], env)
        except subprocess.CalledProcessError as exc:
            print(f"[test-area] FAILED. Production deployment blocked (exit {exc.returncode}).")
            return exc.returncode or 1

    print("[test-area] PASSED. Changes are eligible for production deployment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
