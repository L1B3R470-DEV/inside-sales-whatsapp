import base64
import json
import re
import sqlite3
from io import BytesIO
from pathlib import Path

import openpyxl
from PIL import Image

WORKFLOW_ID = 'zN3heKJVLO8w4dG6'
N8N_DB = '/data/database.sqlite'
DESKTOP_DIR = Path('/work/..')
PROJECT_DIR = Path('/work')
ML_DIR = PROJECT_DIR / 'CHATGPT_MACHINE_LEARNING'
IMAGE_BANK_DIR = ML_DIR / 'COLE??O - BANCO DE IMAGENS'
OUTPUT_JSON = PROJECT_DIR / 'product_media_catalog_snapshot.json'
SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
EXCLUDED_DIR_MARKERS = {'INFRASOFT', 'COUBALI', 'SISTEMA', 'GERBARCODE'}

GROUP_MAPPING = {
    ('FEMININO', 'BOLSAS'): 'BOLSAS FEMININAS',
    ('FEMININO', 'CINTO FEMININO'): 'CINTOS FEMININOS',
    ('MASCULINO', 'CINTO MASCULINO'): 'CINTOS MASCULINOS',
    ('FEMININO', 'CARTEIRA FEMININA'): 'CARTEIRAS FEMININAS',
    ('MASCULINO', 'CARTEIRA MASCULINA'): 'CARTEIRAS MASCULINAS',
    ('FEMININO', 'ACESSORIO FEMININO'): 'ACESSORIOS FEMININOS',
    ('MASCULINO', 'ACESSORIO MASCULINO'): 'ACESSORIOS MASCULINOS',
    ('FEMININO', 'MOCHILA FEMININA'): 'MOCHILAS FEMININAS',
    ('MASCULINO', 'MOCHILA MASCULINA'): 'MOCHILAS MASCULINAS',
    ('FEMININO', 'KIT FEM'): 'KITS FEMININOS',
    ('MASCULINO', 'KIT MASC'): 'KITS MASCULINOS',
}


def now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def compact(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def normalize_text(value):
    return compact(value).upper()


def normalize_ref_key(value):
    return re.sub(r'[^A-Z0-9]', '', normalize_text(value))


def digits_only(value):
    return re.sub(r'\D', '', str(value or ''))


def resolve_ranking_file():
    candidate_roots = [Path('/desktop'), DESKTOP_DIR, Path('/work')]
    matches = []
    for root in candidate_roots:
        if root.exists():
            matches.extend(sorted(root.glob('RANKING*INVERNO_26.xlsm')))
    if not matches:
        raise FileNotFoundError('Ranking file not found on Desktop')
    return matches[0]


def product_display_type(group_name, subgroup_name):
    group_name = normalize_text(group_name)
    subgroup_name = normalize_text(subgroup_name)

    if group_name == 'BOLSAS':
        return subgroup_name or 'BOLSA'
    if 'MOCHILA' in group_name:
        return subgroup_name or group_name
    if 'ACESSORIO' in group_name:
        return subgroup_name or group_name
    if 'CARTEIRA' in group_name:
        return group_name
    if 'CINTO' in group_name:
        return group_name
    if 'KIT' in group_name:
        return subgroup_name or group_name
    return subgroup_name or group_name


def compress_image_to_jpeg(raw_bytes):
    img = Image.open(BytesIO(raw_bytes))
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    elif img.mode == 'L':
        img = img.convert('RGB')

    img.thumbnail((900, 900))
    out = BytesIO()
    img.save(out, format='JPEG', quality=72, optimize=True)
    return out.getvalue(), 'image/jpeg'


def image_asset_from_bytes(raw_bytes, file_name, caption):
    compressed, mime = compress_image_to_jpeg(raw_bytes)
    return {
        'mimeType': mime,
        'mediaBase64': base64.b64encode(compressed).decode('ascii'),
        'fileName': str(file_name or '').strip(),
        'caption': str(caption or '').strip(),
    }


def extract_row_images(ws):
    row_images = {}
    for img in getattr(ws, '_images', []):
        try:
            row = img.anchor._from.row + 1
            if row < 6:
                continue
            raw = img._data()
            row_images[row] = raw
        except Exception:
            continue
    return row_images


def is_excluded_path(path):
    upper_parts = {part.upper() for part in path.parts}
    return bool(upper_parts & EXCLUDED_DIR_MARKERS)


def index_image_bank():
    index_by_norm = {}
    index_by_digits = {}
    if not IMAGE_BANK_DIR.exists():
        return index_by_norm, index_by_digits

    for file_path in IMAGE_BANK_DIR.rglob('*'):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_IMAGE_EXTS:
            continue
        if is_excluded_path(file_path):
            continue

        stem = file_path.stem.upper().strip()
        token_match = re.match(r'^([A-Z0-9-]+)', stem)
        token = token_match.group(1) if token_match else stem
        norm_key = normalize_ref_key(token)
        digit_key = digits_only(token)
        if norm_key:
            index_by_norm.setdefault(norm_key, []).append(file_path)
        if digit_key:
            index_by_digits.setdefault(digit_key, []).append(file_path)

    for bucket in (index_by_norm, index_by_digits):
        for key in list(bucket.keys()):
            bucket[key] = sorted(set(bucket[key]), key=lambda p: str(p).lower())

    return index_by_norm, index_by_digits


def resolve_image_bank_assets(ref, caption, index_by_norm, index_by_digits):
    ref_norm = normalize_ref_key(ref)
    ref_digits = digits_only(ref)
    candidates = []
    seen = set()

    for p in index_by_norm.get(ref_norm, []):
        if p not in seen:
            candidates.append(p)
            seen.add(p)
    for p in index_by_digits.get(ref_digits, []):
        if p not in seen:
            candidates.append(p)
            seen.add(p)

    assets = []
    for path in candidates[:4]:
        try:
            raw = path.read_bytes()
            assets.append(image_asset_from_bytes(raw, path.name, caption))
        except Exception:
            continue
    return assets


def build_catalog():
    ranking_path = resolve_ranking_file()
    wb = openpyxl.load_workbook(ranking_path, data_only=True, read_only=False, keep_vba=True)
    ws = wb['RANK GERAL']
    row_images = extract_row_images(ws)
    bank_norm, bank_digits = index_image_bank()

    categories = {}

    for row_idx, row in enumerate(ws.iter_rows(min_row=6, values_only=True), start=6):
        ref = compact(row[0])
        line_name = compact(row[2])
        group_name = compact(row[3])
        subgroup_name = compact(row[4])
        qty_total = row[13]

        if not ref or qty_total in (None, ''):
            continue

        try:
            rank_total = int(round(float(qty_total)))
        except Exception:
            continue

        category_name = GROUP_MAPPING.get((line_name, group_name), compact(f'{group_name} {line_name}'))
        categories.setdefault(category_name, [])

        display_type = product_display_type(group_name, subgroup_name)
        caption = f"{display_type} - {ref}"
        primary_asset = None

        bank_assets = resolve_image_bank_assets(ref, caption, bank_norm, bank_digits)
        if bank_assets:
            primary_asset = bank_assets[0]
        elif row_idx in row_images:
            try:
                primary_asset = image_asset_from_bytes(row_images[row_idx], f'{ref}.jpg', caption)
            except Exception:
                primary_asset = None

        entry = {
            'ref': ref,
            'line': line_name,
            'group': group_name,
            'subgroup': subgroup_name,
            'category': category_name,
            'displayType': display_type,
            'rankTotal': rank_total,
            'hasImage': bool(primary_asset),
            'caption': caption,
            'imageVariantCount': len(bank_assets) if bank_assets else (1 if primary_asset else 0),
            'imageSource': 'bank' if bank_assets else ('worksheet' if primary_asset else 'none'),
        }
        if primary_asset:
            entry.update(primary_asset)
        categories[category_name].append(entry)

    ordered_categories = sorted(
        categories.keys(),
        key=lambda key: (-sum(item['rankTotal'] for item in categories[key]), key)
    )

    final_categories = {}
    for category_name in ordered_categories:
        ranked = sorted(categories[category_name], key=lambda item: (-item['rankTotal'], item['ref']))
        with_images = [item for item in ranked if item.get('hasImage')]
        final_categories[category_name] = {
            'top10': ranked[:10],
            'topWithImage': with_images[:30],
        }

    catalog = {
        'generatedAt': now_iso(),
        'sourceFile': ranking_path.name,
        'imageBankDir': str(IMAGE_BANK_DIR),
        'categories': final_categories,
        'categoryNames': ordered_categories,
    }
    return catalog


def update_workflow_static_data(catalog):
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

    global_data['productCatalog'] = catalog
    obj['global'] = global_data

    cur.execute(
        'UPDATE workflow_entity SET staticData = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?',
        (json.dumps(obj, ensure_ascii=False, separators=(',', ':')), WORKFLOW_ID),
    )
    conn.commit()
    conn.close()


def write_snapshot(catalog):
    OUTPUT_JSON.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    catalog = build_catalog()
    write_snapshot(catalog)
    update_workflow_static_data(catalog)

    image_count = 0
    bank_count = 0
    for category in catalog['categories'].values():
        top_with_image = category.get('topWithImage') or []
        image_count += len(top_with_image)
        bank_count += sum(1 for item in top_with_image if item.get('imageSource') == 'bank')

    print('product_media_catalog_ok')
    print(json.dumps({
        'sourceFile': catalog['sourceFile'],
        'categories': len(catalog['categoryNames']),
        'imageEntries': image_count,
        'bankImageEntries': bank_count,
        'snapshot': str(OUTPUT_JSON),
    }, ensure_ascii=False))
