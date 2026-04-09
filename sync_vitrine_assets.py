import base64
import json
import re
import sqlite3
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False

WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
N8N_DB = '/data/database.sqlite'
PROJECT_DIR = Path('/work')
ML_DIR = PROJECT_DIR / 'CHATGPT_MACHINE_LEARNING'
OUTPUT_JSON = PROJECT_DIR / 'vitrine_assets_snapshot.json'
MANIFEST_JSON = PROJECT_DIR / 'asset_manifest.json'
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
DEFAULT_PREFERRED_ORDER = [
    'VITRINE_CLASSE.png',
    'SUGESTAO_PEDIDO_2000_FEMININO.pdf',
    'SUGESTAO_PEDIDO_4000_FEMININO.pdf',
    'SUGESTAO_PEDIDO_6000_FEMININO.pdf',
]


def now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def load_manifest():
    if not MANIFEST_JSON.exists():
        return {'sourceOfTruth': 'workflow_static_data', 'vitrineAssets': []}
    data = json.loads(MANIFEST_JSON.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        return {'sourceOfTruth': 'workflow_static_data', 'vitrineAssets': []}
    return data


def is_excluded_path(path):
    upper_parts = {part.upper() for part in path.parts}
    return bool(upper_parts & EXCLUDED_DIR_MARKERS)


def compress_image(raw_bytes):
    if not HAS_PIL:
        return raw_bytes, 'image/png'
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


def guess_image_mime(path):
    suffix = path.suffix.lower()
    if suffix in {'.jpg', '.jpeg'}:
        return 'image/jpeg'
    if suffix == '.webp':
        return 'image/webp'
    if suffix == '.bmp':
        return 'image/bmp'
    return 'image/png'


def build_asset(path, manifest_entry=None):
    manifest_entry = manifest_entry or {}
    label = str(manifest_entry.get('label') or classify_label(path) or path.stem).strip()
    version = str(manifest_entry.get('version') or '').strip()
    if path.suffix.lower() == '.pdf':
        return {
            'mediaType': 'document',
            'mimeType': 'application/pdf',
            'mediaBase64': base64.b64encode(path.read_bytes()).decode('ascii'),
            'fileName': path.name,
            'label': label,
            'caption': label,
            'sourcePath': str(path),
            'assetVersion': version,
        }

    raw = path.read_bytes()
    compressed, mime = compress_image(raw)
    if not HAS_PIL:
        mime = guess_image_mime(path)
    return {
        'mediaType': 'image',
        'mimeType': mime,
        'mediaBase64': base64.b64encode(compressed).decode('ascii'),
        'fileName': path.name,
        'label': label,
        'caption': label,
        'sourcePath': str(path),
        'assetVersion': version,
    }


def find_assets():
    found = []
    seen = set()
    preferred_paths = []
    manifest = load_manifest()
    manifest_entries = manifest.get('vitrineAssets') if isinstance(manifest.get('vitrineAssets'), list) else []
    preferred_order = [str(item.get('fileName') or '').strip() for item in manifest_entries if str(item.get('fileName') or '').strip()]
    if not preferred_order:
        preferred_order = DEFAULT_PREFERRED_ORDER
    manifest_by_file = {
        str(item.get('fileName') or '').strip(): item
        for item in manifest_entries
        if isinstance(item, dict) and str(item.get('fileName') or '').strip()
    }

    for file_name in preferred_order:
        for root in SEARCH_DIRS:
            candidate = root / file_name
            if candidate.exists() and candidate.is_file() and not is_excluded_path(candidate):
                preferred_paths.append(candidate)
                break

    for file_path in preferred_paths:
        key = str(file_path).lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            found.append(build_asset(file_path, manifest_by_file.get(file_path.name)))
        except Exception:
            continue

    if found:
        return found

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
                found.append(build_asset(file_path, manifest_by_file.get(file_path.name)))
            except Exception:
                continue
    return found[:5]


def update_workflow_static_data(items):
    manifest = load_manifest()
    payload = {
        'generatedAt': now_iso(),
        'items': items,
        'count': len(items),
        'sourceOfTruth': str(manifest.get('sourceOfTruth') or 'workflow_static_data'),
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
