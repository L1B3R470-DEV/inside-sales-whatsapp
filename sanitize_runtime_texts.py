import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(r'C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES')
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
N8N_DB = ROOT / 'n8n-database.sqlite'
ROUTER_DB = ROOT / 'router_runtime.sqlite'


def normalize_text(value: str) -> str:
    text = str(value or '')
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'---[\s\S]*$', ' ', text)
    text = re.sub(r'\bClasse\s+Couro\b', 'Classe', text, flags=re.I)
    text = re.sub(r'\bEduardo\s+Silva\b', 'Eduardo Vinhas', text, flags=re.I)
    text = re.sub(r'\b(bolsas?|carteiras?|cintos?|mochilas?|kits?|acessorios?|produtos?|modelos?)\s+(femininas?|masculinas?|feminino|masculino)\b', r'\1', text, flags=re.I)
    text = re.sub(r'\b(femininas?|masculinas?|feminino|masculino|premium)\b', '', text, flags=re.I)
    text = re.sub(r'^aqui e o eduardo(?:\s+vinhas|\s+silva)?(?:,?\s*consultor de vendas internas(?: da classe(?: couro)?)?)?[.!:\-\s]*', '', text, flags=re.I)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def walk(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == 'companyName' and isinstance(v, str):
                out[k] = 'Classe'
            elif k == 'consultantName' and isinstance(v, str):
                out[k] = 'Eduardo Vinhas'
            else:
                out[k] = walk(v)
        return out
    if isinstance(obj, list):
        return [walk(x) for x in obj]
    if isinstance(obj, str):
        return normalize_text(obj)
    return obj

changes = {'n8n_static_rows': 0, 'router_conversation_rows': 0, 'router_cache_rows': 0, 'router_lead_rows': 0, 'router_learning_rows': 0}

if N8N_DB.exists():
    conn = sqlite3.connect(N8N_DB)
    cur = conn.cursor()
    row = cur.execute('select staticData from workflow_entity where id=?', (WORKFLOW_ID,)).fetchone()
    if row and row[0]:
        data = json.loads(row[0])
        new_data = walk(data)
        if json.dumps(data, ensure_ascii=False, sort_keys=True) != json.dumps(new_data, ensure_ascii=False, sort_keys=True):
            cur.execute('update workflow_entity set staticData=?, updatedAt=CURRENT_TIMESTAMP where id=?', (json.dumps(new_data, ensure_ascii=False, separators=(",", ":")), WORKFLOW_ID))
            changes['n8n_static_rows'] = cur.rowcount
            conn.commit()
    conn.close()

if ROUTER_DB.exists():
    conn = sqlite3.connect(ROUTER_DB)
    cur = conn.cursor()
    tables = {r[0] for r in cur.execute("select name from sqlite_master where type='table'").fetchall()}

    def update_text_table(sql_select, sql_update):
        touched = 0
        for rowid, text in cur.execute(sql_select).fetchall():
            new_text = normalize_text(text)
            if new_text != (text or ''):
                cur.execute(sql_update, (new_text, rowid))
                touched += 1
        return touched

    if 'conversation_history' in tables:
        changes['router_conversation_rows'] = update_text_table(
            "select rowid, message_text from conversation_history where direction='outbound'",
            'update conversation_history set message_text=? where rowid=?'
        )
    if 'response_cache' in tables:
        changes['router_cache_rows'] = update_text_table(
            'select rowid, reply_text from response_cache',
            'update response_cache set reply_text=? where rowid=?'
        )
    if 'lead_memory' in tables:
        lead_rows = cur.execute('select rowid, company_name, next_step, summary, open_question, last_outbound_text from lead_memory').fetchall()
        for rowid, company_name, next_step, summary, open_question, last_outbound_text in lead_rows:
            new_company = 'Classe' if str(company_name or '').strip() else str(company_name or '')
            new_next = normalize_text(next_step)
            new_summary = normalize_text(summary)
            new_open = normalize_text(open_question)
            new_last = normalize_text(last_outbound_text)
            if [new_company, new_next, new_summary, new_open, new_last] != [company_name or '', next_step or '', summary or '', open_question or '', last_outbound_text or '']:
                cur.execute('update lead_memory set company_name=?, next_step=?, summary=?, open_question=?, last_outbound_text=? where rowid=?', (new_company, new_next, new_summary, new_open, new_last, rowid))
                changes['router_lead_rows'] += 1
    if 'learning_events' in tables:
        changes['router_learning_rows'] = update_text_table(
            'select rowid, reply_text from learning_events',
            'update learning_events set reply_text=? where rowid=?'
        )
    conn.commit()
    conn.close()

print(json.dumps(changes, ensure_ascii=False))
