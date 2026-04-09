from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import sqlite3
import sys
import time

SOURCE_DB = Path(os.getenv('N8N_DB_PATH', '/data/database.sqlite'))
BACKUP_DIR = Path(os.getenv('N8N_BACKUP_DIR', '/backup'))
RETENTION_MINUTES = int(os.getenv('N8N_BACKUP_RETENTION_MINUTES', str(24 * 60)))
LOOP_SECONDS = int(os.getenv('N8N_BACKUP_LOOP_SECONDS', '300'))
LOG_PATH = Path(os.getenv('N8N_BACKUP_LOG_PATH', '/backup/n8n-backup.log'))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def append_log(payload: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + '\n')


def prune_old(now_epoch: float) -> None:
    for path in BACKUP_DIR.glob('database_*.sqlite'):
        age_minutes = (now_epoch - path.stat().st_mtime) / 60.0
        if age_minutes > RETENTION_MINUTES:
            path.unlink(missing_ok=True)


def backup_once() -> dict:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCE_DB.exists():
        payload = {
            'action': 'sqlite_backup',
            'status': 'skip_missing_source',
            'source': str(SOURCE_DB),
            'timestamp': utc_now().isoformat(),
        }
        append_log(payload)
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return payload

    timestamp = utc_now().strftime('%Y%m%d_%H%M%S')
    target = BACKUP_DIR / f'database_{timestamp}.sqlite'
    temp_target = target.with_suffix('.sqlite.tmp')

    src = sqlite3.connect(str(SOURCE_DB), timeout=300)
    src.row_factory = sqlite3.Row
    src.execute('PRAGMA busy_timeout = 300000')
    src.execute('PRAGMA synchronous = NORMAL')
    checkpoint = None

    dst = sqlite3.connect(str(temp_target), timeout=300)
    dst.execute('PRAGMA journal_mode = DELETE')
    src.backup(dst, pages=2000, sleep=0.05)
    dst.commit()
    dst.close()
    src.close()

    verify = sqlite3.connect(str(temp_target), timeout=60)
    integrity = str(verify.execute('PRAGMA integrity_check').fetchone()[0] or '').strip().lower()
    verify.close()

    if integrity != 'ok':
        temp_target.unlink(missing_ok=True)
        raise RuntimeError(f'integrity_check_failed:{integrity}')

    shutil.move(str(temp_target), str(target))
    prune_old(time.time())

    payload = {
        'action': 'sqlite_backup',
        'status': 'ok',
        'file': target.name,
        'sizeBytes': target.stat().st_size,
        'walCheckpoint': list(checkpoint) if checkpoint is not None else [],
        'integrity': integrity,
        'timestamp': utc_now().isoformat(),
    }
    append_log(payload)
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return payload


def main() -> None:
    once = '--once' in sys.argv
    if once:
        backup_once()
        return
    while True:
        try:
            backup_once()
        except Exception as exc:
            payload = {
                'action': 'sqlite_backup',
                'status': 'error',
                'error': str(exc),
                'timestamp': utc_now().isoformat(),
            }
            append_log(payload)
            print(json.dumps(payload, ensure_ascii=False), flush=True)
        time.sleep(LOOP_SECONDS)


if __name__ == '__main__':
    main()
