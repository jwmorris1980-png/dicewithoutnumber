"""
cleanup.py — DICEwithoutNumber Project Cleaner
Removes temporary, diagnostic, and deployment junk from the project root.
ALWAYS shows a preview first and asks for confirmation before deleting anything.
"""

import os
import shutil
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))

# ── Files to delete by exact name ────────────────────────────────────────────
EXACT_FILES = [
    "absolute_zero_fix.py",
    "add_cron.py",
    "analyze_remote_logs.py",
    "bot_new.log",
    "check_len.py",
    "check_logs.py",
    "check_oracle_filesystem.py",
    "check_remote_ip.py",
    "complete_repair.py",
    "deploy_pass.py",
    "deploy_to_oracle_final.py",
    "deploy_to_oracle_zip.py",
    "diag_external.py",
    "diag_full.py",
    "diag_nginx.py",
    "diag_oracle.py",
    "diag_remote.py",
    "diag_remote_v2.py",
    "do_ip.docx",
    "do_ip.txt",
    "download_all_wheels.py",
    "download_linux_wheels.py",
    "droplet.env",
    "droplet_bot.log.docx",
    "droplet_bot_v2.log.docx",
    "droplet_bot_v3.log.docx",
    "droplet_diagnosis.txt",
    "droplet_logs.txt",
    "dump_remote_logs.py",
    "fetch_remote_logs.py",
    "final_bot_fix.py",
    "final_linux_upload.py",
    "final_offline_setup.py",
    "final_recursive_setup.py",
    "final_repair.py",
    "final_smuggle_transfer.py",
    "final_stable_install.py",
    "final_strict_setup.py",
    "final_upload_wheels.py",
    "final_v5_repair.py",
    "fire_fix.py",
    "fix_libraries.py",
    "fix_nginx.py",
    "fix_oracle.py",
    "fix_oracle_all.py",
    "fix_oracle_service.py",
    "get_oracle_logs.py",
    "global_commands_audit.json",
    "guild_commands_audit.json",
    "inspect_tree.py",
    "integrity_check.py",
    "last_final_repair.py",
    "last_hope_install.py",
    "local_wheel_download.py",
    "main.py.bak",
    "migrate_wholesale.py",
    "nuke_rebuild.py",
    "oracle_filesystem.txt",
    "oracle_logs_full.txt",
    "out.docx",
    "rebuild_ipv4.py",
    "remote_status.txt",
    "remote_tracker_full.json",
    "requirements.docx",
    "setup_git_remote.py",
    "strict_linux_download.py",
    "sync_output.txt",
    "sync_output_2.txt",
    "sync_payload.json",
    "test.js",
    "test_map.png",
    "test_pypi.py",
    "true_recursive_download.py",
    "update_dns.py",
    "verify_dns_update.py",
    "verify_fix.py",
    "verify_nginx_fix.py",
    "verify_remote_index_exact.py",
    "verify_remote_web.py",
    # Deploy zips
    "deploy_20260403_215354.zip",
    "deploy_20260403_215410.zip",
    # Smuggle archives (BIG)
    "big_smuggle.tar.gz",
    "smuggle.zip",
    "venv_smuggle.tar.gz",
    "site_packages.zip",
    "system_libs.zip",
    "wholesale_migration.tar.gz",
    "wholesale_smuggle.tar.gz",
]

# ── Files matching patterns ───────────────────────────────────────────────────
PATTERNS = [
    "tmp_*.py",
]

# ── Folders to delete entirely ────────────────────────────────────────────────
FOLDERS = [
    "wheels",
    "wheels_final",
    "wheels_linux",
    "wheels_recursive",
    "wheels_strict",
    "wheels_true",
]

# ── Files/folders to NEVER touch ─────────────────────────────────────────────
KEEP = {
    "bot.py", "game_data.py", "dice_service.py", "ai_service.py",
    "requirements.txt", "settings.json", ".env", ".env_actual",
    ".gitignore", ".cursorrules", "dicewithoutnumber.service",
    "cleanup.py",  # keep this script itself
    "commands.md", "SERVER_GUIDE.md",
}


def collect_targets():
    targets = []

    # Exact files
    for name in EXACT_FILES:
        path = os.path.join(ROOT, name)
        if os.path.isfile(path) and name not in KEEP:
            targets.append(("file", path))

    # Pattern files
    for pattern in PATTERNS:
        for path in glob.glob(os.path.join(ROOT, pattern)):
            name = os.path.basename(path)
            if name not in KEEP:
                targets.append(("file", path))

    # Folders
    for name in FOLDERS:
        path = os.path.join(ROOT, name)
        if os.path.isdir(path):
            targets.append(("dir", path))

    # Deduplicate
    seen = set()
    unique = []
    for kind, path in targets:
        if path not in seen:
            seen.add(path)
            unique.append((kind, path))

    return unique


def human_size(path, kind):
    try:
        if kind == "file":
            return f"{os.path.getsize(path) / 1024 / 1024:.2f} MB"
        else:
            total = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, files in os.walk(path)
                for f in files
            )
            return f"{total / 1024 / 1024:.2f} MB"
    except Exception:
        return "? MB"


def main():
    targets = collect_targets()

    if not targets:
        print("✅ Nothing to clean up — project is already tidy!")
        return

    print(f"\n{'='*60}")
    print("  🧹  DICEwithoutNumber — Cleanup Preview")
    print(f"{'='*60}\n")
    print(f"  Found {len(targets)} items to remove:\n")

    total_mb = 0.0
    for kind, path in targets:
        label = "[DIR] " if kind == "dir" else "      "
        size_str = human_size(path, kind)
        try:
            size_mb = float(size_str.replace(" MB", ""))
            total_mb += size_mb
        except Exception:
            pass
        rel = os.path.relpath(path, ROOT)
        print(f"  {label}{rel:<55} {size_str:>10}")

    print(f"\n{'─'*60}")
    print(f"  Total space to recover: ~{total_mb:.1f} MB")
    print(f"{'─'*60}\n")

    confirm = input("  ⚠️  Type YES to delete all of the above, or anything else to cancel: ").strip()
    if confirm != "YES":
        print("\n  ❌ Cancelled. Nothing was deleted.\n")
        return

    print()
    errors = []
    for kind, path in targets:
        try:
            if kind == "file":
                os.remove(path)
            else:
                shutil.rmtree(path)
            print(f"  🗑️  Deleted: {os.path.relpath(path, ROOT)}")
        except Exception as e:
            errors.append((path, str(e)))
            print(f"  ⚠️  Failed:  {os.path.relpath(path, ROOT)} — {e}")

    print(f"\n{'='*60}")
    if errors:
        print(f"  ✅ Done with {len(errors)} error(s). See above for details.")
    else:
        print(f"  ✅ All clean! Recovered ~{total_mb:.1f} MB.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
