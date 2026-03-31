"""Migrate hard-coded blocked numbers from guardrails.js config to SQLite."""
import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('ROUTER_DB_PATH', ROOT_DIR / 'router_runtime.sqlite'))

HARDCODED_NUMBERS = [
    '557599991111',
    '553498066683', '556282755369', '557182157263', '557581495845',
    '557581534233', '557581542771', '557581960700', '557588270211',
    '557588270407', '557588330352', '557588340002', '557591433132',
    '557591612728', '557591691926', '557591711025', '557591932073',
    '557591958170', '5575920008385', '557592305601', '557592385248',
    '557592490290', '557592637709', '557592832955', '557599001144',
    '557599668464', '557599669915', '557599966316', '558796686768',
]


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute('''
        CREATE TABLE IF NOT EXISTS blocked_numbers (
          number TEXT PRIMARY KEY,
          reason TEXT DEFAULT '',
          added_at TEXT NOT NULL
        )
    ''')
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for number in HARDCODED_NUMBERS:
        digits = ''.join(c for c in number if c.isdigit())
        if not digits:
            continue
        try:
            conn.execute(
                'INSERT OR IGNORE INTO blocked_numbers (number, reason, added_at) VALUES (?, ?, ?)',
                (digits, 'migrated from guardrails.js hardcoded list', now),
            )
            inserted += 1
        except Exception as e:
            print(f'  SKIP {digits}: {e}')
    conn.commit()
    total = conn.execute('SELECT COUNT(*) FROM blocked_numbers').fetchone()[0]
    conn.close()
    print(f'Migrated {inserted} numbers. Total in DB: {total}')


if __name__ == '__main__':
    migrate()
