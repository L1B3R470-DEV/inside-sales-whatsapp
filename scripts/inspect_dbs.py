import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def show_table(cur, table, limit=10):
    cur.execute(f"PRAGMA table_info([{table}])")
    cols = [r[1] for r in cur.fetchall()]
    cur.execute(f"SELECT COUNT(*) FROM [{table}]")
    count = cur.fetchone()[0]
    print(f"\n  [{table}] — {count} rows | cols: {cols}")
    if count > 0 and limit > 0:
        cur.execute(f"SELECT * FROM [{table}] ORDER BY rowid DESC LIMIT {limit}")
        for row in cur.fetchall():
            print(f"    {dict(zip(cols, row))}")

# ── CRM ─────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CRM — crm_operacional.sqlite")
print("="*60)
crm = sqlite3.connect(ROOT / "crm_operacional.sqlite")
cur = crm.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"  Tables: {tables}")

for t in tables:
    show_table(cur, t, limit=5)

# Stats
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM [{t}]")
    print(f"  {t}: {cur.fetchone()[0]} rows")

crm.close()

# ── ROUTER ───────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  ROUTER — router_runtime.sqlite")
print("="*60)
rt = sqlite3.connect(ROOT / "router_runtime.sqlite")
cur2 = rt.cursor()
cur2.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables2 = [r[0] for r in cur2.fetchall()]
print(f"  Tables: {tables2}")

for t in tables2:
    show_table(cur2, t, limit=3)

rt.close()
print("\nDone.")
