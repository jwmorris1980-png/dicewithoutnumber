"""Install the repository-local pre-push test-area gate."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".git" / "hooks" / "pre-push"
CONTENT = """#!/bin/sh
echo "Running DICEwithoutNumber local test area before push..."
python scripts/test_area.py
"""


def main() -> None:
    if not HOOK.parent.is_dir():
        raise SystemExit("This repository has no .git/hooks directory.")
    HOOK.write_text(CONTENT, encoding="utf-8", newline="\n")
    HOOK.chmod(0o755)
    print(f"Installed test gate: {HOOK}")


if __name__ == "__main__":
    main()
