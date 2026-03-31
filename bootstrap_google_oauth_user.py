import json
import os
import re
from datetime import datetime

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ENV_FILE = '/work/.env'
DEFAULT_CLIENT_SECRET_PATH = '/work/google-oauth-client.json'
DEFAULT_TOKEN_PATH = '/work/google-oauth-token.json'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]


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


def upsert_env(path, key, value):
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'{key}={value}\n')
        return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = re.compile(rf'^{re.escape(key)}=.*$', flags=re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(f'{key}={value}', content)
    else:
        if not content.endswith('\n'):
            content += '\n'
        content += f'{key}={value}\n'

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def load_or_authenticate(client_secret_path, token_path):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.valid:
        return creds

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    # Uses localhost callback. Run container with -p 8765:8765.
    creds = flow.run_local_server(
        host='0.0.0.0',
        port=8765,
        open_browser=False,
        authorization_prompt_message='Abra esta URL no navegador para autorizar:\n{url}',
        success_message='Autorizacao concluida. Voce pode fechar esta aba.',
    )

    with open(token_path, 'w', encoding='utf-8') as f:
        f.write(creds.to_json())
    return creds


def ensure_tabs(sheets, spreadsheet_id):
    expected = [
        'leads_snapshot',
        'open_backlog',
        'active_rules',
        'knowledge_cycles',
        'knowledge_rules_input',
        'backlog_updates',
    ]
    metadata = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing = {s['properties']['title'] for s in metadata.get('sheets', [])}
    missing = [t for t in expected if t not in existing]
    if not missing:
        return

    reqs = []
    for title in missing:
        reqs.append({
            'addSheet': {
                'properties': {
                    'title': title,
                    'gridProperties': {'rowCount': 2000, 'columnCount': 30},
                }
            }
        })
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': reqs},
    ).execute()


def main():
    env = load_env(ENV_FILE)
    client_secret_path = env.get('GOOGLE_OAUTH_CLIENT_SECRET_JSON_PATH', DEFAULT_CLIENT_SECRET_PATH).strip() or DEFAULT_CLIENT_SECRET_PATH
    token_path = env.get('GOOGLE_OAUTH_TOKEN_JSON_PATH', DEFAULT_TOKEN_PATH).strip() or DEFAULT_TOKEN_PATH
    spreadsheet_id = env.get('GOOGLE_SHEETS_SPREADSHEET_ID', '').strip()
    title = env.get('GOOGLE_SHEETS_TITLE', f'CRM Operacional - {datetime.now().strftime("%Y-%m-%d %H:%M")}').strip()

    if not os.path.exists(client_secret_path):
        raise RuntimeError(f'Arquivo de client secret OAuth nao encontrado: {client_secret_path}')

    creds = load_or_authenticate(client_secret_path, token_path)
    sheets = build('sheets', 'v4', credentials=creds, cache_discovery=False)

    created = False
    if not spreadsheet_id:
        sheet = sheets.spreadsheets().create(body={'properties': {'title': title}}).execute()
        spreadsheet_id = sheet['spreadsheetId']
        created = True

    ensure_tabs(sheets, spreadsheet_id)

    upsert_env(ENV_FILE, 'GOOGLE_AUTH_MODE', 'oauth_user')
    upsert_env(ENV_FILE, 'GOOGLE_OAUTH_CLIENT_SECRET_JSON_PATH', client_secret_path)
    upsert_env(ENV_FILE, 'GOOGLE_OAUTH_TOKEN_JSON_PATH', token_path)
    upsert_env(ENV_FILE, 'GOOGLE_SHEETS_SPREADSHEET_ID', spreadsheet_id)

    print('bootstrap_google_oauth_user_ok')
    print(json.dumps({
        'createdSpreadsheet': created,
        'spreadsheetId': spreadsheet_id,
        'tokenPath': token_path,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
