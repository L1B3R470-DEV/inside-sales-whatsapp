import csv
import hashlib
import json
import os
import re
import sqlite3
import zipfile
from collections import Counter
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

N8N_DB = os.getenv('N8N_DB', '/data/database.sqlite')
CRM_DB = os.getenv('CRM_DB', '/work/crm_operacional.sqlite')
EXPORT_DIR = os.getenv('CRM_EXPORT_DIR', os.getenv('EXPORT_DIR', '/work/crm_exports'))
ML_DIR = os.getenv('CRM_ML_DIR', os.getenv('ML_DIR', '/work/CHATGPT_MACHINE_LEARNING'))
IGNORED_CONTACTS_FILE = os.getenv('IGNORED_CONTACTS_FILE', '/work/LISTA_DE_CONTATOS_IGNORADOS.xlsx')
IGNORED_CONTACTS_ML_FILE = os.getenv(
    'IGNORED_CONTACTS_ML_FILE',
    os.path.join(ML_DIR, '_AUTO_LISTA_DE_CONTATOS_IGNORADOS.txt'),
)
LEADS_WORKBOOK_PATH = os.getenv('LEADS_WORKBOOK_PATH', '/work/LEADS_INSIDE_SALES_AUTO.xlsx')
LEADS_WORKBOOK_EXPORT_PATH = os.getenv(
    'LEADS_WORKBOOK_EXPORT_PATH',
    os.path.join(EXPORT_DIR, 'LEADS_INSIDE_SALES_AUTO.xlsx'),
)
WORKFLOW_ID = 'zN3heKJVLO8w4dG6'

STOPWORDS = {
    'para', 'com', 'sem', 'mais', 'menos', 'sobre', 'quero', 'gostaria', 'preciso', 'pode', 'favor', 'agora', 'depois',
    'como', 'qual', 'quais', 'onde', 'quando', 'isso', 'essa', 'esse', 'isto', 'pela', 'pelo', 'meu', 'minha', 'seu', 'sua',
    'dos', 'das', 'por', 'uma', 'uns', 'umas', 'nos', 'nas', 'que', 'vou', 'tem', 'tenho', 'saber', 'valor', 'preco', 'prazo'
}

INTENT_RULES = {
    'atacado_quantidade': {
        'pattern': r'(atacado|revenda|lote|quantidade)',
        'guidance': 'Quando identificar intencao de atacado/revenda, priorizar qualificacao com produto, quantidade, cidade e prazo, e conduzir para proposta personalizada.',
        'priority': 95,
    },
    'preco_orcamento': {
        'pattern': r'(preco|valor|orcamento|cotacao)',
        'guidance': 'Em pedidos de preco/orcamento, evitar valor fechado sem contexto; coletar quantidade, modelo e prazo antes da proposta.',
        'priority': 92,
    },
    'prazo_entrega': {
        'pattern': r'(prazo|entrega|frete|envio)',
        'guidance': 'Em duvidas de prazo, coletar cidade/UF e urgencia para orientar melhor opcao de atendimento.',
        'priority': 90,
    },
    'produto_catalogo': {
        'pattern': r'(catalogo|modelo|produto|carteira|cinto)',
        'guidance': 'Ao pedir catalogo/produto, recomendar caminho com base em uso e quantidade, finalizando com pergunta de avancao.',
        'priority': 88,
    },
    'pagamento': {
        'pattern': r'(pagamento|pix|cartao|boleto|parcelamento)',
        'guidance': 'Em pagamento, contextualizar que condicao depende do pedido e conduzir para fechamento com dados minimos.',
        'priority': 86,
    },
}


TEXT_EXTENSIONS = {'.txt', '.md', '.csv', '.json', '.log', '.xml', '.html', '.htm'}
OFFICE_XML_EXTENSIONS = {'.docx', '.xlsx', '.pptx', '.odt', '.ods'}
BINARY_OFFICE_EXTENSIONS = {'.doc', '.xls'}
OTHER_DOC_EXTENSIONS = {'.pdf', '.rtf'}
ML_EXTENSIONS = TEXT_EXTENSIONS | OFFICE_XML_EXTENSIONS | BINARY_OFFICE_EXTENSIONS | OTHER_DOC_EXTENSIONS
EXCLUDED_B2B_REASONS = {'cnpj_inativo_ou_ausente', 'sem_loja_fisica'}
DEFAULT_CRM_REPORTING_EXCLUDED_NUMBERS = {
    # Numeros internos, homologacao, testes e denylist operacional conhecida.
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
    '557588340002',
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
TEST_ARTIFACT_RE = re.compile(
    r'\b(teste|test|e2e|debug|dedupe|homolog|phelper|infra|validacao|dashboard|numero\s+resolvido)\b',
    re.IGNORECASE,
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def digits_only(value: str) -> str:
    return re.sub(r'\D+', '', str(value or ''))


def env_number_set(name: str) -> set:
    raw = os.getenv(name, '')
    return {digits_only(x) for x in re.split(r'[,;\s]+', raw) if digits_only(x)}


def crm_reporting_excluded_numbers() -> set:
    return set(DEFAULT_CRM_REPORTING_EXCLUDED_NUMBERS) | env_number_set('CRM_REPORTING_EXCLUDED_NUMBERS')


def normalized_question_key(value: str) -> str:
    return re.sub(r'\s+', ' ', str(value or '').strip().lower())


def is_test_artifact_text(*values: str) -> bool:
    joined = ' '.join(str(v or '') for v in values)
    return bool(TEST_ARTIFACT_RE.search(joined))


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def sha_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def normalize_tokens(text: str):
    t = (text or '').lower()
    t = re.sub(r'[^a-z0-9à-ÿ\s]', ' ', t)
    tokens = [x for x in t.split() if len(x) >= 4 and x not in STOPWORDS]
    return tokens


def export_csv(path: str, headers, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(headers)
        for row in rows:
            w.writerow([row[h] for h in headers])


def xlsx_col_name(index: int) -> str:
    out = []
    i = int(index)
    while i >= 0:
        i, rem = divmod(i, 26)
        out.append(chr(65 + rem))
        i -= 1
    return ''.join(reversed(out))


def xlsx_inline_cell(cell_ref: str, value, style: int = 0) -> str:
    if value is None:
        value = ''
    if isinstance(value, dict) and value.get('formula'):
        formula = xml_escape(str(value.get('formula', '')), {'"': '&quot;'})
        return f'<c r="{cell_ref}" s="{style}"><f>{formula}</f></c>'
    if isinstance(value, bool):
        value = 'SIM' if value else 'NAO'
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{cell_ref}" s="{style}"><v>{value}</v></c>'
    else:
        value = str(value)

    safe = xml_escape(value, {'"': '&quot;'}).replace('\r\n', '\n').replace('\r', '\n')
    return (
        f'<c r="{cell_ref}" t="inlineStr" s="{style}">'
        f'<is><t xml:space="preserve">{safe}</t></is>'
        f'</c>'
    )


def build_sheet_xml(headers, rows) -> str:
    headers = list(headers or [])
    rows = list(rows or [])
    total_rows = len(rows) + 1
    total_cols = max(len(headers), 1)
    last_cell = f'{xlsx_col_name(total_cols - 1)}{max(total_rows, 1)}'

    xml_rows = []
    header_cells = []
    for col_idx, header in enumerate(headers):
        cell_ref = f'{xlsx_col_name(col_idx)}1'
        header_cells.append(xlsx_inline_cell(cell_ref, header, style=1))
    xml_rows.append(f'<row r="1">{"".join(header_cells)}</row>')

    for row_idx, row in enumerate(rows, start=2):
        row_cells = []
        for col_idx, header in enumerate(headers):
            cell_ref = f'{xlsx_col_name(col_idx)}{row_idx}'
            value = row[header] if isinstance(row, sqlite3.Row) else row.get(header)
            row_cells.append(xlsx_inline_cell(cell_ref, value, style=0))
        xml_rows.append(f'<row r="{row_idx}">{"".join(row_cells)}</row>')

    auto_filter = f'<autoFilter ref="A1:{last_cell}"/>' if headers else ''

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last_cell}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        f'{auto_filter}'
        '</worksheet>'
    )


def export_xlsx_workbook(path: str, sheets):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for idx in range(len(sheets)):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{idx + 1}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append('</Types>')

    workbook_xml = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        '<sheets>',
    ]
    workbook_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for idx, sheet in enumerate(sheets, start=1):
        safe_name = xml_escape(str(sheet['name'])[:31] or f'Sheet{idx}', {'"': '&quot;'})
        workbook_xml.append(f'<sheet name="{safe_name}" sheetId="{idx}" r:id="rId{idx}"/>')
        workbook_rels.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
    workbook_xml.extend(['</sheets>', '</workbook>'])
    workbook_rels.append(
        f'<Relationship Id="rId{len(sheets) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels.append('</Relationships>')

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font>'
        '</fonts>'
        '<fills count="2">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '</fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )

    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ''.join(content_types))
        z.writestr('_rels/.rels', root_rels)
        z.writestr('xl/workbook.xml', ''.join(workbook_xml))
        z.writestr('xl/_rels/workbook.xml.rels', ''.join(workbook_rels))
        z.writestr('xl/styles.xml', styles_xml)
        for idx, sheet in enumerate(sheets, start=1):
            z.writestr(
                f'xl/worksheets/sheet{idx}.xml',
                build_sheet_xml(sheet['headers'], sheet['rows'])
            )


def format_br_datetime(value: str) -> str:
    raw = str(value or '').strip()
    if not raw:
        return ''
    try:
        normalized = raw.replace('Z', '+00:00')
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        br_dt = dt.astimezone()
        return br_dt.strftime('%H:%M - %d/%m/%Y')
    except Exception:
        return raw


def map_book_sales_access(value: str) -> str:
    mapping = {
        'eligible': 'LIBERADO',
        'locked_pending_triage': 'BLOQUEADO - TRIAGEM PENDENTE',
        'locked_invalid_cnpj': 'BLOQUEADO - CNPJ INVALIDO',
        'locked_invalid_cnpj_status': 'BLOQUEADO - CNPJ INATIVO',
        'locked_pf_ecommerce': 'DIRECIONADO AO E-COMMERCE',
        'locked_ineligible': 'BLOQUEADO - FORA DE POLITICA',
    }
    key = str(value or '').strip().lower()
    return mapping.get(key, str(value or '').strip().upper())


def make_instagram_cell(value: str):
    raw = str(value or '').strip()
    if not raw:
        return '(NÃO INFORMADO)'

    norm = raw.lower()
    if norm in {'sim', 'yes', 'ok', 'positivo'}:
        return '(NÃO INFORMADO)'
    if norm in {'nao informado', 'não informado'}:
        return '(NÃO INFORMADO)'
    if norm in {'nao possui', 'não possui', 'nao tenho', 'não tenho'}:
        return '(NÃO POSSUI)'

    handle = raw
    if 'instagram.com/' in norm:
        url = raw
        label = raw
    else:
        if not handle.startswith('@'):
            handle = f'@{handle.lstrip("@")}'
        slug = handle.lstrip('@')
        if not slug:
            return '(NÃO INFORMADO)'
        url = f'https://www.instagram.com/{slug}/'
        label = handle

    safe_url = url.replace('"', '""')
    safe_label = label.replace('"', '""')
    return {'formula': f'HYPERLINK("{safe_url}","{safe_label}")'}


def build_leads_workbook_rows(rows):
    out = []
    for row in rows:
        out.append({
            'NÚMERO': row['number'],
            'NOME NO WHATSAPP': row['push_name'],
            'NOME DO LEAD': row['customer_name'],
            'TELEFONE INFORMADO': row['informed_phone'],
            'CIDADE': row['city'],
            'INSTAGRAM': make_instagram_cell(row['instagram']),
            'RAZÃO SOCIAL': row['company_legal_name'],
            'CNPJ': row['company_cnpj'],
            'SITUAÇÃO DO CNPJ': row['company_cnpj_situation'],
            'STATUS DO BOOK': map_book_sales_access(row['book_sales_access']),
            'ESTÁGIO DO LEAD': row['lead_stage'],
            'ÚLTIMA INTENÇÃO': row['last_intent'],
            'CONFIANÇA': row['last_confidence'],
            'AGUARDANDO HUMANO': 'SIM' if int(row['awaiting_human'] or 0) else 'NÃO',
            'OBSERVAÇÕES': row['notes'],
            'PRÓXIMO PASSO': row['next_step'],
            'ÚLTIMA MENSAGEM DO LEAD': row['last_inbound_text'],
            'ÚLTIMA RESPOSTA DO ATENDENTE': row['last_reply_text'],
            'PRIMEIRO CONTATO': format_br_datetime(row['first_seen_at']),
            'ÚLTIMA INTERAÇÃO': format_br_datetime(row['last_seen_at']),
            'ATUALIZADO EM': format_br_datetime(row['updated_at']),
        })
    return out


def build_interactions_workbook_rows(rows):
    out = []
    for row in rows:
        out.append({
            'NÚMERO': row['number'],
            'DIREÇÃO': 'ENTRADA' if str(row['direction'] or '').lower() == 'inbound' else 'SAÍDA',
            'MENSAGEM': row['text'],
            'INTENÇÃO': row['intent'],
            'CONFIANÇA': row['confidence'],
            'EXIGE HUMANO': 'SIM' if int(row['needs_human'] or 0) else 'NÃO',
            'DATA/HORA DO EVENTO': format_br_datetime(row['event_ts']),
            'REGISTRADO EM': format_br_datetime(row['created_at']),
        })
    return out


def build_summary_workbook_rows(summary_rows):
    label_map = {
        'new_leads': 'NOVOS LEADS',
        'new_interactions': 'NOVAS INTERAÇÕES',
        'new_backlog': 'NOVOS ITENS DE APRENDIZADO',
        'open_backlog': 'BACKLOG ABERTO',
        'active_rules': 'REGRAS ATIVAS',
        'generated_rules': 'REGRAS GERADAS',
        'ml_docs_indexed_now': 'DOCUMENTOS INDEXADOS NO CICLO',
        'ml_docs_active': 'DOCUMENTOS ATIVOS',
        'ignored_contacts_active': 'CONTATOS IGNORADOS',
        'generated_at': 'GERADO EM',
    }
    out = []
    for row in summary_rows:
        metric = str(row.get('metric', '')).strip()
        value = row.get('value', '')
        if metric == 'generated_at':
            value = format_br_datetime(str(value or ''))
        out.append({
            'MÉTRICA': label_map.get(metric, metric.upper()),
            'VALOR': value,
        })
    return out


def safe_decode_bytes(raw: bytes) -> str:
    if not raw:
        return ''
    for enc in ('utf-8', 'utf-16', 'latin1'):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode('utf-8', errors='ignore')


def is_readable_text_line(value: str) -> bool:
    s = re.sub(r'\s+', ' ', str(value or '')).strip()
    if len(s) < 20:
        return False

    low = s.lower()
    blocked = ('endstream', 'endobj', '%pdf', ' xref ', ' obj ')
    if any(b in low for b in blocked):
        return False

    printable = sum(1 for ch in s if (ch.isalnum() or ch in " .,!?;:()/-_@%&'\""))
    letters = sum(1 for ch in s if ch.isalpha())
    printable_ratio = printable / max(len(s), 1)
    letters_ratio = letters / max(len(s), 1)
    return printable_ratio >= 0.80 and letters_ratio >= 0.45


def extract_xml_text(raw: bytes) -> str:
    try:
        root = ET.fromstring(raw)
    except Exception:
        return ''

    txt = []
    for node in root.iter():
        tag = str(getattr(node, 'tag', ''))
        if node.text and (tag.endswith('}t') or tag.endswith('}p') or tag.endswith('}span')):
            value = re.sub(r'\s+', ' ', str(node.text)).strip()
            if value:
                txt.append(value)
    return ' '.join(txt)


def read_zip_xml_text(path: str, path_prefixes):
    parts = []
    try:
        with zipfile.ZipFile(path, 'r') as z:
            xml_files = [
                n for n in z.namelist()
                if n.endswith('.xml') and any(n.startswith(prefix) for prefix in path_prefixes)
            ]
            for xml_name in xml_files:
                try:
                    content = extract_xml_text(z.read(xml_name))
                    if content:
                        parts.append(content)
                except Exception:
                    continue
    except zipfile.BadZipFile:
        return ''
    return '\n'.join(parts)


def read_docx_text(path: str) -> str:
    return read_zip_xml_text(path, ['word/'])


def read_xlsx_text(path: str) -> str:
    rows = []
    try:
        with zipfile.ZipFile(path, 'r') as z:
            shared_strings = []
            if 'xl/sharedStrings.xml' in z.namelist():
                try:
                    root = ET.fromstring(z.read('xl/sharedStrings.xml'))
                    for node in root.iter():
                        if str(getattr(node, 'tag', '')).endswith('}t') and node.text:
                            shared_strings.append(str(node.text))
                except Exception:
                    shared_strings = []

            sheet_files = [n for n in z.namelist() if n.startswith('xl/worksheets/') and n.endswith('.xml')]
            for sheet_name in sheet_files:
                try:
                    root = ET.fromstring(z.read(sheet_name))
                except Exception:
                    continue
                for c in root.iter():
                    if not str(getattr(c, 'tag', '')).endswith('}c'):
                        continue

                    ctype = str(c.attrib.get('t', '')).strip().lower()
                    value = ''

                    if ctype == 'inlineStr':
                        for t in c.iter():
                            if str(getattr(t, 'tag', '')).endswith('}t') and t.text:
                                value = str(t.text)
                                break
                    else:
                        v = None
                        for child in c:
                            if str(getattr(child, 'tag', '')).endswith('}v'):
                                v = child
                                break
                        if v is not None and v.text is not None:
                            raw = str(v.text)
                            if ctype == 's':
                                try:
                                    idx = int(raw)
                                    if 0 <= idx < len(shared_strings):
                                        value = shared_strings[idx]
                                except Exception:
                                    value = raw
                            else:
                                value = raw

                    value = re.sub(r'\s+', ' ', str(value)).strip()
                    if value:
                        rows.append(value)
    except zipfile.BadZipFile:
        return ''
    return '\n'.join(rows)


def read_rtf_text(path: str) -> str:
    raw = read_text_file(path)
    t = re.sub(r'\\[a-zA-Z]+\d* ?', ' ', raw)
    t = t.replace('{', ' ').replace('}', ' ')
    t = re.sub(r'\\\'([0-9a-fA-F]{2})', lambda m: bytes([int(m.group(1), 16)]).decode('latin1', errors='ignore'), t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def read_binary_strings(path: str, min_len: int = 4, max_lines: int = 500):
    try:
        raw = open(path, 'rb').read()
    except Exception:
        return []

    pattern = rb'[\x20-\x7E]{' + str(min_len).encode('ascii') + rb',}'
    chunks = re.findall(pattern, raw)
    out = []
    seen = set()
    for c in chunks:
        s = safe_decode_bytes(c)
        s = re.sub(r'\s+', ' ', s).strip()
        if len(s) < min_len:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s[:220])
        if len(out) >= max_lines:
            break
    return out


def read_pdf_text(path: str) -> str:
    # Lightweight PDF text extraction without external dependencies.
    try:
        raw = open(path, 'rb').read()
    except Exception:
        return ''

    snippets = []
    for m in re.finditer(rb'\(([^()]{3,600})\)', raw):
        piece = m.group(1)
        piece = piece.replace(b'\\n', b' ').replace(b'\\r', b' ').replace(b'\\t', b' ')
        piece = re.sub(rb'\\[0-7]{1,3}', b' ', piece)
        text = safe_decode_bytes(piece)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) >= 4:
            snippets.append(text)

    if len(snippets) < 6:
        snippets.extend(read_binary_strings(path, min_len=5, max_lines=350))

    dedup = []
    seen = set()
    for s in snippets:
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        dedup.append(s)
        if len(dedup) >= 1200:
            break

    clean = [s for s in dedup if is_readable_text_line(s)]
    return '\n'.join(clean)


def read_text_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def extract_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        return read_docx_text(path)
    if ext in {'.xlsx', '.ods'}:
        return read_xlsx_text(path)
    if ext in {'.pptx', '.odt'}:
        return read_zip_xml_text(path, ['ppt/', 'content.xml'])
    if ext == '.pdf':
        return read_pdf_text(path)
    if ext == '.rtf':
        return read_rtf_text(path)
    if ext in {'.doc', '.xls'}:
        return '\n'.join(read_binary_strings(path, min_len=5, max_lines=400))
    if ext in TEXT_EXTENSIONS:
        return read_text_file(path)
    return ''


def normalize_phone_digits(value: str) -> str:
    digits = re.sub(r'\D', '', str(value or ''))
    if not digits:
        return ''
    if len(digits) >= 13 and digits.startswith('55'):
        return digits[:13]
    if len(digits) == 12 and digits.startswith('55'):
        return digits
    if len(digits) == 11:
        return f'55{digits}'
    if len(digits) == 10:
        return f'55{digits}'
    return digits


def read_xlsx_rows(path: str, max_rows: int = 5000):
    rows = []
    with zipfile.ZipFile(path, 'r') as z:
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            try:
                root = ET.fromstring(z.read('xl/sharedStrings.xml'))
                for node in root.iter():
                    if str(getattr(node, 'tag', '')).endswith('}t') and node.text:
                        shared_strings.append(str(node.text))
            except Exception:
                shared_strings = []

        sheet_files = [n for n in z.namelist() if n.startswith('xl/worksheets/') and n.endswith('.xml')]
        if not sheet_files:
            return rows

        root = ET.fromstring(z.read(sheet_files[0]))
        for row in root.iter():
            if not str(getattr(row, 'tag', '')).endswith('}row'):
                continue

            values = []
            for c in row:
                if not str(getattr(c, 'tag', '')).endswith('}c'):
                    continue

                ctype = str(c.attrib.get('t', '')).strip().lower()
                value = ''

                if ctype == 'inlineStr':
                    for t in c.iter():
                        if str(getattr(t, 'tag', '')).endswith('}t') and t.text:
                            value = str(t.text)
                            break
                else:
                    v = None
                    for child in c:
                        if str(getattr(child, 'tag', '')).endswith('}v'):
                            v = child
                            break
                    if v is not None and v.text is not None:
                        raw = str(v.text)
                        if ctype == 's':
                            try:
                                idx = int(raw)
                                if 0 <= idx < len(shared_strings):
                                    value = shared_strings[idx]
                            except Exception:
                                value = raw
                        else:
                            value = raw

                values.append(compact_line(value))

            if any(values):
                rows.append(values)
            if len(rows) >= max_rows:
                break

    return rows


def write_ignored_contacts_ml_file(entries):
    os.makedirs(ML_DIR, exist_ok=True)
    lines = [
        'LISTA DE CONTATOS IGNORADOS',
        '',
        'Objetivo:',
        'Estes contatos devem ser ignorados pelo atendimento automatico do WhatsApp e nao devem receber resposta automatica.',
        '',
        f'Total de contatos ativos: {len(entries)}',
        '',
        'Contatos ativos:',
    ]
    for entry in entries:
        number = str(entry.get('number', '')).strip()
        name = compact_line(entry.get('contact_name', ''))
        label = f'- {name} | {number}' if name else f'- {number}'
        lines.append(label)

    with open(IGNORED_CONTACTS_ML_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines).strip() + '\n')


def ingest_ignored_contacts_source(crm_conn):
    crm_conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS ignored_contacts_registry (
          number TEXT PRIMARY KEY,
          raw_value TEXT,
          contact_name TEXT,
          source_file TEXT,
          source_hash TEXT,
          last_modified TEXT,
          imported_at TEXT,
          status TEXT DEFAULT 'active'
        );
        '''
    )

    if not os.path.isfile(IGNORED_CONTACTS_FILE):
        crm_conn.execute("UPDATE ignored_contacts_registry SET status='inactive' WHERE status='active'")
        if os.path.isfile(IGNORED_CONTACTS_ML_FILE):
            try:
                os.remove(IGNORED_CONTACTS_ML_FILE)
            except OSError:
                pass
        return {
            'sourceFile': IGNORED_CONTACTS_FILE,
            'sourceExists': False,
            'indexedNow': 0,
            'activeContacts': 0,
            'contacts': [],
        }

    rows = read_xlsx_rows(IGNORED_CONTACTS_FILE, max_rows=10000)
    source_hash = sha_file(IGNORED_CONTACTS_FILE)
    last_modified = datetime.fromtimestamp(os.path.getmtime(IGNORED_CONTACTS_FILE), tz=timezone.utc).isoformat()
    now = now_iso()
    seen_numbers = set()
    indexed_now = 0

    for idx, row in enumerate(rows):
        if idx == 0:
            continue
        raw_value = str(row[0] if len(row) >= 1 else '').strip()
        contact_name = compact_line(row[1] if len(row) >= 2 else '')
        number = normalize_phone_digits(raw_value)
        if len(number) < 10:
            continue

        seen_numbers.add(number)
        existing = crm_conn.execute(
            'SELECT raw_value, contact_name, source_hash, status FROM ignored_contacts_registry WHERE number = ?',
            (number,)
        ).fetchone()

        if existing and existing['raw_value'] == raw_value and existing['contact_name'] == contact_name and existing['source_hash'] == source_hash and existing['status'] == 'active':
            continue

        crm_conn.execute(
            '''
            INSERT INTO ignored_contacts_registry (number, raw_value, contact_name, source_file, source_hash, last_modified, imported_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
            ON CONFLICT(number) DO UPDATE SET
              raw_value=excluded.raw_value,
              contact_name=excluded.contact_name,
              source_file=excluded.source_file,
              source_hash=excluded.source_hash,
              last_modified=excluded.last_modified,
              imported_at=excluded.imported_at,
              status='active'
            ''',
            (number, raw_value, contact_name, os.path.basename(IGNORED_CONTACTS_FILE), source_hash, last_modified, now)
        )
        indexed_now += 1

    if seen_numbers:
        placeholders = ','.join(['?'] * len(seen_numbers))
        crm_conn.execute(
            f"UPDATE ignored_contacts_registry SET status='inactive' WHERE status='active' AND number NOT IN ({placeholders})",
            tuple(seen_numbers)
        )
    else:
        crm_conn.execute("UPDATE ignored_contacts_registry SET status='inactive' WHERE status='active'")

    active_rows = crm_conn.execute(
        '''
        SELECT number, raw_value, contact_name, imported_at
        FROM ignored_contacts_registry
        WHERE status='active'
        ORDER BY contact_name COLLATE NOCASE ASC, number ASC
        '''
    ).fetchall()

    entries = [
        {
            'number': r['number'],
            'rawValue': r['raw_value'],
            'contact_name': r['contact_name'],
            'importedAt': r['imported_at'],
        }
        for r in active_rows
    ]

    write_ignored_contacts_ml_file(entries)

    return {
        'sourceFile': IGNORED_CONTACTS_FILE,
        'sourceExists': True,
        'indexedNow': indexed_now,
        'activeContacts': len(entries),
        'contacts': entries[:300],
    }


def build_highlights(text: str, max_lines: int = 18):
    if not text:
        return []

    lines = []
    for line in text.splitlines():
        clean = re.sub(r'\s+', ' ', line).strip(' -\t')
        if len(clean) >= 35 and is_readable_text_line(clean):
            lines.append(clean)

    if len(lines) < max_lines:
        merged = re.sub(r'\s+', ' ', text).strip()
        for sentence in re.split(r'(?<=[\.!?])\s+', merged):
            clean = sentence.strip()
            if 40 <= len(clean) <= 220 and is_readable_text_line(clean):
                lines.append(clean)

    seen = set()
    unique = []
    for line in lines:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(line[:220])
        if len(unique) >= max_lines:
            break

    return unique


def build_rag_chunks(text: str, max_chunks: int = 24, chunk_chars: int = 520):
    if not text:
        return []

    raw_parts = []
    for block in re.split(r'\n{2,}', text):
        clean = re.sub(r'\s+', ' ', str(block or '')).strip(' -\t')
        if len(clean) >= 80 and is_readable_text_line(clean):
            raw_parts.append(clean)

    if not raw_parts:
        merged = re.sub(r'\s+', ' ', str(text or '')).strip()
        sentences = [s.strip() for s in re.split(r'(?<=[\.!?])\s+', merged) if s.strip()]
        current = []
        current_len = 0
        for sentence in sentences:
            if not is_readable_text_line(sentence):
                continue
            if current_len + len(sentence) + 1 > chunk_chars and current:
                raw_parts.append(' '.join(current).strip())
                current = [sentence]
                current_len = len(sentence)
            else:
                current.append(sentence)
                current_len += len(sentence) + 1
        if current:
            raw_parts.append(' '.join(current).strip())

    chunks = []
    seen = set()
    for part in raw_parts:
        clean = re.sub(r'\s+', ' ', str(part or '')).strip()
        if len(clean) < 80:
            continue
        if len(clean) > chunk_chars:
            start = 0
            while start < len(clean):
                piece = clean[start:start + chunk_chars].strip()
                if len(piece) >= 80 and is_readable_text_line(piece):
                    key = piece.lower()
                    if key not in seen:
                        seen.add(key)
                        chunks.append(piece)
                if len(chunks) >= max_chunks:
                    break
                start += max(280, int(chunk_chars * 0.65))
        else:
            key = clean.lower()
            if key not in seen:
                seen.add(key)
                chunks.append(clean)
        if len(chunks) >= max_chunks:
            break

    return chunks[:max_chunks]


def compact_line(value: str) -> str:
    return re.sub(r'\s+', ' ', str(value or '')).strip(' -\t')


def extract_keywords_from_text(text: str, max_terms: int = 10):
    tokens = normalize_tokens(text)
    if not tokens:
        return []
    counter = Counter(tokens)
    return [t for t, _ in counter.most_common(max_terms)]


def detect_mandatory_script(file_name: str, text: str, highlights):
    source = f"{file_name}\n{text or ''}".lower()

    markers = [
        'script mandatorio', 'script obrigatório', 'script obrigatorio',
        'roteiro mandatorio', 'roteiro obrigatório', 'roteiro obrigatorio',
        'pergunta por pergunta', 'so avanca', 'só avança',
        'nao avanca', 'não avança', 'requisito para seguir',
        'obrigatorio para seguir', 'obrigatório para seguir',
        'fluxo de triagem'
    ]

    hits = sum(1 for m in markers if m in source)
    explicit = any(x in source for x in ['[mandatorio]', '[obrigatorio]', 'script_mandatorio: sim'])
    is_mandatory = explicit or hits >= 2
    if not is_mandatory:
        return None

    objective = ''
    m_obj = re.search(r'(objetivo|foco|finalidade)\s*[:\-]\s*(.{15,220})', text or '', flags=re.IGNORECASE)
    if m_obj:
        objective = compact_line(m_obj.group(2))

    if not objective and highlights:
        objective = compact_line(highlights[0])

    questions = []
    for line in (text or '').splitlines():
        clean = compact_line(line)
        if 8 <= len(clean) <= 180 and clean.endswith('?'):
            questions.append(clean)

    if len(questions) < 2:
        for h in highlights or []:
            clean = compact_line(h)
            if clean.endswith('?'):
                questions.append(clean)

    dedup_q = []
    seen = set()
    for q in questions:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup_q.append(q[:180])
        if len(dedup_q) >= 12:
            break

    keyword_base = '\n'.join([
        file_name or '',
        objective or '',
        '\n'.join(dedup_q[:6]),
        (text or '')[:1600],
    ])
    keywords = extract_keywords_from_text(keyword_base, max_terms=10)

    return {
        'mandatory': True,
        'objective': objective[:220] if objective else '',
        'questions': dedup_q[:10],
        'keywords': keywords[:10],
        'enforcement': 'preserve_objective'
    }


def ingest_machine_learning_folder(crm_conn):
    crm_conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS knowledge_documents (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          file_path TEXT UNIQUE,
          file_name TEXT,
          extension TEXT,
          content_hash TEXT,
          chars_count INTEGER,
          last_modified TEXT,
          indexed_at TEXT,
          highlights_json TEXT,
          chunks_json TEXT,
          keywords_json TEXT,
          mandatory_json TEXT,
          status TEXT DEFAULT 'active'
        );
        '''
    )

    # Backward compatible columns for older DBs.
    try:
        crm_conn.execute('ALTER TABLE knowledge_documents ADD COLUMN chunks_json TEXT')
    except sqlite3.OperationalError:
        pass

    try:
        crm_conn.execute('ALTER TABLE knowledge_documents ADD COLUMN keywords_json TEXT')
    except sqlite3.OperationalError:
        pass

    try:
        crm_conn.execute('ALTER TABLE knowledge_documents ADD COLUMN mandatory_json TEXT')
    except sqlite3.OperationalError:
        pass

    if not os.path.isdir(ML_DIR):
        return {
            'folder': ML_DIR,
            'folderExists': False,
            'indexedNow': 0,
            'activeDocuments': 0,
            'highlights': [],
            'documents': [],
            'mandatoryDirectives': []
        }

    now = now_iso()
    indexed_now = 0
    seen_paths = set()

    for root, _, files in os.walk(ML_DIR):
        for fname in files:
            full_path = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ML_EXTENSIONS:
                continue

            rel_path = os.path.relpath(full_path, '/work') if full_path.startswith('/work') else full_path
            seen_paths.add(rel_path)
            file_hash = sha_file(full_path)
            last_modified = datetime.fromtimestamp(os.path.getmtime(full_path), tz=timezone.utc).isoformat()

            existing = crm_conn.execute(
                'SELECT content_hash, chunks_json FROM knowledge_documents WHERE file_path = ?',
                (rel_path,)
            ).fetchone()

            if existing and existing[0] == file_hash and str(existing[1] or '').strip():
                continue

            text = extract_text_from_file(full_path)
            highlights = build_highlights(text, max_lines=18)
            chunks = build_rag_chunks(text, max_chunks=24, chunk_chars=520)
            keywords = extract_keywords_from_text(text, max_terms=16)
            mandatory_meta = detect_mandatory_script(fname, text, highlights)
            chars_count = len(text or '')

            crm_conn.execute(
                '''
                INSERT INTO knowledge_documents (file_path, file_name, extension, content_hash, chars_count, last_modified, indexed_at, highlights_json, chunks_json, keywords_json, mandatory_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
                ON CONFLICT(file_path) DO UPDATE SET
                  file_name=excluded.file_name,
                  extension=excluded.extension,
                  content_hash=excluded.content_hash,
                  chars_count=excluded.chars_count,
                  last_modified=excluded.last_modified,
                  indexed_at=excluded.indexed_at,
                  highlights_json=excluded.highlights_json,
                  chunks_json=excluded.chunks_json,
                  keywords_json=excluded.keywords_json,
                  mandatory_json=excluded.mandatory_json,
                  status='active'
                ''',
                (
                    rel_path, fname, ext, file_hash, chars_count, last_modified, now,
                    json.dumps(highlights, ensure_ascii=False),
                    json.dumps(chunks, ensure_ascii=False),
                    json.dumps(keywords, ensure_ascii=False),
                    json.dumps(mandatory_meta or {}, ensure_ascii=False),
                )
            )
            indexed_now += 1

    if seen_paths:
        placeholders = ','.join(['?'] * len(seen_paths))
        crm_conn.execute(
            f"UPDATE knowledge_documents SET status='inactive' WHERE status='active' AND file_path NOT IN ({placeholders})",
            tuple(seen_paths)
        )
    else:
        crm_conn.execute("UPDATE knowledge_documents SET status='inactive' WHERE status='active'")

    docs = crm_conn.execute(
        '''
        SELECT file_path, file_name, extension, chars_count, indexed_at, highlights_json, chunks_json, keywords_json, mandatory_json
        FROM knowledge_documents
        WHERE status='active'
        ORDER BY indexed_at DESC
        LIMIT 30
        '''
    ).fetchall()

    highlights = []
    doc_list = []
    mandatory_directives = []
    for d in docs:
        doc_highlights = []
        doc_chunks = []
        doc_keywords = []
        mandatory_meta = {}
        try:
            doc_highlights = json.loads(d['highlights_json'] or '[]')
        except Exception:
            doc_highlights = []
        try:
            doc_chunks = json.loads(d['chunks_json'] or '[]')
        except Exception:
            doc_chunks = []
        try:
            doc_keywords = json.loads(d['keywords_json'] or '[]')
        except Exception:
            doc_keywords = []
        try:
            mandatory_meta = json.loads(d['mandatory_json'] or '{}')
        except Exception:
            mandatory_meta = {}

        doc_list.append({
            'filePath': d['file_path'],
            'fileName': d['file_name'],
            'extension': d['extension'],
            'charsCount': int(d['chars_count'] or 0),
            'indexedAt': d['indexed_at'],
            'keywords': doc_keywords[:12],
            'ragChunks': doc_chunks[:10],
            'mandatory': bool(mandatory_meta.get('mandatory')),
        })

        for h in doc_highlights[:4]:
            if not is_readable_text_line(h):
                continue
            highlights.append(f"[{d['file_name']}] {str(h)[:220]}")

        if mandatory_meta.get('mandatory'):
            mandatory_directives.append({
                'fileName': d['file_name'],
                'filePath': d['file_path'],
                'objective': str(mandatory_meta.get('objective', ''))[:220],
                'questions': list(mandatory_meta.get('questions') or [])[:10],
                'keywords': list(mandatory_meta.get('keywords') or [])[:10],
                'enforcement': str(mandatory_meta.get('enforcement', 'preserve_objective')),
            })

    return {
        'folder': ML_DIR,
        'folderExists': True,
        'indexedNow': indexed_now,
        'activeDocuments': len(doc_list),
        'highlights': highlights[:25],
        'documents': doc_list[:15],
        'mandatoryDirectives': mandatory_directives[:8],
    }


n8n = sqlite3.connect(N8N_DB)
n8n.row_factory = sqlite3.Row
crm = sqlite3.connect(CRM_DB)
crm.row_factory = sqlite3.Row

n8n.execute('PRAGMA busy_timeout=30000')
crm.execute('PRAGMA journal_mode=WAL')
crm.execute('PRAGMA synchronous=NORMAL')

crm.executescript(
    '''
    CREATE TABLE IF NOT EXISTS leads (
      number TEXT PRIMARY KEY,
      push_name TEXT,
      customer_name TEXT,
      informed_phone TEXT,
      city TEXT,
      instagram TEXT,
      company_legal_name TEXT,
      company_cnpj TEXT,
      company_cnpj_situation TEXT,
      cnpj_ativo_answer TEXT,
      loja_fisica_answer TEXT,
      book_sales_access TEXT,
      revenda_script_stage INTEGER,
      revenda_script_completed INTEGER,
      first_seen_at TEXT,
      last_product_focus TEXT,
      last_product_category TEXT,
      last_inbound_text TEXT,
      last_reply_text TEXT,
      lead_stage TEXT,
      last_intent TEXT,
      last_confidence REAL,
      awaiting_human INTEGER,
      notes TEXT,
      next_step TEXT,
      last_seen_at TEXT,
      updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS interactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      interaction_hash TEXT UNIQUE,
      number TEXT,
      direction TEXT,
      text TEXT,
      intent TEXT,
      confidence REAL,
      needs_human INTEGER,
      event_ts TEXT,
      created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS learning_backlog (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      backlog_hash TEXT UNIQUE,
      number TEXT,
      push_name TEXT,
      intent TEXT,
      confidence REAL,
      model_json_parsed INTEGER,
      customer_question TEXT,
      model_raw TEXT,
      source_created_at TEXT,
      status TEXT DEFAULT 'open',
      created_at TEXT,
      updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS knowledge_rules (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      intent TEXT,
      pattern TEXT,
      response_guidance TEXT,
      priority INTEGER DEFAULT 50,
      active INTEGER DEFAULT 1,
      source TEXT DEFAULT 'auto_cycle',
      created_at TEXT,
      updated_at TEXT,
      UNIQUE(intent, pattern, source)
    );

    CREATE TABLE IF NOT EXISTS knowledge_cycles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_at TEXT,
      new_leads INTEGER,
      new_interactions INTEGER,
      new_backlog INTEGER,
      open_backlog INTEGER,
      generated_rules INTEGER,
      ml_docs_indexed INTEGER,
      ml_docs_active INTEGER,
      notes TEXT
    );

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
    );
    '''
)

crm.execute('DROP VIEW IF EXISTS b2b_eligible_leads')
crm.execute(
    '''
    CREATE VIEW b2b_eligible_leads AS
    SELECT l.*
    FROM leads l
    LEFT JOIN b2b_reporting_exclusions x
      ON x.number = l.number AND x.active = 1
    WHERE x.number IS NULL
    '''
)

# Backward-compatible column add if table already existed before customer_name.
try:
    crm.execute('ALTER TABLE leads ADD COLUMN customer_name TEXT')
except sqlite3.OperationalError:
    pass

for alter_sql in [
    'ALTER TABLE leads ADD COLUMN informed_phone TEXT',
    'ALTER TABLE leads ADD COLUMN city TEXT',
    'ALTER TABLE leads ADD COLUMN instagram TEXT',
    'ALTER TABLE leads ADD COLUMN company_legal_name TEXT',
    'ALTER TABLE leads ADD COLUMN company_cnpj TEXT',
    'ALTER TABLE leads ADD COLUMN company_cnpj_situation TEXT',
    'ALTER TABLE leads ADD COLUMN cnpj_ativo_answer TEXT',
    'ALTER TABLE leads ADD COLUMN loja_fisica_answer TEXT',
    'ALTER TABLE leads ADD COLUMN book_sales_access TEXT',
    'ALTER TABLE leads ADD COLUMN revenda_script_stage INTEGER',
    'ALTER TABLE leads ADD COLUMN revenda_script_completed INTEGER',
    'ALTER TABLE leads ADD COLUMN first_seen_at TEXT',
    'ALTER TABLE leads ADD COLUMN last_product_focus TEXT',
    'ALTER TABLE leads ADD COLUMN last_product_category TEXT',
    'ALTER TABLE leads ADD COLUMN last_inbound_text TEXT',
    'ALTER TABLE leads ADD COLUMN last_reply_text TEXT',
]:
    try:
        crm.execute(alter_sql)
    except sqlite3.OperationalError:
        pass

try:
    crm.execute('ALTER TABLE knowledge_cycles ADD COLUMN ml_docs_indexed INTEGER')
except sqlite3.OperationalError:
    pass

try:
    crm.execute('ALTER TABLE knowledge_cycles ADD COLUMN ml_docs_active INTEGER')
except sqlite3.OperationalError:
    pass

ignored_contacts_data = ingest_ignored_contacts_source(crm)
reporting_excluded_numbers = crm_reporting_excluded_numbers()


def upsert_b2b_exclusion(number, reason, source, profile, now_value):
    crm.execute('DELETE FROM leads WHERE number = ?', (number,))
    crm.execute(
        '''
        INSERT INTO b2b_reporting_exclusions (
          number, exclusion_reason, source, push_name, customer_name,
          last_inbound_text, last_seen_at, created_at, updated_at, active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(number) DO UPDATE SET
          exclusion_reason=excluded.exclusion_reason,
          source=excluded.source,
          push_name=excluded.push_name,
          customer_name=excluded.customer_name,
          last_inbound_text=excluded.last_inbound_text,
          last_seen_at=excluded.last_seen_at,
          updated_at=excluded.updated_at,
          active=1
        ''',
        (
            number,
            reason,
            source,
            profile.get('pushName', ''),
            profile.get('customerName', ''),
            str(profile.get('lastInboundText', ''))[:600],
            profile.get('lastSeenAt', now_value),
            now_value,
            now_value,
        ),
    )


def profile_exclusion_reason(number, profile):
    if number in reporting_excluded_numbers:
        return 'numero_interno_teste_ou_bloqueado'
    if is_test_artifact_text(
        profile.get('pushName', ''),
        profile.get('customerName', ''),
        profile.get('lastInboundText', ''),
        profile.get('lastReplyText', ''),
    ):
        return 'artefato_teste_homologacao'
    return ''

row = n8n.execute('SELECT staticData FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,)).fetchone()
if not row:
    raise RuntimeError(f'Workflow {WORKFLOW_ID} not found')

static_data_raw = row['staticData'] or '{}'
static_data_obj = json.loads(static_data_raw)
global_data = static_data_obj.get('global', {})

profiles = global_data.get('customerProfiles', {})
history = global_data.get('customerHistory', {})
backlog = global_data.get('learningBacklog', [])

now = now_iso()
new_leads = 0
new_interactions = 0
new_backlog = 0

for number, p in profiles.items():
    number = str(number or '').strip()
    if not number:
        continue

    reporting_exclusion_reason = profile_exclusion_reason(number, p)
    if reporting_exclusion_reason:
        upsert_b2b_exclusion(number, reporting_exclusion_reason, 'crm_auto_triage', p, now)
        continue

    revenda_script = p.get('revendaScript', {}) if isinstance(p.get('revendaScript', {}), dict) else {}
    revenda_data = revenda_script.get('data', {}) if isinstance(revenda_script.get('data', {}), dict) else {}
    disqualified_reason = str(revenda_script.get('disqualifiedReason', '') or '').strip()
    exclude_from_b2b_sheet = disqualified_reason in EXCLUDED_B2B_REASONS

    if exclude_from_b2b_sheet:
        crm.execute('DELETE FROM leads WHERE number = ?', (number,))
        crm.execute(
            '''
            INSERT INTO b2b_reporting_exclusions (
              number, exclusion_reason, source, push_name, customer_name,
              last_inbound_text, last_seen_at, created_at, updated_at, active
            )
            VALUES (?, ?, 'revenda_triage', ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(number) DO UPDATE SET
              exclusion_reason=excluded.exclusion_reason,
              source=excluded.source,
              push_name=excluded.push_name,
              customer_name=excluded.customer_name,
              last_inbound_text=excluded.last_inbound_text,
              last_seen_at=excluded.last_seen_at,
              updated_at=excluded.updated_at,
              active=1
            ''',
            (
                number,
                disqualified_reason,
                p.get('pushName', ''),
                p.get('customerName', ''),
                str(p.get('lastInboundText', ''))[:600],
                p.get('lastSeenAt', now),
                now,
                now,
            ),
        )
        continue

    crm.execute('DELETE FROM b2b_reporting_exclusions WHERE number = ?', (number,))

    existing = crm.execute('SELECT 1 FROM leads WHERE number = ?', (number,)).fetchone()
    if not existing:
        new_leads += 1

    crm.execute(
        '''
        INSERT INTO leads (
          number, push_name, customer_name, informed_phone, city, instagram,
          company_legal_name, company_cnpj, company_cnpj_situation,
          cnpj_ativo_answer, loja_fisica_answer, book_sales_access,
          revenda_script_stage, revenda_script_completed, first_seen_at,
          last_product_focus, last_product_category, last_inbound_text, last_reply_text,
          lead_stage, last_intent, last_confidence, awaiting_human, notes, next_step, last_seen_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(number) DO UPDATE SET
          push_name=excluded.push_name,
          customer_name=excluded.customer_name,
          informed_phone=excluded.informed_phone,
          city=excluded.city,
          instagram=excluded.instagram,
          company_legal_name=excluded.company_legal_name,
          company_cnpj=excluded.company_cnpj,
          company_cnpj_situation=excluded.company_cnpj_situation,
          cnpj_ativo_answer=excluded.cnpj_ativo_answer,
          loja_fisica_answer=excluded.loja_fisica_answer,
          book_sales_access=excluded.book_sales_access,
          revenda_script_stage=excluded.revenda_script_stage,
          revenda_script_completed=excluded.revenda_script_completed,
          first_seen_at=COALESCE(leads.first_seen_at, excluded.first_seen_at),
          last_product_focus=excluded.last_product_focus,
          last_product_category=excluded.last_product_category,
          last_inbound_text=excluded.last_inbound_text,
          last_reply_text=excluded.last_reply_text,
          lead_stage=excluded.lead_stage,
          last_intent=excluded.last_intent,
          last_confidence=excluded.last_confidence,
          awaiting_human=CASE
            WHEN leads.next_step='follow_up_humano_pendente' THEN 1
            ELSE excluded.awaiting_human
          END,
          notes=CASE
            WHEN leads.next_step='follow_up_humano_pendente'
              AND instr(coalesce(leads.notes, ''), '[auto_followup:') > 0
            THEN leads.notes
            ELSE excluded.notes
          END,
          next_step=CASE
            WHEN leads.next_step='follow_up_humano_pendente' THEN leads.next_step
            ELSE excluded.next_step
          END,
          last_seen_at=excluded.last_seen_at,
          updated_at=excluded.updated_at
        ''',
        (
            number,
            p.get('pushName', ''),
            p.get('customerName', ''),
            revenda_data.get('telefone', ''),
            revenda_data.get('cidade', ''),
            revenda_data.get('instagram', ''),
            p.get('companyLegalName', ''),
            p.get('companyCnpj', ''),
            p.get('companyCnpjSituation', ''),
            revenda_data.get('cnpjAtivo', ''),
            revenda_data.get('lojaFisica', ''),
            p.get('bookSalesAccess', ''),
            int(revenda_script.get('stage') or 0),
            1 if revenda_script.get('completed') else 0,
            p.get('firstSeenAt', p.get('lastSeenAt', now)),
            p.get('lastProductFocus', ''),
            p.get('lastProductCategory', ''),
            str(p.get('lastInboundText', ''))[:600],
            str(p.get('lastReplyText', ''))[:600],
            p.get('leadStage', 'novo'),
            p.get('lastIntent', 'geral'),
            float(p.get('lastConfidence') or 0),
            1 if p.get('awaitingHuman') else 0,
            p.get('notes', ''),
            p.get('nextStep', ''),
            p.get('lastSeenAt', now),
            now,
        ),
    )

for number, events in history.items():
    number = str(number or '').strip()
    if not number:
        continue

    for e in (events or []):
        text = str(e.get('text', '')).strip()
        ts = str(e.get('timestamp', now))
        direction = 'inbound' if e.get('role') == 'customer' else 'outbound'
        h = sha_text(f'{number}|{direction}|{text}|{ts}')
        cur = crm.execute(
            '''
            INSERT OR IGNORE INTO interactions (interaction_hash, number, direction, text, intent, confidence, needs_human, event_ts, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                h,
                number,
                direction,
                text,
                str(e.get('intent', '')),
                float(e.get('confidence') or 0),
                1 if e.get('needsHuman') else 0,
                ts,
                now,
            ),
        )
        if cur.rowcount:
            new_interactions += 1

for item in (backlog or []):
    number = str(item.get('number', '')).strip()
    question = str(item.get('customerQuestion', '')).strip()
    intent = str(item.get('intent', 'geral')).strip() or 'geral'
    created = str(item.get('createdAt', now))
    h = sha_text(f'{number}|{intent}|{question}|{created}')

    cur = crm.execute(
        '''
        INSERT OR IGNORE INTO learning_backlog
          (backlog_hash, number, push_name, intent, confidence, model_json_parsed, customer_question, model_raw, source_created_at, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
        ''',
        (
            h,
            number,
            str(item.get('pushName', '')),
            intent,
            float(item.get('confidence') or 0),
            1 if item.get('modelJsonParsed') else 0,
            question,
            str(item.get('modelRaw', ''))[:3000],
            created,
            now,
            now,
        ),
    )
    if cur.rowcount:
        new_backlog += 1


def auto_triage_learning_backlog(now_value):
    updates = {'empty': 0, 'test_artifact': 0, 'duplicate': 0}

    cur = crm.execute(
        '''
        UPDATE learning_backlog
        SET status='auto_closed_empty', updated_at=?
        WHERE status='open' AND trim(coalesce(customer_question, '')) = ''
        ''',
        (now_value,),
    )
    updates['empty'] = cur.rowcount

    rows = crm.execute(
        '''
        SELECT id, number, push_name, intent, customer_question
        FROM learning_backlog
        WHERE status='open'
        '''
    ).fetchall()
    test_ids = [
        int(r['id'])
        for r in rows
        if digits_only(r['number']) in reporting_excluded_numbers
        or is_test_artifact_text(r['number'], r['push_name'], r['customer_question'])
    ]
    if test_ids:
        placeholders = ','.join('?' for _ in test_ids)
        cur = crm.execute(
            f'''
            UPDATE learning_backlog
            SET status='auto_closed_test_artifact', updated_at=?
            WHERE id IN ({placeholders})
            ''',
            (now_value, *test_ids),
        )
        updates['test_artifact'] = cur.rowcount

    rows = crm.execute(
        '''
        SELECT id, number, intent, customer_question, source_created_at
        FROM learning_backlog
        WHERE status='open' AND trim(coalesce(customer_question, '')) <> ''
        ORDER BY source_created_at DESC, id DESC
        '''
    ).fetchall()
    by_key = {}
    for r in rows:
        key = (str(r['intent'] or '').strip(), normalized_question_key(r['customer_question']))
        if not key[1]:
            continue
        by_key.setdefault(key, []).append(r)

    duplicate_ids = []
    for items in by_key.values():
        if len(items) <= 1:
            continue
        ranked = sorted(
            items,
            key=lambda r: (
                1 if digits_only(r['number']) else 0,
                str(r['source_created_at'] or ''),
                int(r['id']),
            ),
            reverse=True,
        )
        duplicate_ids.extend(int(r['id']) for r in ranked[1:])

    if duplicate_ids:
        placeholders = ','.join('?' for _ in duplicate_ids)
        cur = crm.execute(
            f'''
            UPDATE learning_backlog
            SET status='auto_closed_duplicate', updated_at=?
            WHERE id IN ({placeholders})
            ''',
            (now_value, *duplicate_ids),
        )
        updates['duplicate'] = cur.rowcount

    return updates


backlog_triage = auto_triage_learning_backlog(now)


def queue_open_learning_backlog_for_review(now_value):
    queue_hours = int(os.getenv('LEARNING_BACKLOG_AUTO_QUEUE_HOURS', '12'))
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=queue_hours)).isoformat().replace('+00:00', 'Z')
    reason = f'open_backlog_sla_{queue_hours}h'

    crm.execute(
        '''
        CREATE TABLE IF NOT EXISTS learning_backlog_review_audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          backlog_id INTEGER NOT NULL,
          number TEXT,
          previous_status TEXT NOT NULL,
          new_status TEXT NOT NULL,
          reason TEXT NOT NULL,
          source_created_at TEXT,
          created_at TEXT NOT NULL
        )
        '''
    )
    crm.execute(
        '''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_backlog_review_audit_once
        ON learning_backlog_review_audit(backlog_id, reason)
        '''
    )

    rows = crm.execute(
        '''
        SELECT id, number, status, source_created_at
        FROM learning_backlog
        WHERE status='open'
          AND (
            coalesce(source_created_at, '') < ?
            OR trim(coalesce(number, '')) = ''
          )
        ORDER BY source_created_at ASC, id ASC
        ''',
        (cutoff,),
    ).fetchall()

    queued = 0
    for row in rows:
        crm.execute(
            '''
            INSERT OR IGNORE INTO learning_backlog_review_audit
              (backlog_id, number, previous_status, new_status, reason, source_created_at, created_at)
            VALUES (?, ?, ?, 'queued_human_review', ?, ?, ?)
            ''',
            (
                int(row['id']),
                str(row['number'] or ''),
                str(row['status'] or ''),
                reason,
                str(row['source_created_at'] or ''),
                now_value,
            ),
        )
        cur = crm.execute(
            '''
            UPDATE learning_backlog
            SET status='queued_human_review',
                updated_at=?
            WHERE id=? AND status='open'
            ''',
            (now_value, int(row['id'])),
        )
        queued += cur.rowcount

    return {
        'queueHours': queue_hours,
        'cutoff': cutoff,
        'candidates': len(rows),
        'queued': queued,
    }


backlog_review_queue = queue_open_learning_backlog_for_review(now)


def mark_stale_leads_for_human_followup(now_value):
    stale_hours = int(os.getenv('CRM_STALE_LEAD_HOURS', '24'))
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=stale_hours)).isoformat().replace('+00:00', 'Z')
    reason = f'stale_or_context_missing_{stale_hours}h'

    crm.execute(
        '''
        CREATE TABLE IF NOT EXISTS lead_stale_followup_audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          number TEXT NOT NULL,
          previous_stage TEXT,
          previous_next_step TEXT,
          previous_awaiting_human INTEGER,
          reason TEXT NOT NULL,
          cutoff_at TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        '''
    )
    crm.execute(
        '''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_lead_stale_followup_audit_once
        ON lead_stale_followup_audit(number, reason)
        '''
    )

    candidates = crm.execute(
        '''
        SELECT number, lead_stage, next_step, awaiting_human, last_seen_at,
               last_inbound_text, last_reply_text, notes
        FROM leads
        WHERE lead_stage IN ('novo', 'qualificando')
          AND (
            coalesce(last_seen_at, '') < ?
            OR trim(coalesce(last_inbound_text, '')) = ''
            OR trim(coalesce(last_reply_text, '')) = ''
          )
        ''',
        (cutoff,),
    ).fetchall()

    marked = 0
    marker = f'[auto_followup:{now_value[:19]}]'
    for row in candidates:
        number = str(row['number'] or '').strip()
        if not number:
            continue

        crm.execute(
            '''
            INSERT OR IGNORE INTO lead_stale_followup_audit
              (number, previous_stage, previous_next_step, previous_awaiting_human, reason, cutoff_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                number,
                str(row['lead_stage'] or ''),
                str(row['next_step'] or ''),
                int(row['awaiting_human'] or 0),
                reason,
                cutoff,
                now_value,
            ),
        )

        current_notes = str(row['notes'] or '').strip()
        if '[auto_followup:' not in current_notes:
            note = f'{marker} Lead em novo/qualificando sem avanço ou com contexto incompleto; revisar atendimento humano.'
            next_notes = f'{current_notes} | {note}' if current_notes else note
        else:
            next_notes = current_notes

        cur = crm.execute(
            '''
            UPDATE leads
            SET awaiting_human = 1,
                next_step = 'follow_up_humano_pendente',
                notes = ?,
                updated_at = ?
            WHERE number = ?
              AND (
                awaiting_human IS NULL OR awaiting_human = 0
                OR coalesce(next_step, '') <> 'follow_up_humano_pendente'
              )
            ''',
            (next_notes, now_value, number),
        )
        marked += cur.rowcount

    return {
        'staleHours': stale_hours,
        'cutoff': cutoff,
        'candidates': len(candidates),
        'marked': marked,
    }


stale_lead_followup = mark_stale_leads_for_human_followup(now)

# Index/update external machine learning folder
ml_data = ingest_machine_learning_folder(crm)

# Generate/refresh automatic rules from intent counts
intent_counts = crm.execute(
    "SELECT intent, COUNT(*) c FROM learning_backlog WHERE status='open' GROUP BY intent ORDER BY c DESC"
).fetchall()

generated_rules = 0
for r in intent_counts:
    intent = r['intent']
    c = int(r['c'])
    if intent not in INTENT_RULES:
        continue
    tpl = INTENT_RULES[intent]
    priority = min(99, int(tpl['priority']) + min(c, 5))
    crm.execute(
        '''
        INSERT INTO knowledge_rules (intent, pattern, response_guidance, priority, active, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, 1, 'auto_cycle', ?, ?)
        ON CONFLICT(intent, pattern, source) DO UPDATE SET
          response_guidance=excluded.response_guidance,
          priority=excluded.priority,
          active=1,
          updated_at=excluded.updated_at
        ''',
        (intent, tpl['pattern'], tpl['guidance'], priority, now, now),
    )
    generated_rules += 1

# Add one generic lexical rule from frequent terms in open backlog
rows_q = crm.execute("SELECT customer_question FROM learning_backlog WHERE status='open' ORDER BY id DESC LIMIT 200").fetchall()
tokens = []
for r in rows_q:
    tokens.extend(normalize_tokens(r['customer_question'] or ''))

counter = Counter(tokens)
top_terms = [t for t, n in counter.items() if n >= 2][:6]
if top_terms:
    pattern = '(' + '|'.join(top_terms) + ')'
    guidance = 'Quando aparecer termo recorrente de duvida, confirmar contexto (produto, quantidade, prazo e cidade) e conduzir para proposta objetiva.'
    crm.execute(
        '''
        INSERT INTO knowledge_rules (intent, pattern, response_guidance, priority, active, source, created_at, updated_at)
        VALUES ('geral', ?, ?, 70, 1, 'auto_cycle', ?, ?)
        ON CONFLICT(intent, pattern, source) DO UPDATE SET
          response_guidance=excluded.response_guidance,
          active=1,
          updated_at=excluded.updated_at
        ''',
        (pattern, guidance, now, now),
    )
    generated_rules += 1

# Promote mandatory scripts discovered in learning documents.
mandatory_sources = []
for directive in (ml_data.get('mandatoryDirectives') or []):
    file_name = str(directive.get('fileName', '')).strip() or 'knowledge_doc'
    source = f"mandatory_doc:{file_name[:80]}"
    mandatory_sources.append(source)

    objective = str(directive.get('objective', '')).strip()
    questions = [str(q).strip() for q in (directive.get('questions') or []) if str(q).strip()]
    keywords = [str(k).strip() for k in (directive.get('keywords') or []) if str(k).strip()]
    question_preview = ' | '.join(questions[:4])
    guidance = (
        f"Script mandatorio ativo ({file_name}). "
        f"Objetivo central: {objective or 'preservar a finalidade comercial definida pela equipe'}. "
        f"Nao alterar foco/finalidade; adaptar apenas redacao ao cliente. "
        f"Perguntas-chave: {question_preview[:500]}"
    ).strip()

    if keywords:
        escaped = [re.escape(k) for k in keywords[:8]]
        pattern = '(' + '|'.join(escaped) + ')'
    else:
        pattern = '(atacado|revenda|cadastro|cnpj|loja)'

    crm.execute(
        '''
        INSERT INTO knowledge_rules (intent, pattern, response_guidance, priority, active, source, created_at, updated_at)
        VALUES ('geral', ?, ?, 120, 1, ?, ?, ?)
        ON CONFLICT(intent, pattern, source) DO UPDATE SET
          response_guidance=excluded.response_guidance,
          priority=excluded.priority,
          active=1,
          updated_at=excluded.updated_at
        ''',
        (pattern, guidance, source, now, now),
    )
    generated_rules += 1

if mandatory_sources:
    placeholders = ','.join(['?'] * len(mandatory_sources))
    crm.execute(
        f"UPDATE knowledge_rules SET active=0, updated_at=? WHERE source LIKE 'mandatory_doc:%' AND source NOT IN ({placeholders})",
        [now] + mandatory_sources
    )
else:
    crm.execute("UPDATE knowledge_rules SET active=0, updated_at=? WHERE source LIKE 'mandatory_doc:%'", (now,))

active_rules = crm.execute(
    "SELECT intent, pattern, response_guidance, priority, source FROM knowledge_rules WHERE active=1 ORDER BY priority DESC, updated_at DESC LIMIT 20"
).fetchall()

top_questions = crm.execute(
    "SELECT customer_question, intent, confidence, source_created_at FROM learning_backlog WHERE status='open' ORDER BY source_created_at DESC LIMIT 12"
).fetchall()

open_backlog = crm.execute("SELECT COUNT(*) c FROM learning_backlog WHERE status='open'").fetchone()['c']

machine_learning_block = {
    'folder': ml_data['folder'],
    'folderExists': ml_data['folderExists'],
    'indexedNow': int(ml_data['indexedNow']),
    'activeDocuments': int(ml_data['activeDocuments']),
    'highlights': ml_data['highlights'],
    'documents': ml_data['documents'],
    'mandatoryDirectives': ml_data.get('mandatoryDirectives', []),
    'ignoredContacts': {
        'sourceFile': ignored_contacts_data['sourceFile'],
        'sourceExists': ignored_contacts_data['sourceExists'],
        'indexedNow': int(ignored_contacts_data['indexedNow']),
        'activeContacts': int(ignored_contacts_data['activeContacts']),
        'contacts': ignored_contacts_data.get('contacts', [])[:120],
    },
}

dynamic_knowledge = {
    'generatedAt': now,
    'cycleSummary': {
        'newLeadsImported': new_leads,
        'newInteractionsImported': new_interactions,
        'newBacklogImported': new_backlog,
        'openBacklog': int(open_backlog),
        'activeRules': len(active_rules),
        'mandatoryDirectives': len(ml_data.get('mandatoryDirectives') or []),
        'ignoredContactsActive': int(ignored_contacts_data['activeContacts']),
    },
    'activeRules': [
        {
            'intent': r['intent'],
            'pattern': r['pattern'],
            'responseGuidance': r['response_guidance'],
            'priority': r['priority'],
            'source': r['source'],
        }
        for r in active_rules
    ],
    'topBacklogQuestions': [
        {
            'question': q['customer_question'],
            'intent': q['intent'],
            'confidence': q['confidence'],
            'createdAt': q['source_created_at'],
        }
        for q in top_questions
    ],
    'machineLearning': machine_learning_block,
}

global_data['dynamicKnowledge'] = dynamic_knowledge
global_data['crmSync'] = {
    'lastRunAt': now,
    'newLeadsImported': new_leads,
    'newInteractionsImported': new_interactions,
    'newBacklogImported': new_backlog,
    'openBacklog': int(open_backlog),
    'activeRules': len(active_rules),
    'machineLearningIndexedNow': int(ml_data['indexedNow']),
    'machineLearningActiveDocuments': int(ml_data['activeDocuments']),
    'mandatoryDirectives': len(ml_data.get('mandatoryDirectives') or []),
    'ignoredContactsIndexedNow': int(ignored_contacts_data['indexedNow']),
    'ignoredContactsActive': int(ignored_contacts_data['activeContacts']),
}
global_data['ignoredContacts'] = {
    'lastSyncAt': now,
    'sourceFile': os.path.basename(IGNORED_CONTACTS_FILE),
    'activeCount': int(ignored_contacts_data['activeContacts']),
    'numbers': [c['number'] for c in ignored_contacts_data.get('contacts', [])[:1000]],
    'contacts': ignored_contacts_data.get('contacts', [])[:300],
}
static_data_obj['global'] = global_data

n8n.execute(
    'UPDATE workflow_entity SET staticData = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?',
    (json.dumps(static_data_obj, ensure_ascii=False, separators=(',', ':')), WORKFLOW_ID),
)

crm.execute(
    '''
    INSERT INTO knowledge_cycles (run_at, new_leads, new_interactions, new_backlog, open_backlog, generated_rules, ml_docs_indexed, ml_docs_active, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''',
    (
        now,
        new_leads,
        new_interactions,
        new_backlog,
        int(open_backlog),
        generated_rules,
        int(ml_data['indexedNow']),
        int(ml_data['activeDocuments']),
        (
            f'Auto cycle from n8n workflow {WORKFLOW_ID}; '
            f'backlog_triage_empty={backlog_triage["empty"]}; '
            f'backlog_triage_test={backlog_triage["test_artifact"]}; '
            f'backlog_triage_duplicate={backlog_triage["duplicate"]}; '
            f'backlog_review_queued={backlog_review_queue["queued"]}; '
            f'stale_followup_candidates={stale_lead_followup["candidates"]}; '
            f'stale_followup_marked={stale_lead_followup["marked"]}'
        ),
    ),
)

# Basic sanitation for legacy values that should not surface in the operational workbook.
crm.execute(
    "UPDATE leads SET instagram = '' WHERE lower(trim(coalesce(instagram, ''))) IN ('sim', 'yes', 'ok', 'positivo')"
)
crm.execute(
    "UPDATE leads SET city = '' WHERE lower(trim(coalesce(city, ''))) IN ('sim', 'yes', 'ok', 'positivo', 'nao', 'não')"
)

crm.commit()
n8n.commit()

leads_rows = crm.execute(
    '''
    SELECT
      number,
      push_name,
      customer_name,
      informed_phone,
      city,
      instagram,
      company_legal_name,
      company_cnpj,
      company_cnpj_situation,
      cnpj_ativo_answer,
      loja_fisica_answer,
      book_sales_access,
      revenda_script_stage,
      revenda_script_completed,
      first_seen_at,
      last_product_focus,
      last_product_category,
      lead_stage,
      last_intent,
      last_confidence,
      awaiting_human,
      notes,
      next_step,
      last_inbound_text,
      last_reply_text,
      last_seen_at,
      updated_at
    FROM b2b_eligible_leads
    ORDER BY updated_at DESC
    LIMIT 5000
    '''
).fetchall()

interactions_rows = crm.execute(
    '''
    SELECT number, direction, text, intent, confidence, needs_human, event_ts, created_at
    FROM interactions
    ORDER BY event_ts DESC, id DESC
    LIMIT 5000
    '''
).fetchall()

backlog_rows = crm.execute(
    '''
    SELECT number, push_name, intent, confidence, customer_question, source_created_at, status
    FROM learning_backlog
    WHERE status='open'
    ORDER BY source_created_at DESC
    LIMIT 1000
    '''
).fetchall()

rules_rows = crm.execute(
    '''
    SELECT intent, pattern, response_guidance, priority, source, updated_at
    FROM knowledge_rules
    WHERE active=1
    ORDER BY priority DESC, updated_at DESC
    LIMIT 200
    '''
).fetchall()

cycle_rows = crm.execute(
    '''
    SELECT run_at, new_leads, new_interactions, new_backlog, open_backlog, generated_rules, ml_docs_indexed, ml_docs_active, notes
    FROM knowledge_cycles
    ORDER BY id DESC
    LIMIT 200
    '''
).fetchall()

docs_rows = crm.execute(
    '''
    SELECT file_path, file_name, extension, chars_count, indexed_at, last_modified
    FROM knowledge_documents
    WHERE status='active'
    ORDER BY indexed_at DESC
    LIMIT 500
    '''
).fetchall()

ignored_rows = crm.execute(
    '''
    SELECT number, raw_value, contact_name, source_file, last_modified, imported_at, status
    FROM ignored_contacts_registry
    ORDER BY status DESC, contact_name COLLATE NOCASE ASC, number ASC
    LIMIT 2000
    '''
).fetchall()

export_csv(
    os.path.join(EXPORT_DIR, 'leads_snapshot.csv'),
    [
        'number', 'push_name', 'customer_name', 'informed_phone', 'city', 'instagram',
        'company_legal_name', 'company_cnpj', 'company_cnpj_situation',
        'cnpj_ativo_answer', 'loja_fisica_answer', 'book_sales_access',
        'revenda_script_stage', 'revenda_script_completed', 'first_seen_at',
        'last_product_focus', 'last_product_category', 'lead_stage', 'last_intent',
        'last_confidence', 'awaiting_human', 'notes', 'next_step',
        'last_inbound_text', 'last_reply_text', 'last_seen_at', 'updated_at'
    ],
    leads_rows,
)
export_csv(
    os.path.join(EXPORT_DIR, 'interactions_recent.csv'),
    ['number', 'direction', 'text', 'intent', 'confidence', 'needs_human', 'event_ts', 'created_at'],
    interactions_rows,
)
export_csv(
    os.path.join(EXPORT_DIR, 'open_backlog.csv'),
    ['number', 'push_name', 'intent', 'confidence', 'customer_question', 'source_created_at', 'status'],
    backlog_rows,
)
export_csv(
    os.path.join(EXPORT_DIR, 'active_rules.csv'),
    ['intent', 'pattern', 'response_guidance', 'priority', 'source', 'updated_at'],
    rules_rows,
)
export_csv(
    os.path.join(EXPORT_DIR, 'knowledge_cycles.csv'),
    ['run_at', 'new_leads', 'new_interactions', 'new_backlog', 'open_backlog', 'generated_rules', 'ml_docs_indexed', 'ml_docs_active', 'notes'],
    cycle_rows,
)
export_csv(
    os.path.join(EXPORT_DIR, 'machine_learning_docs.csv'),
    ['file_path', 'file_name', 'extension', 'chars_count', 'indexed_at', 'last_modified'],
    docs_rows,
)
export_csv(
    os.path.join(EXPORT_DIR, 'ignored_contacts_registry.csv'),
    ['number', 'raw_value', 'contact_name', 'source_file', 'last_modified', 'imported_at', 'status'],
    ignored_rows,
)

workbook_sheets = [
    {
        'name': 'LEADS_OPERACIONAL',
        'headers': [
            'NÚMERO', 'NOME NO WHATSAPP', 'NOME DO LEAD', 'TELEFONE INFORMADO', 'CIDADE',
            'INSTAGRAM', 'RAZÃO SOCIAL', 'CNPJ', 'SITUAÇÃO DO CNPJ', 'STATUS DO BOOK',
            'ESTÁGIO DO LEAD', 'ÚLTIMA INTENÇÃO', 'CONFIANÇA', 'AGUARDANDO HUMANO',
            'OBSERVAÇÕES', 'PRÓXIMO PASSO', 'ÚLTIMA MENSAGEM DO LEAD',
            'ÚLTIMA RESPOSTA DO ATENDENTE', 'PRIMEIRO CONTATO', 'ÚLTIMA INTERAÇÃO', 'ATUALIZADO EM'
        ],
        'rows': build_leads_workbook_rows(leads_rows),
    },
    {
        'name': 'INTERACOES_RECENTES',
        'headers': ['NÚMERO', 'DIREÇÃO', 'MENSAGEM', 'INTENÇÃO', 'CONFIANÇA', 'EXIGE HUMANO', 'DATA/HORA DO EVENTO', 'REGISTRADO EM'],
        'rows': build_interactions_workbook_rows(interactions_rows),
    },
    {
        'name': 'RESUMO_FUNIL',
        'headers': ['MÉTRICA', 'VALOR'],
        'rows': build_summary_workbook_rows([
            {'metric': 'new_leads', 'value': new_leads},
            {'metric': 'new_interactions', 'value': new_interactions},
            {'metric': 'new_backlog', 'value': new_backlog},
            {'metric': 'open_backlog', 'value': int(open_backlog)},
            {'metric': 'active_rules', 'value': len(active_rules)},
            {'metric': 'generated_rules', 'value': generated_rules},
            {'metric': 'ml_docs_indexed_now', 'value': int(ml_data['indexedNow'])},
            {'metric': 'ml_docs_active', 'value': int(ml_data['activeDocuments'])},
            {'metric': 'ignored_contacts_active', 'value': int(ignored_contacts_data['activeContacts'])},
            {'metric': 'generated_at', 'value': now},
        ]),
    },
]

export_xlsx_workbook(LEADS_WORKBOOK_PATH, workbook_sheets)
export_xlsx_workbook(LEADS_WORKBOOK_EXPORT_PATH, workbook_sheets)

print('crm_cycle_ok')
print(json.dumps({
    'newLeads': new_leads,
    'newInteractions': new_interactions,
    'newBacklog': new_backlog,
    'openBacklog': int(open_backlog),
    'activeRules': len(active_rules),
    'generatedRules': generated_rules,
    'machineLearningIndexedNow': int(ml_data['indexedNow']),
    'machineLearningActiveDocuments': int(ml_data['activeDocuments']),
    'mandatoryDirectives': len(ml_data.get('mandatoryDirectives') or []),
    'ignoredContactsIndexedNow': int(ignored_contacts_data['indexedNow']),
    'ignoredContactsActive': int(ignored_contacts_data['activeContacts']),
    'backlogTriagedEmpty': int(backlog_triage['empty']),
    'backlogTriagedTestArtifacts': int(backlog_triage['test_artifact']),
    'backlogTriagedDuplicates': int(backlog_triage['duplicate']),
    'backlogReviewQueued': int(backlog_review_queue['queued']),
    'staleLeadFollowupCandidates': int(stale_lead_followup['candidates']),
    'staleLeadFollowupMarked': int(stale_lead_followup['marked']),
    'exportsDir': EXPORT_DIR,
    'leadsWorkbookPath': LEADS_WORKBOOK_PATH,
}, ensure_ascii=False))

crm.close()
n8n.close()
