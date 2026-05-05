import hashlib
import json
import os
import re
import sqlite3
import subprocess
from datetime import datetime, timezone


CRM_DB = os.getenv('CRM_DB', r'C:\AUTOMACAO\dados\crm_operacional.sqlite')
LOOKBACK_HOURS = int(os.getenv('EVOLUTION_CRM_RECONCILE_LOOKBACK_HOURS', '48'))
PG_CONTAINER = os.getenv('EVOLUTION_POSTGRES_CONTAINER', 'evolution-postgres')
PG_USER = os.getenv('EVOLUTION_POSTGRES_USER', 'evolution')
PG_DB = os.getenv('EVOLUTION_POSTGRES_DB', 'evolution')
DEFAULT_EXCLUDED_NUMBERS = {
    '557583211367',
    '557588340000',
    '5575999991111',
    '557599991111',
    '553498066683',
    '556282755369',
    '557182157263',
    '557581495845',
    '557581534233',
    '557581542771',
    '557581960700',
    '557588270211',
    '557588270407',
    '557588330352',
    '557591433132',
    '557591612728',
    '557591691926',
    '557591711025',
    '557591932073',
    '557591958170',
    '5575920008385',
    '557592305601',
    '557592385248',
    '557592490290',
    '557592637709',
    '557592832955',
    '557599001144',
    '557599668464',
    '557599669915',
    '557599966316',
    '558796686768',
    '557382474263',
}
INTERNAL_NAME_RE = re.compile(r'(classe comercial pedidos|vendas internas classe|estoque|expedi[cç][aã]o|teste|homolog)', re.I)


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def digits_only(value: str) -> str:
    return re.sub(r'\D+', '', str(value or ''))


def env_number_set(name: str) -> set[str]:
    raw = os.getenv(name, '')
    return {digits_only(x) for x in re.split(r'[,;\s]+', raw) if digits_only(x)}


def looks_internal_contact(push_name: str) -> bool:
    return bool(INTERNAL_NAME_RE.search(str(push_name or '')))


def event_iso(epoch_seconds) -> str:
    return datetime.fromtimestamp(int(epoch_seconds), timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def parse_iso(value: str) -> datetime | None:
    raw = str(value or '').strip()
    if not raw:
        return None
    for candidate in (raw.replace('Z', '+00:00'), raw.replace(' ', 'T').replace('Z', '+00:00')):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    return None


def fetch_evolution_events() -> list[dict]:
    query = f"""
WITH recent AS (
  SELECT
    key->>'remoteJid' AS remote_jid,
    key->>'fromMe' AS from_me,
    COALESCE(NULLIF("pushName", ''), '') AS push_name,
    "messageType" AS message_type,
    "messageTimestamp"::bigint AS message_ts,
    COALESCE(
      "message"->>'conversation',
      "message"#>>'{{extendedTextMessage,text}}',
      "message"#>>'{{imageMessage,caption}}',
      "message"#>>'{{videoMessage,caption}}',
      CASE
        WHEN "messageType" = 'imageMessage' THEN '[imagem recebida]'
        WHEN "messageType" = 'videoMessage' THEN '[video recebido]'
        WHEN "messageType" = 'audioMessage' THEN '[audio recebido]'
        WHEN "messageType" = 'documentMessage' THEN '[documento recebido]'
        ELSE ''
      END
    ) AS text
  FROM "Message"
  WHERE "messageTimestamp" >= EXTRACT(EPOCH FROM (NOW() - INTERVAL '{LOOKBACK_HOURS} hours'))::bigint
    AND key->>'remoteJid' ~ '^[0-9]+@s\\.whatsapp\\.net$'
    AND "messageType" IN ('conversation', 'extendedTextMessage', 'imageMessage', 'videoMessage', 'audioMessage', 'documentMessage')
)
SELECT COALESCE(
  json_agg(
    json_build_object(
      'remoteJid', remote_jid,
      'fromMe', from_me,
      'pushName', push_name,
      'messageType', message_type,
      'messageTimestamp', message_ts,
      'text', text
    )
    ORDER BY message_ts
  ),
  '[]'::json
)::text
FROM recent
WHERE trim(coalesce(text, '')) <> '';
"""
    proc = subprocess.run(
        [
            'docker',
            'exec',
            '-i',
            PG_CONTAINER,
            'psql',
            '-U',
            PG_USER,
            '-d',
            PG_DB,
            '-t',
            '-A',
            '-v',
            'ON_ERROR_STOP=1',
        ],
        input=query,
        text=True,
        encoding='utf-8',
        capture_output=True,
        check=True,
    )
    raw = proc.stdout.strip()
    return json.loads(raw or '[]')


def interaction_exists(crm: sqlite3.Connection, number: str, direction: str, text: str, event_dt: datetime) -> bool:
    rows = crm.execute(
        '''
        SELECT event_ts
        FROM interactions
        WHERE number = ? AND direction = ? AND text = ?
        ''',
        (number, direction, text),
    ).fetchall()
    for row in rows:
        existing_dt = parse_iso(row['event_ts'])
        if existing_dt and abs((existing_dt - event_dt).total_seconds()) <= 2:
            return True
    return False


def ensure_lead(
    crm: sqlite3.Connection,
    number: str,
    push_name: str,
    event_ts: str,
    direction: str,
    text: str,
    allow_create: bool,
) -> None:
    if not allow_create:
        return

    crm.execute(
        '''
        INSERT OR IGNORE INTO leads (
          number, push_name, lead_stage, last_intent, last_confidence,
          awaiting_human, notes, next_step, last_seen_at, updated_at, first_seen_at,
          last_inbound_text, last_reply_text
        )
        VALUES (?, ?, 'novo', 'geral', 0, 0, '', '', ?, ?, ?, ?, ?)
        ''',
        (
            number,
            push_name,
            event_ts,
            event_ts,
            event_ts,
            text if direction == 'inbound' else '',
            text if direction == 'outbound' else '',
        ),
    )


def update_lead_from_event(
    crm: sqlite3.Connection,
    number: str,
    push_name: str,
    direction: str,
    text: str,
    event_ts: str,
    allow_create: bool,
) -> None:
    ensure_lead(crm, number, push_name, event_ts, direction, text, allow_create)
    crm.execute(
        '''
        UPDATE leads
        SET
          push_name = CASE
            WHEN ? <> '' AND (push_name IS NULL OR trim(push_name) = '') THEN ?
            ELSE push_name
          END,
          last_inbound_text = CASE WHEN ? = 'inbound' THEN ? ELSE last_inbound_text END,
          last_reply_text = CASE WHEN ? = 'outbound' THEN ? ELSE last_reply_text END,
          last_seen_at = ?,
          updated_at = ?
        WHERE number = ?
        ''',
        (push_name, push_name, direction, text, direction, text, event_ts, datetime.now(timezone.utc).isoformat(), number),
    )


def main() -> None:
    events = fetch_evolution_events()
    crm = sqlite3.connect(CRM_DB, timeout=60)
    crm.row_factory = sqlite3.Row
    crm.execute('PRAGMA busy_timeout = 60000')
    existing_leads = {
        str(row['number'])
        for row in crm.execute('SELECT number FROM leads').fetchall()
    }
    excluded_numbers = DEFAULT_EXCLUDED_NUMBERS | env_number_set('CRM_REPORTING_EXCLUDED_NUMBERS')
    try:
        excluded_numbers |= {
            str(row['number'])
            for row in crm.execute(
                'SELECT number FROM b2b_reporting_exclusions WHERE active = 1'
            ).fetchall()
        }
    except sqlite3.OperationalError:
        pass

    inserted = 0
    duplicates = 0
    skipped_excluded = 0
    skipped_orphan_outbound = 0
    touched_numbers = set()

    for event in events:
        number = digits_only(str(event.get('remoteJid', '')).split('@', 1)[0])
        text = str(event.get('text', '') or '').strip()
        if not number or not text:
            continue

        direction = 'outbound' if str(event.get('fromMe', '')).lower() == 'true' else 'inbound'
        push_name = str(event.get('pushName', '') or '').strip()
        if number in excluded_numbers or looks_internal_contact(push_name):
            skipped_excluded += 1
            continue

        lead_exists = number in existing_leads
        allow_create = lead_exists or direction == 'inbound'
        if not allow_create:
            skipped_orphan_outbound += 1
            continue

        ts = event_iso(event.get('messageTimestamp'))
        event_dt = parse_iso(ts)
        if event_dt is None:
            continue

        if interaction_exists(crm, number, direction, text, event_dt):
            duplicates += 1
        else:
            h = sha_text(f'{number}|{direction}|{text}|{ts}')
            cur = crm.execute(
                '''
                INSERT OR IGNORE INTO interactions
                  (interaction_hash, number, direction, text, intent, confidence, needs_human, event_ts, created_at)
                VALUES (?, ?, ?, ?, '', 0, 0, ?, ?)
                ''',
                (h, number, direction, text, ts, datetime.now(timezone.utc).isoformat()),
            )
            inserted += cur.rowcount

        update_lead_from_event(crm, number, push_name, direction, text, ts, allow_create)
        existing_leads.add(number)
        touched_numbers.add(number)

    crm.commit()
    crm.close()

    print(
        json.dumps(
            {
                'action': 'evolution_crm_reconcile',
                'lookbackHours': LOOKBACK_HOURS,
                'eventsScanned': len(events),
                'interactionsInserted': inserted,
                'duplicatesSkipped': duplicates,
                'skippedExcluded': skipped_excluded,
                'skippedOrphanOutbound': skipped_orphan_outbound,
                'leadsTouched': len(touched_numbers),
            },
            ensure_ascii=False,
        )
    )


if __name__ == '__main__':
    main()
