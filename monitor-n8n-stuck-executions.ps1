$ErrorActionPreference = 'Stop'

$thresholdMinutes = 2
if ($args.Count -ge 1) {
  $parsed = 0
  if ([int]::TryParse([string]$args[0], [ref]$parsed) -and $parsed -gt 0) {
    $thresholdMinutes = $parsed
  }
}

$python = @"
import json
import sqlite3
from datetime import datetime, timedelta, timezone

threshold_minutes = $thresholdMinutes
cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

conn = sqlite3.connect('/data/database.sqlite')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
rows = cur.execute(
    '''
    SELECT id, workflowId, status, mode, startedAt, stoppedAt, finished
    FROM execution_entity
    WHERE status = 'running'
    ORDER BY startedAt ASC
    '''
).fetchall()
conn.close()

out = []
for row in rows:
    started_raw = str(row['startedAt'] or '').strip()
    started_dt = None
    for candidate in [started_raw.replace(' ', 'T'), started_raw]:
        if not candidate:
            continue
        try:
            started_dt = datetime.fromisoformat(candidate.replace('Z', '+00:00'))
            break
        except Exception:
            pass
    if started_dt is None:
        out.append({**dict(row), 'stuck': False, 'reason': 'unparsed_startedAt'})
        continue
    if started_dt.tzinfo is None:
        started_dt = started_dt.replace(tzinfo=timezone.utc)
    age_seconds = int((datetime.now(timezone.utc) - started_dt).total_seconds())
    if started_dt <= cutoff:
        item = dict(row)
        item['ageSeconds'] = age_seconds
        item['stuck'] = True
        out.append(item)

print(json.dumps({
    'ok': True,
    'thresholdMinutes': threshold_minutes,
    'count': len(out),
    'executions': out,
}, ensure_ascii=False, indent=2))
"@

docker run --rm -v ai_n8n_data:/data python:3.11-slim python -c $python
