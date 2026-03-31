import base64
import json
import re
import sqlite3
from io import BytesIO
from pathlib import Path

from PIL import Image

WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
N8N_DB = '/data/database.sqlite'
PROJECT_DIR = Path('/work')
ML_DIR = PROJECT_DIR / 'CHATGPT_MACHINE_LEARNING'
OUTPUT_JSON = PROJECT_DIR / 'vitrine_assets_snapshot.json'
SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.pdf'}
SEARCH_DIRS = [
    ML_DIR / 'VITRINE_PEDIDO_INICIAL',
    ML_DIR,
]
EXCLUDED_DIR_MARKERS = {'INFRASOFT', 'COUBALI', 'SISTEMA', 'GERBARCODE'}
PATTERNS = [
    (re.compile(r'(?i)vitrine.*2000|2000.*vitrine|pedido.*2000|2000.*pedido'), 'VITRINE R$ 2.000'),
    (re.compile(r'(?i)vitrine.*4000|4000.*vitrine|pedido.*4000|4000.*pedido'), 'VITRINE R$ 4.000'),
    (re.compile(r'(?i)vitrine.*6000|6000.*vitrine|pedido.*6000|6000.*pedido'), 'VITRINE R$ 6.000'),
    (re.compile(r'(?i)vitrine|pedido inicial|pedido_minimo|pedido minimo'), 'VITRINE DE REFERENCIA'),
]


def now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def is_excluded_path(path):
    upper_parts = {part.upper() for part in path.parts}
    return bool(upper_parts & EXCLUDED_DIR_MARKERS)


def compress_image(raw_bytes):
    img = Image.open(BytesIO(raw_bytes))
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    elif img.mode == 'L':
        img = img.convert('RGB')
    img.thumbnail((1200, 1200))
    out = BytesIO()
    img.save(out, format='JPEG', quality=76, optimize=True)
    return out.getvalue(), 'image/jpeg'


def classify_label(path):
    blob = f'{path.parent.name} {path.name}'
    for rx, label in PATTERNS:
        if rx.search(blob):
            return label
    return ''


def build_asset(path):
    label = classify_label(path) or path.stem
    if path.suffix.lower() == '.pdf':
        return {
            'mediaType': 'document',
            'mimeType': 'application/pdf',
            'mediaBase64': base64.b64encode(path.read_bytes()).decode('ascii'),
            'fileName': path.name,
            'label': label,
            'caption': label,
            'sourcePath': str(path),
        }

    raw = path.read_bytes()
    compressed, mime = compress_image(raw)
    return {
        'mediaType': 'image',
        'mimeType': mime,
        'mediaBase64': base64.b64encode(compressed).decode('ascii'),
        'fileName': path.name,
        'label': label,
        'caption': label,
        'sourcePath': str(path),
    }


def find_assets():
    found = []
    seen = set()
    for root in SEARCH_DIRS:
        if not root.exists():
            continue
        for file_path in root.rglob('*'):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in SUPPORTED_EXTS:
                continue
            if is_excluded_path(file_path):
                continue
            label = classify_label(file_path)
            if not label:
                continue
            key = str(file_path).lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                found.append(build_asset(file_path))
            except Exception:
                continue
    return found


def update_workflow_static_data(items):
    payload = {
        'generatedAt': now_iso(),
        'items': items,
        'count': len(items),
    }

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
    global_data['vitrineAssets'] = payload
    obj['global'] = global_data

    cur.execute(
        'UPDATE workflow_entity SET staticData = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?',
        (json.dumps(obj, ensure_ascii=False, separators=(',', ':')), WORKFLOW_ID),
    )
    conn.commit()
    conn.close()

    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return payload


if __name__ == '__main__':
    items = find_assets()
    payload = update_workflow_static_data(items)
    print('vitrine_assets_ok')
    print(json.dumps({
        'count': payload['count'],
        'snapshot': str(OUTPUT_JSON),
    }, ensure_ascii=False))
