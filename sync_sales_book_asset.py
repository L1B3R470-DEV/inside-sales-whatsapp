import base64
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
N8N_DB = '/data/database.sqlite'
PROJECT_DIR = Path('/work')
BOOK_FILE = PROJECT_DIR / 'CHATGPT_MACHINE_LEARNING' / 'BOOK_PROSPECCAO_VENDAS_INTERNAS.pdf'
OUTPUT_JSON = PROJECT_DIR / 'sales_book_asset_snapshot.json'
MANIFEST_JSON = PROJECT_DIR / 'asset_manifest.json'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_manifest():
    if not MANIFEST_JSON.exists():
        return {'sourceOfTruth': 'workflow_static_data', 'salesBook': {}}
    data = json.loads(MANIFEST_JSON.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        return {'sourceOfTruth': 'workflow_static_data', 'salesBook': {}}
    return data


def build_asset():
    manifest = load_manifest()
    sales_book = manifest.get('salesBook') if isinstance(manifest.get('salesBook'), dict) else {}
    book_file_name = str(sales_book.get('fileName') or BOOK_FILE.name).strip() or BOOK_FILE.name
    book_file = BOOK_FILE.parent / book_file_name
    caption = str(sales_book.get('caption') or 'BOOK DE VENDAS | Colecao Classe').strip()
    version = str(sales_book.get('version') or '').strip()
    if not book_file.exists():
        raise FileNotFoundError(f'Sales book not found: {book_file}')

    raw = book_file.read_bytes()
    return {
        'fileName': book_file.name,
        'mimeType': 'application/pdf',
        'mediaBase64': base64.b64encode(raw).decode('ascii'),
        'sizeBytes': len(raw),
        'updatedAt': now_iso(),
        'caption': caption,
        'assetVersion': version,
        'sourceOfTruth': str(manifest.get('sourceOfTruth') or 'workflow_static_data'),
    }


def write_snapshot(asset):
    snapshot = {
        'fileName': asset['fileName'],
        'mimeType': asset['mimeType'],
        'sizeBytes': asset['sizeBytes'],
        'updatedAt': asset['updatedAt'],
        'snapshotCreatedAt': now_iso()
    }
    OUTPUT_JSON.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')


def update_workflow_static_data(asset):
    conn = sqlite3.connect(N8N_DB)
    cur = conn.cursor()
    cur.execute('SELECT staticData FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f'Workflow {WORKFLOW_ID} not found')

    obj = json.loads(row[0] or '{}')
    if not isinstance(obj, dict):
        obj = {}

    global_data = obj.get('global')
    if not isinstance(global_data, dict):
        global_data = {}

    global_data['salesBookAsset'] = asset
    obj['global'] = global_data

    cur.execute(
        'UPDATE workflow_entity SET staticData = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?',
        (json.dumps(obj, ensure_ascii=False, separators=(',', ':')), WORKFLOW_ID),
    )
    conn.commit()
    conn.close()


if __name__ == '__main__':
    asset = build_asset()
    write_snapshot(asset)
    update_workflow_static_data(asset)
    print('sales_book_asset_ok')
    print(json.dumps({
        'fileName': asset['fileName'],
        'sizeBytes': asset['sizeBytes'],
        'snapshot': str(OUTPUT_JSON)
    }, ensure_ascii=False))
