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


def heal_once() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_audit_table(conn)

    rows = conn.execute(
        '''
        SELECT id, workflowId, startedAt
        FROM execution_entity
        WHERE status = 'running'
        ORDER BY startedAt ASC
        '''
    ).fetchall()

    healed = []
    now_ms = int(time.time() * 1000)
    healed_at = utc_now()

    for row in rows:
        workflow_id = str(row['workflowId'] or '').strip()
        if workflow_id in WHITELIST:
            continue

        started_raw = str(row['startedAt'] or '').strip()
        if not started_raw:
            continue

        started_dt = None
        for candidate in (started_raw.replace(' ', 'T'), started_raw):
            try:
                started_dt = datetime.fromisoformat(candidate.replace('Z', '+00:00'))
                break
            except ValueError:
                continue
        if started_dt is None:
            continue
        if started_dt.tzinfo is None:
            started_dt = started_dt.replace(tzinfo=timezone.utc)

        age_ms = now_ms - int(started_dt.timestamp() * 1000)
        if age_ms <= MAX_RUNNING_MS:
            continue

        conn.execute(
            '''
            UPDATE execution_entity
            SET status = 'failed',
                stoppedAt = ?,
                finished = 1,
                waitTill = NULL
            WHERE id = ? AND status = 'running'
            ''',
            (healed_at, row['id']),
        )
        conn.execute(
            '''
            INSERT INTO execution_auto_heal_audit
                (executionId, workflowId, startedAt, healedAt, maxRunningMs, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (row['id'], workflow_id, started_raw, healed_at, MAX_RUNNING_MS, 'running_timeout'),
        )
        healed.append({'executionId': row['id'], 'workflowId': workflow_id, 'ageMs': age_ms})

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
