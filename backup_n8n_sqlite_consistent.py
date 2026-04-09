import json
import os
import sqlite3
import shutil
from datetime import datetime, timezone
from pathlib import Path

SOURCE_DB = Path(os.getenv('BACKUP_SOURCE_DB', '/data/database.sqlite'))
BACKUP_DIR = Path(os.getenv('BACKUP_TARGET_DIR', '/backup'))


def run_backup() -> dict:
    if not SOURCE_DB.exists():
        raise FileNotFoundError(f'database not found: {SOURCE_DB}')

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    target_dir = BACKUP_DIR / timestamp
    target_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for candidate in (SOURCE_DB, SOURCE_DB.with_name(SOURCE_DB.name + '-wal'), SOURCE_DB.with_name(SOURCE_DB.name + '-shm')):
        if candidate.exists():
            dst = target_dir / candidate.name
            shutil.copy2(candidate, dst)
            copied.append(dst.name)

    target = target_dir / SOURCE_DB.name
    check = sqlite3.connect(str(target))
    integrity = check.execute('PRAGMA quick_check;').fetchone()[0]
    execution_rows = check.execute('SELECT COUNT(*) FROM execution_entity').fetchone()[0]
    check.close()
    if integrity != 'ok':
        raise RuntimeError(f'integrity_check_failed: {integrity}')

    return {
        'ok': True,
        'directory': str(target_dir),
        'files': copied,
        'sizeBytes': sum((target_dir / name).stat().st_size for name in copied),
        'integrity': integrity,
        'executionRows': int(execution_rows),
    }


if __name__ == '__main__':
    print(json.dumps(run_backup(), ensure_ascii=False), flush=True)
