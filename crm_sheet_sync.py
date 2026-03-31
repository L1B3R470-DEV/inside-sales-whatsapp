import json
import os
import sqlite3
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

N8N_DB = '/data/database.sqlite'
CRM_DB = '/work/crm_operacional.sqlite'
ENV_FILE = '/work/.env'
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_env(path):
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    return env


def as_bool(v):
    return str(v).strip().lower() in {'1', 'true', 'yes', 'y', 'sim', 'ativo'}


def sheet_values(service, spreadsheet_id, rng):
    return service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=rng
    ).execute().get('values', [])


def ensure_sheet(service, spreadsheet_id, title, metadata_cache):
    existing = {s['properties']['title'] for s in metadata_cache['sheets']}
    if title in existing:
        return
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            'requests': [
                {
                    'addSheet': {
                        'properties': {
                            'title': title,
                            'gridProperties': {
                                'rowCount': 2000,
                                'columnCount': 30
                            }
                        }
                    }
                }
            ]
        },
    ).execute()
    metadata_cache['sheets'].append({'properties': {'title': title}})


def clear_and_write(service, spreadsheet_id, title, headers, rows):
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f'{title}!A:Z',
        body={}
    ).execute()

    values = [headers]
    for row in rows:
        values.append([row.get(h, '') for h in headers])

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f'{title}!A1',
        valueInputOption='RAW',
        body={'values': values}
    ).execute()


def ensure_headers(service, spreadsheet_id, title, headers):
    values = sheet_values(service, spreadsheet_id, f'{title}!A1:Z1')
    if values and values[0]:
        return
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f'{title}!A1',
        valueInputOption='RAW',
        body={'values': [headers]}
    ).execute()


def fetch_rows(conn, query):
    conn.row_factory = sqlite3.Row
    out = []
    for r in conn.execute(query).fetchall():
        out.append(dict(r))
    return out


def apply_manual_rules_from_sheet(service, spreadsheet_id, crm_conn):
    tab = 'knowledge_rules_input'
    values = sheet_values(service, spreadsheet_id, f'{tab}!A1:Z1000')
    if len(values) <= 1:
        return 0

    header = [str(x).strip() for x in values[0]]
    idx = {k: i for i, k in enumerate(header)}
    required = {'intent', 'pattern', 'response_guidance'}
    if not required.issubset(set(idx.keys())):
        return 0

    upserts = 0
    now = now_iso()
    for row in values[1:]:
        def get(key, default=''):
            i = idx.get(key)
            if i is None or i >= len(row):
                return default
            return str(row[i]).strip()

        intent = get('intent', 'geral') or 'geral'
        pattern = get('pattern', '')
        guidance = get('response_guidance', '')
        if not pattern or not guidance:
            continue
        priority = int(get('priority', '70') or 70)
        active = 1 if as_bool(get('active', 'true')) else 0
        source = get('source', 'sheet_manual') or 'sheet_manual'

        crm_conn.execute(
            '''
            INSERT INTO knowledge_rules (intent, pattern, response_guidance, priority, active, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(intent, pattern, source) DO UPDATE SET
              response_guidance=excluded.response_guidance,
              priority=excluded.priority,
              active=excluded.active,
              updated_at=excluded.updated_at
            ''',
            (intent, pattern, guidance, priority, active, source, now, now),
        )
        upserts += 1

    return upserts


def apply_backlog_updates_from_sheet(service, spreadsheet_id, crm_conn):
    tab = 'backlog_updates'
    values = sheet_values(service, spreadsheet_id, f'{tab}!A1:Z1000')
    if len(values) <= 1:
        return 0

    header = [str(x).strip() for x in values[0]]
    idx = {k: i for i, k in enumerate(header)}
    required = {'backlog_hash', 'status'}
    if not required.issubset(set(idx.keys())):
        return 0

    updates = 0
    now = now_iso()
    for row in values[1:]:
        def get(key, default=''):
            i = idx.get(key)
            if i is None or i >= len(row):
                return default
            return str(row[i]).strip()

        backlog_hash = get('backlog_hash', '')
        status = get('status', '')
        if not backlog_hash or not status:
            continue

        cur = crm_conn.execute(
            '''
            UPDATE learning_backlog
            SET status = ?, updated_at = ?
            WHERE backlog_hash = ?
            ''',
            (status, now, backlog_hash),
        )
        if cur.rowcount:
            updates += cur.rowcount

    return updates


def sync_dynamic_knowledge_to_n8n(crm_conn, n8n_conn, manual_rules_applied, backlog_updates_applied):
    row = n8n_conn.execute(
        'SELECT staticData FROM workflow_entity WHERE id = ?',
        (WORKFLOW_ID,),
    ).fetchone()
    if not row:
        raise RuntimeError(f'Workflow {WORKFLOW_ID} not found')

    static_obj = json.loads(row[0] or '{}')
    global_data = static_obj.get('global', {})

    active_rules = crm_conn.execute(
        '''
        SELECT intent, pattern, response_guidance, priority, source
        FROM knowledge_rules
        WHERE active=1
        ORDER BY priority DESC, updated_at DESC
        LIMIT 20
        '''
    ).fetchall()

    top_questions = crm_conn.execute(
        '''
        SELECT customer_question, intent, confidence, source_created_at
        FROM learning_backlog
        WHERE status='open'
        ORDER BY source_created_at DESC
        LIMIT 12
        '''
    ).fetchall()

    open_backlog = crm_conn.execute(
        "SELECT COUNT(*) c FROM learning_backlog WHERE status='open'"
    ).fetchone()[0]

    now = now_iso()
    dynamic_knowledge = {
        'generatedAt': now,
        'cycleSummary': {
            'newLeadsImported': int(global_data.get('crmSync', {}).get('newLeadsImported', 0)),
            'newInteractionsImported': int(global_data.get('crmSync', {}).get('newInteractionsImported', 0)),
            'newBacklogImported': int(global_data.get('crmSync', {}).get('newBacklogImported', 0)),
            'openBacklog': int(open_backlog),
            'activeRules': len(active_rules),
        },
        'activeRules': [
            {
                'intent': r[0],
                'pattern': r[1],
                'responseGuidance': r[2],
                'priority': r[3],
                'source': r[4],
            } for r in active_rules
        ],
        'topBacklogQuestions': [
            {
                'question': q[0],
                'intent': q[1],
                'confidence': q[2],
                'createdAt': q[3],
            } for q in top_questions
        ],
    }

    crm_sync = global_data.get('crmSync', {})
    crm_sync['lastSheetSyncAt'] = now
    crm_sync['manualRulesAppliedFromSheet'] = int(manual_rules_applied)
    crm_sync['backlogUpdatesAppliedFromSheet'] = int(backlog_updates_applied)
    crm_sync['openBacklog'] = int(open_backlog)
    crm_sync['activeRules'] = len(active_rules)

    global_data['dynamicKnowledge'] = dynamic_knowledge
    global_data['crmSync'] = crm_sync
    static_obj['global'] = global_data

    n8n_conn.execute(
        'UPDATE workflow_entity SET staticData = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?',
        (json.dumps(static_obj, ensure_ascii=False, separators=(',', ':')), WORKFLOW_ID)
    )


def build_sheets_service(env):
    auth_mode = env.get('GOOGLE_AUTH_MODE', 'service_account').strip().lower()

    if auth_mode == 'oauth_user':
        token_path = env.get('GOOGLE_OAUTH_TOKEN_JSON_PATH', '/work/google-oauth-token.json').strip() or '/work/google-oauth-token.json'
        if not os.path.exists(token_path):
            raise RuntimeError(f'OAuth token nao encontrado: {token_path}. Rode bootstrap-google-oauth-user.ps1')

        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w', encoding='utf-8') as f:
                f.write(creds.to_json())

        if not creds.valid:
            raise RuntimeError('OAuth token invalido/expirado sem refresh. Rode bootstrap-google-oauth-user.ps1')

        return build('sheets', 'v4', credentials=creds, cache_discovery=False)

    credentials_path = env.get('GOOGLE_SERVICE_ACCOUNT_JSON_PATH', '/work/google-service-account.json').strip() or '/work/google-service-account.json'
    if not os.path.exists(credentials_path):
        raise RuntimeError(f'Arquivo de credencial nao encontrado: {credentials_path}')

    creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds, cache_discovery=False)


def main():
    env = load_env(ENV_FILE)
    spreadsheet_id = env.get('GOOGLE_SHEETS_SPREADSHEET_ID', '').strip()
    if not spreadsheet_id:
        raise RuntimeError('GOOGLE_SHEETS_SPREADSHEET_ID nao configurado no .env')

    service = build_sheets_service(env)
    metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    crm = sqlite3.connect(CRM_DB)
    n8n = sqlite3.connect(N8N_DB)
    crm.execute('PRAGMA busy_timeout=30000')
    n8n.execute('PRAGMA busy_timeout=30000')
    crm.execute(
        '''
        CREATE TABLE IF NOT EXISTS b2b_reporting_exclusions (
          number TEXT PRIMARY KEY,
          exclusion_reason TEXT,
          source TEXT,
          push_name TEXT,
          customer_name TEXT,
          last_inbound_text TEXT,
          last_seen_at TEXT,
          created_at TEXT,
          updated_at TEXT,
          active INTEGER DEFAULT 1
        )
        '''
    )

    for tab in [
        'leads_snapshot',
        'open_backlog',
        'active_rules',
        'knowledge_cycles',
        'knowledge_rules_input',
        'backlog_updates',
    ]:
        ensure_sheet(service, spreadsheet_id, tab, metadata)

    manual_rules_applied = apply_manual_rules_from_sheet(service, spreadsheet_id, crm)
    backlog_updates_applied = apply_backlog_updates_from_sheet(service, spreadsheet_id, crm)

    leads_rows = fetch_rows(crm, '''
        SELECT
          number, push_name, customer_name, informed_phone, city, instagram,
          company_legal_name, company_cnpj, company_cnpj_situation,
          cnpj_ativo_answer, loja_fisica_answer, book_sales_access,
          revenda_script_stage, revenda_script_completed, first_seen_at,
          last_product_focus, last_product_category,
          lead_stage, last_intent, last_confidence, awaiting_human,
          notes, next_step, last_inbound_text, last_reply_text, last_seen_at, updated_at
        FROM leads
        WHERE number NOT IN (
          SELECT number
          FROM b2b_reporting_exclusions
          WHERE active = 1
        )
        ORDER BY updated_at DESC
        LIMIT 2000
    ''')
    clear_and_write(
        service,
        spreadsheet_id,
        'leads_snapshot',
        [
            'number', 'push_name', 'customer_name', 'informed_phone', 'city', 'instagram',
            'company_legal_name', 'company_cnpj', 'company_cnpj_situation',
            'cnpj_ativo_answer', 'loja_fisica_answer', 'book_sales_access',
            'revenda_script_stage', 'revenda_script_completed', 'first_seen_at',
            'last_product_focus', 'last_product_category',
            'lead_stage', 'last_intent', 'last_confidence', 'awaiting_human',
            'notes', 'next_step', 'last_inbound_text', 'last_reply_text', 'last_seen_at', 'updated_at'
        ],
        leads_rows
    )

    backlog_rows = fetch_rows(crm, '''
        SELECT backlog_hash, number, push_name, intent, confidence, customer_question, source_created_at, status, updated_at
        FROM learning_backlog
        ORDER BY source_created_at DESC
        LIMIT 2000
    ''')
    clear_and_write(
        service,
        spreadsheet_id,
        'open_backlog',
        ['backlog_hash', 'number', 'push_name', 'intent', 'confidence', 'customer_question', 'source_created_at', 'status', 'updated_at'],
        backlog_rows
    )

    rules_rows = fetch_rows(crm, '''
        SELECT intent, pattern, response_guidance, priority, active, source, updated_at
        FROM knowledge_rules
        ORDER BY priority DESC, updated_at DESC
        LIMIT 1000
    ''')
    clear_and_write(
        service,
        spreadsheet_id,
        'active_rules',
        ['intent', 'pattern', 'response_guidance', 'priority', 'active', 'source', 'updated_at'],
        rules_rows
    )

    cycle_rows = fetch_rows(crm, '''
        SELECT run_at, new_leads, new_interactions, new_backlog, open_backlog, generated_rules, notes
        FROM knowledge_cycles
        ORDER BY id DESC
        LIMIT 1000
    ''')
    clear_and_write(
        service,
        spreadsheet_id,
        'knowledge_cycles',
        ['run_at', 'new_leads', 'new_interactions', 'new_backlog', 'open_backlog', 'generated_rules', 'notes'],
        cycle_rows
    )

    ensure_headers(
        service,
        spreadsheet_id,
        'knowledge_rules_input',
        ['intent', 'pattern', 'response_guidance', 'priority', 'active', 'source']
    )
    ensure_headers(
        service,
        spreadsheet_id,
        'backlog_updates',
        ['backlog_hash', 'status']
    )

    sync_dynamic_knowledge_to_n8n(crm, n8n, manual_rules_applied, backlog_updates_applied)

    crm.commit()
    n8n.commit()

    print('crm_sheet_sync_ok')
    print(json.dumps({
        'authMode': env.get('GOOGLE_AUTH_MODE', 'service_account').strip().lower(),
        'spreadsheetId': spreadsheet_id,
        'manualRulesAppliedFromSheet': manual_rules_applied,
        'backlogUpdatesAppliedFromSheet': backlog_updates_applied,
        'tabsSynced': 6
    }, ensure_ascii=False))

    crm.close()
    n8n.close()


if __name__ == '__main__':
    main()
