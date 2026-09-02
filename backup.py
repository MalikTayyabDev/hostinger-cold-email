#!/usr/bin/env python3
"""Backup campaign.db to backups/ with timestamp."""
import shutil
from datetime import datetime
from pathlib import Path

from config import load_config


def backup():
    cfg = load_config()
    db_path = Path(cfg["DATABASE"])
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = backup_dir / f"campaign_{stamp}.db"
    shutil.copy2(db_path, dest)
    print(f"Backup saved: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(backup())
