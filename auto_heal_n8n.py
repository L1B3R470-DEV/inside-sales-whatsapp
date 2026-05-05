import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

DB_PATH = os.getenv('AUTO_HEAL_DB_PATH', os.getenv('N8N_DB_PATH', '/data/database.sqlite'))
MAX_RUNNING_MS = int(
    os.getenv(
        'AUTO_HEAL_MAX_RUNNING_MS',
        str(int(os.getenv('N8N_AUTO_HEAL_MAX_RUNNING_SECONDS', '120')) * 1000),
    )
)
SLEEP_SECONDS = int(os.getenv('AUTO_HEAL_INTERVAL_SECONDS', os.getenv('N8N_AUTO_HEAL_LOOP_SECONDS', '60')))
WHITELIST = {
    item.strip()
    for item in os.getenv(
        'AUTO_HEAL_WORKFLOW_WHITELIST',
        os.getenv('N8N_AUTO_HEAL_EXCLUDED_WORKFLOW_IDS', ''),
    ).split(',')
    if item.strip()
}

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')


def ensure_audit_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS execution_auto_heal_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            executionId INTEGER NOT NULL,
            workflowId TEXT,
            startedAt TEXT,
            healedAt TEXT NOT NULL,
            maxRunningMs INTEGER NOT NULL,
            reason TEXT NOT NULL
        )
        '''
    )
    conn.commit()


def parse_sqlite_datetime(raw_value: str) -> datetime | None:
    raw_value = str(raw_value or '').strip()
    if not raw_value:
        return None

    for candidate in (raw_value.replace(' ', 'T'), raw_value):
        try:
            parsed = datetime.fromisoformat(candidate.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue

    return None


def heal_once() -> dict:
    conn = sqlite3.connect(DB_PATH, timeout=300)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout = 300000')

    rows = conn.execute(
        '''
        SELECT id, workflowId, status, startedAt, createdAt
        FROM execution_entity
        WHERE status IN ('running', 'new', 'crashed')
        ORDER BY COALESCE(startedAt, createdAt) ASC
        '''
    ).fetchall()
    if not rows:
        conn.close()
        return {
            'action': 'auto_heal',
            'scanned': 0,
            'healed': 0,
            'healedExecutions': [],
            'maxRunningMs': MAX_RUNNING_MS,
            'whitelistSize': len(WHITELIST),
        }

    healed = []
    now_ms = int(time.time() * 1000)
    healed_at = utc_now()
    audit_ready = False

    for row in rows:
        workflow_id = str(row['workflowId'] or '').strip()
        if workflow_id in WHITELIST:
            continue

        original_status = str(row['status'] or '').strip()
        started_raw = str(row['startedAt'] or row['createdAt'] or '').strip()
        started_dt = parse_sqlite_datetime(started_raw)
        if started_dt is None:
            continue

        age_ms = now_ms - int(started_dt.timestamp() * 1000)
        if age_ms <= MAX_RUNNING_MS:
            continue

        if not audit_ready:
            ensure_audit_table(conn)
            audit_ready = True

        update_cursor = conn.execute(
            '''
            UPDATE execution_entity
            SET status = 'failed',
                stoppedAt = ?,
                finished = 1,
                waitTill = NULL
            WHERE id = ? AND status = ?
            ''',
            (healed_at, row['id'], original_status),
        )
        if update_cursor.rowcount == 0:
            continue

        conn.execute(
            '''
            INSERT INTO execution_auto_heal_audit
                (executionId, workflowId, startedAt, healedAt, maxRunningMs, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                row['id'],
                workflow_id,
                started_raw,
                healed_at,
                MAX_RUNNING_MS,
                f'status_timeout:{original_status}',
            ),
        )
        healed.append(
            {
                'executionId': row['id'],
                'workflowId': workflow_id,
                'status': original_status,
                'ageMs': age_ms,
            }
        )

    if healed:
        conn.commit()
    conn.close()

    return {
        'action': 'auto_heal',
        'scanned': len(rows),
        'healed': len(healed),
        'healedExecutions': healed,
        'maxRunningMs': MAX_RUNNING_MS,
        'whitelistSize': len(WHITELIST),
    }


def main() -> None:
    if '--once' in sys.argv:
        print(json.dumps(heal_once(), ensure_ascii=False), flush=True)
        return
    while True:
        print(json.dumps(heal_once(), ensure_ascii=False), flush=True)
        time.sleep(SLEEP_SECONDS)


if __name__ == '__main__':
    main()
