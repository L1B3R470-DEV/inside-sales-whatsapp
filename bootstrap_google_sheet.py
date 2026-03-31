import os
import re
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

ENV_FILE = '/work/.env'
DEFAULT_CRED_PATH = '/work/google-service-account.json'


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


def main():
    env = load_env(ENV_FILE)
    cred_path = env.get('GOOGLE_SERVICE_ACCOUNT_JSON_PATH', DEFAULT_CRED_PATH).strip() or DEFAULT_CRED_PATH
    title = env.get('GOOGLE_SHEETS_TITLE', f'CRM Operacional - {datetime.now().strftime("%Y-%m-%d %H:%M")}').strip()
    share_with = env.get('GOOGLE_SHARE_WITH_EMAIL', '').strip()

    if not os.path.exists(cred_path):
        raise RuntimeError(f'Credencial nao encontrada em: {cred_path}')

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = service_account.Credentials.from_service_account_file(cred_path, scopes=scopes)
    sheets = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    drive = build('drive', 'v3', credentials=creds, cache_discovery=False)

    created = sheets.spreadsheets().create(
        body={
            'properties': {'title': title},
            'sheets': [{'properties': {'title': 'leads_snapshot'}}]
        }
    ).execute()

    spreadsheet_id = created['spreadsheetId']
    upsert_env(ENV_FILE, 'GOOGLE_SHEETS_SPREADSHEET_ID', spreadsheet_id)

    shared = False
    if share_with:
        drive.permissions().create(
            fileId=spreadsheet_id,
            body={
                'type': 'user',
                'role': 'writer',
                'emailAddress': share_with
            },
            fields='id',
            sendNotificationEmail=False
        ).execute()
        shared = True

    print('bootstrap_google_sheet_ok')
    print(f'spreadsheet_id={spreadsheet_id}')
    print(f'shared_with_email={shared}')


if __name__ == '__main__':
    main()
