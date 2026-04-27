from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil


def create_database_backup(database_path: str | Path, backup_dir: str | Path) -> Path:
    source = Path(database_path)
    destination_dir = Path(backup_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = destination_dir / f"{source.stem}-{timestamp}.db"
    shutil.copy2(source, backup_path)
    return backup_path


def restore_database_backup(database_path: str | Path, backup_path: str | Path) -> Path:
    source_backup = Path(backup_path)
    target_database = Path(database_path)
    target_database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_backup, target_database)
    return target_database
