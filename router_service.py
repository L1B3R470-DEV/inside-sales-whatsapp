import hashlib
import json
import math
import os
import re
import sys
import ctypes
import atexit
import base64
import tempfile
import urllib.request
import urllib.error

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
import sqlite3
import subprocess
import threading
import time
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from xml.etree import ElementTree as ET

import phonenumbers
import structlog
from cachetools import TTLCache
from flask import Flask, jsonify, request
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
from rank_bm25 import BM25Okapi

import multi_llm

try:
    import pymupdf  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

log = structlog.get_logger()
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer() if os.getenv('ROUTER_LOG_FORMAT', 'console') == 'console' else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(int(os.getenv('ROUTER_LOG_LEVEL', '20'))),
)


ROOT_DIR = Path(__file__).resolve().parent
ML_DIR = Path(os.getenv('ROUTER_ML_DIR', ROOT_DIR / 'CHATGPT_MACHINE_LEARNING'))
DB_PATH = Path(os.getenv('ROUTER_DB_PATH', ROOT_DIR / 'router_runtime.sqlite'))
QDRANT_PATH = Path(os.getenv('ROUTER_QDRANT_PATH', ROOT_DIR / 'rag_vector_store'))
QDRANT_COLLECTION = os.getenv('ROUTER_QDRANT_COLLECTION', 'knowledge_chunks')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
OPENAI_EMBED_MODEL = os.getenv('ROUTER_OPENAI_EMBED_MODEL', 'text-embedding-3-small')
OPENAI_TRANSCRIBE_MODEL = os.getenv('ROUTER_OPENAI_TRANSCRIBE_MODEL', 'gpt-4o-mini-transcribe')
OPENAI_TRANSCRIBE_PROMPT = os.getenv(
    'ROUTER_OPENAI_TRANSCRIBE_PROMPT',
    'Transcreva fielmente o audio em portugues do Brasil, mantendo nomes, numeros, valores e pontuacao.',
).strip()
OPENAI_TRANSCRIBE_TIMEOUT_SECONDS = int(os.getenv('ROUTER_OPENAI_TRANSCRIBE_TIMEOUT_SECONDS', '35'))
MAX_AUDIO_BYTES = int(os.getenv('ROUTER_MAX_AUDIO_BYTES', str(25 * 1024 * 1024)))
WATCH_INTERVAL_SECONDS = int(os.getenv('ROUTER_WATCH_INTERVAL_SECONDS', '300'))
INGEST_REFRESH_ON_ROUTE_SECONDS = int(os.getenv('ROUTER_INGEST_REFRESH_ON_ROUTE_SECONDS', '90'))
MAX_CACHE_REPLY_CHARS = int(os.getenv('ROUTER_MAX_CACHE_REPLY_CHARS', '1800'))
LID_LOG_SCAN_SECONDS = int(os.getenv('ROUTER_LID_LOG_SCAN_SECONDS', '1800'))
LID_LOG_SCAN_LINES = int(os.getenv('ROUTER_LID_LOG_SCAN_LINES', '2500'))
ROUTER_ENFORCE_TEST_GATE = str(os.getenv('ROUTER_ENFORCE_TEST_GATE', 'false')).strip().lower() in {'1', 'true', 'yes', 'on'}

TEXT_EXTENSIONS = {'.txt', '.md', '.csv', '.json', '.log', '.xml', '.html', '.htm'}
OFFICE_XML_EXTENSIONS = {'.docx', '.xlsx'}
OTHER_DOC_EXTENSIONS = {'.pdf', '.rtf'}
INDEXABLE_EXTENSIONS = TEXT_EXTENSIONS | OFFICE_XML_EXTENSIONS | OTHER_DOC_EXTENSIONS
SKIP_DIR_NAMES = {'COLEÇÃO - BANCO DE IMAGENS', '__pycache__', 'crm_exports', '_legacy_wrappers_removed'}
COLLECTION_READY = False
COLLECTION_DIM = 0
EMBEDDINGS_AVAILABLE = True
QDRANT_DISABLED = False
QDRANT_RETRY_COOLDOWN_SECONDS = int(os.getenv('ROUTER_QDRANT_RETRY_COOLDOWN_SECONDS', '60'))
QDRANT_LAST_FAILURE_EPOCH = 0

EMBED_RATE_LIMIT_RPM = int(os.getenv('ROUTER_EMBED_RATE_LIMIT_RPM', '500'))
EMBED_RATE_LIMIT_BURST = int(os.getenv('ROUTER_EMBED_RATE_LIMIT_BURST', '10'))
LID_CACHE_TTL_SECONDS = int(os.getenv('ROUTER_LID_CACHE_TTL_SECONDS', '3600'))

# --- Dual-LLM: SDR persona system prompt for Claude/GPT reply generation ---
def _load_sdr_prompt() -> str:
    env_val = os.getenv('SDR_SYSTEM_PROMPT', '').strip()
    if env_val:
        return env_val
    prompt_file = ROOT_DIR / 'sdr_prompt.txt'
    if prompt_file.exists():
        return prompt_file.read_text(encoding='utf-8').strip()
    return 'Voce e Eduardo, Consultor de Vendas Internas da Classe Couro.'

SDR_SYSTEM_PROMPT = _load_sdr_prompt()

SAFE_CACHE_INTENTS = {
    'saudacao',
    'agradecimento',
    'institucional_empresa',
    'produto_catalogo',
    'prazo_entrega',
    'pagamento',
    'preco_orcamento',
}

CACHE_MIN_CONFIDENCE_LEARN = float(os.getenv('ROUTER_CACHE_MIN_CONFIDENCE_LEARN', '0.45'))
CACHE_SEMANTIC_ENABLED = str(os.getenv('ROUTER_CACHE_SEMANTIC_ENABLED', 'true')).strip().lower() in {'1', 'true', 'yes', 'on'}
CACHE_SEMANTIC_THRESHOLD = float(os.getenv('ROUTER_CACHE_SEMANTIC_THRESHOLD', '0.78'))
CACHE_SEMANTIC_CANDIDATE_LIMIT = int(os.getenv('ROUTER_CACHE_SEMANTIC_CANDIDATE_LIMIT', '120'))

STOPWORDS = {
    'para', 'com', 'sem', 'mais', 'menos', 'sobre', 'quero', 'gostaria', 'preciso', 'pode', 'favor', 'agora', 'depois',
    'como', 'qual', 'quais', 'onde', 'quando', 'isso', 'essa', 'esse', 'isto', 'pela', 'pelo', 'meu', 'minha', 'seu',
    'sua', 'dos', 'das', 'por', 'uma', 'uns', 'umas', 'nos', 'nas', 'que', 'vou', 'tem', 'tenho', 'saber', 'valor',
    'preco', 'prazo', 'bom', 'dia', 'boa', 'tarde', 'noite', 'ola', 'olá', 'oi'
}

RAW_AUTHORIZED_OUTBOUND_LINKS = [
    item.strip()
    for item in str(os.getenv('ROUTER_AUTHORIZED_OUTBOUND_LINKS', '')).split(',')
    if item.strip()
]
URL_PATTERN = re.compile(r'(?i)\bhttps?://[^\s<>()]+')
WWW_PATTERN = re.compile(r'(?i)\bwww\.[^\s<>()]+')
DOMAIN_PATTERN = re.compile(r'(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?:/[^\s<>()]*)?')
EMOJI_PATTERN = re.compile(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]', re.UNICODE)


class EmbeddingRateLimiter:
    """Token-bucket rate limiter for OpenAI embedding requests."""
    def __init__(self, rpm: int, burst: int):
        self._rate = rpm / 60.0
        self._max_tokens = burst
        self._tokens = float(burst)
        self._last = time.monotonic()
        self._lock = threading.Lock()
        self._total_requests = 0
        self._total_throttled = 0

    def acquire(self) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(self._max_tokens, self._tokens + elapsed * self._rate)
            self._total_requests += 1
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            self._total_throttled += 1
            return False

    def wait(self, timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.acquire():
                return True
            time.sleep(0.1)
        return False

    @property
    def stats(self) -> Dict:
        with self._lock:
            return {
                'totalRequests': self._total_requests,
                'totalThrottled': self._total_throttled,
                'availableTokens': round(self._tokens, 2),
            }

embed_limiter = EmbeddingRateLimiter(EMBED_RATE_LIMIT_RPM, EMBED_RATE_LIMIT_BURST)


class LidCache:
    """In-memory cache for LID->phone mappings using cachetools TTLCache."""
    def __init__(self, ttl: int, maxsize: int = 4096):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, jid: str):
        with self._lock:
            entry = self._cache.get(jid)
            if entry is not None:
                self._hits += 1
                return entry
            self._misses += 1
            return None

    def put(self, jid: str, mapping: Dict):
        with self._lock:
            self._cache[jid] = mapping

    def invalidate(self, jid: str):
        with self._lock:
            self._cache.pop(jid, None)

    @property
    def stats(self) -> Dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                'hits': self._hits,
                'misses': self._misses,
                'hitRate': round(self._hits / total, 3) if total > 0 else 0,
                'cachedEntries': len(self._cache),
            }

lid_cache = LidCache(LID_CACHE_TTL_SECONDS)

ATTENDANT_OPERATIONAL_HOST_ROLE = os.getenv('ATTENDANT_OPERATIONAL_HOST_ROLE', 'PC_CLS').strip() or 'PC_CLS'
ATTENDANT_OPERATIONAL_HOST_IP = os.getenv('ATTENDANT_OPERATIONAL_HOST_IP', '100.113.13.27').strip() or '100.113.13.27'
ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE = os.getenv('ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE', ATTENDANT_OPERATIONAL_HOST_ROLE).strip() or ATTENDANT_OPERATIONAL_HOST_ROLE
ATTENDANT_OPERATIONAL_DOCKER_HOST_IP = os.getenv('ATTENDANT_OPERATIONAL_DOCKER_HOST_IP', ATTENDANT_OPERATIONAL_HOST_IP).strip() or ATTENDANT_OPERATIONAL_HOST_IP
ATTENDANT_INTERACTIVE_HOST_ROLE = os.getenv('ATTENDANT_INTERACTIVE_HOST_ROLE', 'PC_LBN').strip() or 'PC_LBN'
ATTENDANT_INTERACTIVE_HOST_IP = os.getenv('ATTENDANT_INTERACTIVE_HOST_IP', '100.101.106.95').strip() or '100.101.106.95'
ATTENDANT_INTERACTIVE_MODE_ONLY = os.getenv('ATTENDANT_INTERACTIVE_MODE_ONLY', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
ATTENDANT_REJECT_LBN_AS_RUNTIME = os.getenv('ATTENDANT_REJECT_LBN_AS_RUNTIME', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
ATTENDANT_REJECT_LBN_DOCKER = os.getenv('ATTENDANT_REJECT_LBN_DOCKER', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}


def topology_metadata() -> Dict:
    return {
        'operationalHostRole': ATTENDANT_OPERATIONAL_HOST_ROLE,
        'operationalHostIp': ATTENDANT_OPERATIONAL_HOST_IP,
        'operationalDockerHostRole': ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE,
        'operationalDockerHostIp': ATTENDANT_OPERATIONAL_DOCKER_HOST_IP,
        'interactiveHostRole': ATTENDANT_INTERACTIVE_HOST_ROLE,
        'interactiveHostIp': ATTENDANT_INTERACTIVE_HOST_IP,
        'interactiveModeOnly': ATTENDANT_INTERACTIVE_MODE_ONLY,
        'rejectLbnAsRuntime': ATTENDANT_REJECT_LBN_AS_RUNTIME,
        'rejectLbnDocker': ATTENDANT_REJECT_LBN_DOCKER,
    }


def validate_topology() -> None:
    if ATTENDANT_OPERATIONAL_HOST_ROLE != 'PC_CLS' or ATTENDANT_OPERATIONAL_HOST_IP != '100.113.13.27':
        raise RuntimeError(
            f"invalid_operational_ai_topology role={ATTENDANT_OPERATIONAL_HOST_ROLE} ip={ATTENDANT_OPERATIONAL_HOST_IP}"
        )
    if ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE != 'PC_CLS' or ATTENDANT_OPERATIONAL_DOCKER_HOST_IP != '100.113.13.27':
        raise RuntimeError(
            f"invalid_operational_docker_topology role={ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE} ip={ATTENDANT_OPERATIONAL_DOCKER_HOST_IP}"
        )
    if ATTENDANT_INTERACTIVE_HOST_ROLE != 'PC_LBN' or ATTENDANT_INTERACTIVE_HOST_IP != '100.101.106.95':
        raise RuntimeError(
            f"invalid_interactive_topology role={ATTENDANT_INTERACTIVE_HOST_ROLE} ip={ATTENDANT_INTERACTIVE_HOST_IP}"
        )
    if not ATTENDANT_REJECT_LBN_AS_RUNTIME or not ATTENDANT_REJECT_LBN_DOCKER:
        raise RuntimeError('invalid_topology_guardrails reject_lbn_flags_disabled')

app = Flask(__name__)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
qdrant = None
SINGLE_INSTANCE_MUTEX_HANDLE = None
LAST_INGEST_AT = ''
LAST_INGEST_EPOCH = 0
INGEST_LOCK = threading.Lock()


def acquire_single_instance_lock() -> bool:
    """Windows global mutex to guarantee single router instance."""
    global SINGLE_INSTANCE_MUTEX_HANDLE
    if os.name != 'nt':
        return True
    mutex_name = os.getenv('ROUTER_SINGLE_INSTANCE_NAME', r'Local\WA_Router_Service_Instance')
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, mutex_name)
    if not handle:
        return False
    error_already_exists = 183
    last_error = kernel32.GetLastError()
    if last_error == error_already_exists:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        return False
    SINGLE_INSTANCE_MUTEX_HANDLE = handle

    def _release_mutex():
        if SINGLE_INSTANCE_MUTEX_HANDLE:
            kernel32.CloseHandle(ctypes.c_void_p(SINGLE_INSTANCE_MUTEX_HANDLE))

    atexit.register(_release_mutex)
    return True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    text = str(value or '')
    text = text.replace('\u00a0', ' ')
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = re.sub(r'[^a-z0-9à-ÿ\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_ascii(value: str) -> str:
    text = str(value or '')
    text = text.lower()
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def now_epoch() -> int:
    return int(time.time())


def digits_only(value: str) -> str:
    return re.sub(r'\D', '', str(value or ''))


def _safe_audio_suffix(file_name: str, mime_type: str) -> str:
    name = str(file_name or '').lower().strip()
    mime = str(mime_type or '').lower().strip()
    if name.endswith(('.mp3', '.wav', '.m4a', '.webm', '.ogg', '.mp4', '.mpeg', '.mpga')):
        return Path(name).suffix
    if 'wav' in mime:
        return '.wav'
    if 'm4a' in mime:
        return '.m4a'
    if 'webm' in mime:
        return '.webm'
    if 'ogg' in mime:
        return '.ogg'
    if 'mp4' in mime:
        return '.mp4'
    if 'mpeg' in mime or 'mp3' in mime:
        return '.mp3'
    return '.mp3'


def _read_audio_bytes_from_payload(audio_payload: Dict) -> Tuple[bytes, str, str]:
    audio = dict(audio_payload or {})
    audio_base64 = str(audio.get('base64') or audio.get('audioBase64') or '').strip()
    audio_url = str(audio.get('url') or audio.get('audioUrl') or '').strip()
    mime_type = str(audio.get('mimeType') or audio.get('mimetype') or '').strip()
    file_name = str(audio.get('fileName') or audio.get('filename') or '').strip()

    if audio_base64:
        if audio_base64.startswith('data:') and ';base64,' in audio_base64:
            audio_base64 = audio_base64.split(';base64,', 1)[1]
        raw = base64.b64decode(audio_base64, validate=False)
        if not raw:
            raise ValueError('audio_base64_empty')
        return raw, mime_type, file_name

    if audio_url:
        req = urllib.request.Request(
            audio_url,
            headers={'User-Agent': 'wa-router/1.0'},
            method='GET',
        )
        with urllib.request.urlopen(req, timeout=OPENAI_TRANSCRIBE_TIMEOUT_SECONDS) as resp:
            raw = resp.read(MAX_AUDIO_BYTES + 1)
            if len(raw) > MAX_AUDIO_BYTES:
                raise ValueError('audio_too_large')
            mime = str(resp.headers.get('Content-Type') or mime_type).strip()
            return raw, mime, file_name

    raise ValueError('audio_source_missing')


def transcribe_inbound_audio(payload: Dict) -> Dict:
    inbound_audio = payload.get('inboundAudio')
    if not isinstance(inbound_audio, dict) or not inbound_audio:
        return {'ok': False, 'reason': 'no_audio_payload', 'text': ''}
    if not openai_client:
        return {'ok': False, 'reason': 'openai_client_missing', 'text': ''}

    try:
        audio_bytes, mime_type, file_name = _read_audio_bytes_from_payload(inbound_audio)
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            return {'ok': False, 'reason': 'audio_too_large', 'text': ''}

        suffix = _safe_audio_suffix(file_name, mime_type)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            with open(tmp.name, 'rb') as fh:
                resp = openai_client.audio.transcriptions.create(
                    model=OPENAI_TRANSCRIBE_MODEL,
                    file=fh,
                    response_format='json',
                    prompt=OPENAI_TRANSCRIBE_PROMPT if OPENAI_TRANSCRIBE_PROMPT else None,
                )
        text = str(getattr(resp, 'text', '') or '').strip()
        return {
            'ok': bool(text),
            'reason': 'ok' if text else 'empty_transcript',
            'text': text,
            'model': OPENAI_TRANSCRIBE_MODEL,
        }
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        # retry once after short delay for transient network failures
        try:
            time.sleep(2)
            audio_bytes, mime_type, file_name = _read_audio_bytes_from_payload(inbound_audio)
            suffix = _safe_audio_suffix(file_name, mime_type)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
                tmp.write(audio_bytes)
                tmp.flush()
                with open(tmp.name, 'rb') as fh:
                    resp = openai_client.audio.transcriptions.create(
                        model=OPENAI_TRANSCRIBE_MODEL,
                        file=fh,
                        response_format='json',
                        prompt=OPENAI_TRANSCRIBE_PROMPT if OPENAI_TRANSCRIBE_PROMPT else None,
                    )
            text = str(getattr(resp, 'text', '') or '').strip()
            return {'ok': bool(text), 'reason': 'ok_retry' if text else 'empty_transcript_retry', 'text': text, 'model': OPENAI_TRANSCRIBE_MODEL}
        except Exception:
            return {'ok': False, 'reason': f'audio_download_failed:{exc}', 'text': ''}
    except Exception as exc:
        return {'ok': False, 'reason': f'transcription_failed:{exc}', 'text': ''}


def validate_br_phone(value: str) -> str:
    """Validate and normalize a Brazilian phone number to E.164 digits.
    Returns the normalized digits (e.g. '5511999998888') or the raw digits if invalid."""
    raw = digits_only(value)
    if not raw:
        return raw
    try:
        parsed = phonenumbers.parse('+' + raw if not raw.startswith('+') else raw, 'BR')
        if phonenumbers.is_valid_number(parsed):
            return digits_only(phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164))
    except phonenumbers.NumberParseException:
        pass
    return raw


def normalize_lid_jid(value: str) -> str:
    jid = str(value or '').strip().lower()
    if not jid.endswith('@lid'):
        return jid
    return re.sub(r':\d+(?=@lid$)', '', jid)


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def normalize_authorized_link(value: str) -> str:
    return re.sub(r'/+$', '', str(value or '').strip().strip('<>').rstrip('),.;!?')).lower()


AUTHORIZED_OUTBOUND_LINKS = {
    normalize_authorized_link(item)
    for item in RAW_AUTHORIZED_OUTBOUND_LINKS
    if normalize_authorized_link(item)
}


def strip_emoji_characters(value: str) -> str:
    return EMOJI_PATTERN.sub('', str(value or ''))


def strip_unauthorized_links(value: str, authorized_links=None) -> str:
    allowed = AUTHORIZED_OUTBOUND_LINKS if authorized_links is None else {
        normalize_authorized_link(item)
        for item in (authorized_links or [])
        if normalize_authorized_link(item)
    }
    text = str(value or '')
    for pattern in (URL_PATTERN, WWW_PATTERN, DOMAIN_PATTERN):
        current = text

        def _replacer(match):
            start = match.start()
            prev = current[start - 1] if start > 0 else ''
            token = match.group(0)
            if prev == '@':
                return token
            return token if normalize_authorized_link(token) in allowed else ''

        text = pattern.sub(_replacer, text)
    return text


def sanitize_outbound_text(value: str, limit: int = 0, authorized_links=None) -> str:
    text = str(value or '').replace('\r\n', '\n').replace('\r', '\n')
    text = strip_unauthorized_links(text, authorized_links=authorized_links)
    text = strip_emoji_characters(text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = text.strip()
    if limit > 0:
        text = text[:limit].strip()
    return text


def compact_text(value: str, limit: int = 280) -> str:
    return re.sub(r'\s+', ' ', str(value or '')).strip()[:limit]


def safe_json_loads(value, default):
    if isinstance(value, (dict, list)):
        return value
    raw = str(value or '').strip()
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def extract_last_question(text: str) -> str:
    raw = str(text or '').strip()
    if not raw or '?' not in raw:
        return ''
    questions = re.findall(r'([^?]{6,220}\?)', raw)
    if questions:
        return compact_text(questions[-1], 220)
    return compact_text(raw.rsplit('?', 1)[0] + '?', 220)


def infer_quantity_hint(text: str, structured: Dict) -> str:
    data = structured or {}
    for key in ('quantity', 'quantidade', 'volume', 'quantity_hint'):
        value = compact_text(data.get(key), 80)
        if value:
            return value
    match = re.search(r'\b(\d{1,4})\s*(unidades?|pecas?|itens?|kits?|bolsas?|carteiras?|cintos?)\b', normalize_text(text))
    if match:
        return compact_text(f'{match.group(1)} {match.group(2)}', 80)
    return ''


def infer_city_hint(text: str, structured: Dict) -> str:
    data = structured or {}
    for key in ('city', 'cidade', 'cityHint', 'cidadeHint', 'location'):
        value = compact_text(data.get(key), 80)
        if value:
            return value
    match = re.search(r'\b(?:em|para)\s+([a-zà-ÿ]{3,}(?:\s+[a-zà-ÿ]{2,}){0,2})(?:\s*[-/]\s*([a-z]{2}))?\b', normalize_text(text))
    if match:
        city = compact_text(match.group(1), 60)
        uf = compact_text(match.group(2), 4).upper()
        return f'{city}/{uf}' if city and uf else city
    return ''


def summarize_answered_slots(answered_slots: Dict) -> str:
    if not isinstance(answered_slots, dict):
        return ''
    labels = {
        'productFocus': 'produto',
        'productCategory': 'categoria',
        'quantityHint': 'quantidade',
        'cityHint': 'cidade',
        'companyName': 'empresa',
        'cnpj': 'cnpj',
        'customerName': 'nome',
        'audienceHint': 'publico',
        'objection': 'objecao',
    }
    parts = []
    for key, label in labels.items():
        value = compact_text(answered_slots.get(key), 90)
        if value:
            parts.append(f'{label}={value}')
    return ' | '.join(parts[:6])


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn


def has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f'PRAGMA table_info({table})').fetchall()
    return any(str(row['name']) == column for row in rows)


def get_qdrant():
    global qdrant, QDRANT_DISABLED, QDRANT_LAST_FAILURE_EPOCH
    if QDRANT_DISABLED:
        if (now_epoch() - int(QDRANT_LAST_FAILURE_EPOCH or 0)) < max(5, QDRANT_RETRY_COOLDOWN_SECONDS):
            return None
        QDRANT_DISABLED = False
    if qdrant is not None:
        return qdrant
    try:
        qdrant = QdrantClient(path=str(QDRANT_PATH))
        QDRANT_DISABLED = False
        return qdrant
    except Exception as exc:
        log.error('qdrant_init_failed', error=str(exc))
        QDRANT_DISABLED = True
        QDRANT_LAST_FAILURE_EPOCH = now_epoch()
        qdrant = None
        return None


def ensure_db():
    conn = db()
    conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS response_cache (
          normalized_message TEXT PRIMARY KEY,
          reply_text TEXT NOT NULL,
          intent TEXT,
          confidence REAL DEFAULT 0,
          source TEXT DEFAULT 'auto',
          active INTEGER DEFAULT 1,
          hit_count INTEGER DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_hit_at TEXT
        );

        CREATE TABLE IF NOT EXISTS route_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          number TEXT,
          push_name TEXT,
          inbound_text TEXT,
          normalized_message TEXT,
          route_decision TEXT,
          message_complexity TEXT,
          cache_hit INTEGER DEFAULT 0,
          lead_score INTEGER DEFAULT 0,
          rag_hit_count INTEGER DEFAULT 0,
          rag_top_score REAL DEFAULT 0,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rag_documents (
          file_path TEXT PRIMARY KEY,
          file_name TEXT NOT NULL,
          extension TEXT NOT NULL,
          file_hash TEXT NOT NULL,
          last_modified REAL NOT NULL,
          chunk_count INTEGER DEFAULT 0,
          indexed_at TEXT NOT NULL,
          status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS rag_chunks (
          chunk_id TEXT PRIMARY KEY,
          file_path TEXT NOT NULL,
          file_name TEXT,
          chunk_hash TEXT NOT NULL,
          chunk_text TEXT,
          normalized_text TEXT,
          token_count INTEGER DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_route_logs_created_at ON route_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_route_logs_normalized_message ON route_logs(normalized_message);
        CREATE INDEX IF NOT EXISTS idx_rag_chunks_file_path ON rag_chunks(file_path);

        CREATE TABLE IF NOT EXISTS lid_mappings (
          remote_jid TEXT PRIMARY KEY,
          phone_number TEXT NOT NULL,
          resolved_jid TEXT NOT NULL,
          push_name TEXT,
          source TEXT DEFAULT 'log_scan',
          message_id TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_lid_mappings_phone_number ON lid_mappings(phone_number);

        CREATE TABLE IF NOT EXISTS blocked_numbers (
          number TEXT PRIMARY KEY,
          reason TEXT DEFAULT '',
          added_at TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS always_allowed_numbers (
          number TEXT PRIMARY KEY,
          reason TEXT DEFAULT '',
          added_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversation_history (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          contact_key TEXT NOT NULL,
          direction TEXT NOT NULL DEFAULT 'inbound',
          message_text TEXT NOT NULL,
          intent TEXT DEFAULT '',
          complexity TEXT DEFAULT '',
          lead_score REAL DEFAULT 0,
          route_decision TEXT DEFAULT '',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_conv_history_contact_key ON conversation_history(contact_key);
        CREATE INDEX IF NOT EXISTS idx_conv_history_created_at ON conversation_history(created_at);

        CREATE TABLE IF NOT EXISTS lead_memory (
          contact_key TEXT PRIMARY KEY,
          customer_name TEXT DEFAULT '',
          lead_stage TEXT DEFAULT '',
          last_intent TEXT DEFAULT '',
          product_focus TEXT DEFAULT '',
          product_category TEXT DEFAULT '',
          quantity_hint TEXT DEFAULT '',
          city_hint TEXT DEFAULT '',
          company_name TEXT DEFAULT '',
          cnpj TEXT DEFAULT '',
          last_objection TEXT DEFAULT '',
          next_step TEXT DEFAULT '',
          summary TEXT DEFAULT '',
          answered_slots TEXT DEFAULT '{}',
          open_question TEXT DEFAULT '',
          commercial_momentum TEXT DEFAULT '',
          last_inbound_text TEXT DEFAULT '',
          last_outbound_text TEXT DEFAULT '',
          last_route_decision TEXT DEFAULT '',
          last_provider TEXT DEFAULT '',
          updated_at TEXT NOT NULL,
          learned_at TEXT NOT NULL,
          source TEXT DEFAULT 'router'
        );

        CREATE TABLE IF NOT EXISTS learning_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          contact_key TEXT NOT NULL,
          intent TEXT DEFAULT '',
          lead_stage TEXT DEFAULT '',
          route_decision TEXT DEFAULT '',
          inbound_text TEXT DEFAULT '',
          reply_text TEXT DEFAULT '',
          structured_data TEXT DEFAULT '{}',
          memory_update TEXT DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_learning_events_contact_key ON learning_events(contact_key);
        CREATE INDEX IF NOT EXISTS idx_learning_events_created_at ON learning_events(created_at);
        '''
    )
    if not has_column(conn, 'rag_chunks', 'file_name'):
        conn.execute('ALTER TABLE rag_chunks ADD COLUMN file_name TEXT')
    if not has_column(conn, 'rag_chunks', 'chunk_text'):
        conn.execute('ALTER TABLE rag_chunks ADD COLUMN chunk_text TEXT')
    if not has_column(conn, 'rag_chunks', 'normalized_text'):
        conn.execute('ALTER TABLE rag_chunks ADD COLUMN normalized_text TEXT')
    conn.commit()
    conn.close()


def get_lead_memory(contact_key: str) -> Dict:
    if not contact_key:
        return {}
    conn = db()
    row = conn.execute(
        '''
        SELECT contact_key, customer_name, lead_stage, last_intent, product_focus, product_category,
               quantity_hint, city_hint, company_name, cnpj, last_objection, next_step, summary,
               answered_slots, open_question, commercial_momentum, last_inbound_text, last_outbound_text,
               last_route_decision, last_provider, updated_at, learned_at, source
        FROM lead_memory
        WHERE contact_key = ?
        ''',
        (contact_key,),
    ).fetchone()
    conn.close()
    if not row:
        return {}
    data = dict(row)
    return {
        'contactKey': str(data.get('contact_key') or '').strip(),
        'customerName': str(data.get('customer_name') or '').strip(),
        'leadStage': str(data.get('lead_stage') or '').strip(),
        'lastIntent': str(data.get('last_intent') or '').strip(),
        'productFocus': str(data.get('product_focus') or '').strip(),
        'productCategory': str(data.get('product_category') or '').strip(),
        'quantityHint': str(data.get('quantity_hint') or '').strip(),
        'cityHint': str(data.get('city_hint') or '').strip(),
        'companyName': str(data.get('company_name') or '').strip(),
        'cnpj': str(data.get('cnpj') or '').strip(),
        'lastObjection': str(data.get('last_objection') or '').strip(),
        'nextStep': sanitize_outbound_text(data.get('next_step') or '', 220),
        'summary': sanitize_outbound_text(data.get('summary') or '', 900),
        'answeredSlots': safe_json_loads(data.get('answered_slots'), {}) or {},
        'openQuestion': sanitize_outbound_text(data.get('open_question') or '', 220),
        'commercialMomentum': str(data.get('commercial_momentum') or '').strip(),
        'lastInboundText': str(data.get('last_inbound_text') or '').strip(),
        'lastOutboundText': sanitize_outbound_text(data.get('last_outbound_text') or '', 400),
        'lastRouteDecision': str(data.get('last_route_decision') or '').strip(),
        'lastProvider': str(data.get('last_provider') or '').strip(),
        'updatedAt': str(data.get('updated_at') or '').strip(),
        'learnedAt': str(data.get('learned_at') or '').strip(),
        'source': str(data.get('source') or '').strip(),
    }


def upsert_lead_memory(contact_key: str, patch: Dict) -> Dict:
    if not contact_key:
        return {}
    existing = get_lead_memory(contact_key)
    answered_slots = dict(existing.get('answeredSlots') or {})
    incoming_slots = patch.get('answeredSlots') if isinstance(patch.get('answeredSlots'), dict) else {}
    for key, value in incoming_slots.items():
        clean = compact_text(value, 120)
        if clean:
            answered_slots[key] = clean

    merged = {
        'contactKey': contact_key,
        'customerName': compact_text(patch.get('customerName') or existing.get('customerName'), 120),
        'leadStage': compact_text(patch.get('leadStage') or existing.get('leadStage'), 60),
        'lastIntent': compact_text(patch.get('lastIntent') or existing.get('lastIntent'), 60),
        'productFocus': compact_text(patch.get('productFocus') or existing.get('productFocus'), 90),
        'productCategory': compact_text(patch.get('productCategory') or existing.get('productCategory'), 90),
        'quantityHint': compact_text(patch.get('quantityHint') or existing.get('quantityHint'), 90),
        'cityHint': compact_text(patch.get('cityHint') or existing.get('cityHint'), 90),
        'companyName': compact_text(patch.get('companyName') or existing.get('companyName'), 140),
        'cnpj': digits_only(patch.get('cnpj') or existing.get('cnpj')),
        'lastObjection': compact_text(patch.get('lastObjection') or existing.get('lastObjection'), 180),
        'nextStep': sanitize_outbound_text(patch.get('nextStep') or existing.get('nextStep'), 220),
        'summary': sanitize_outbound_text(patch.get('summary') or existing.get('summary'), 900),
        'answeredSlots': answered_slots,
        'openQuestion': sanitize_outbound_text(patch.get('openQuestion') or existing.get('openQuestion'), 220),
        'commercialMomentum': compact_text(patch.get('commercialMomentum') or existing.get('commercialMomentum'), 60),
        'lastInboundText': compact_text(patch.get('lastInboundText') or existing.get('lastInboundText'), 400),
        'lastOutboundText': sanitize_outbound_text(patch.get('lastOutboundText') or existing.get('lastOutboundText'), 400),
        'lastRouteDecision': compact_text(patch.get('lastRouteDecision') or existing.get('lastRouteDecision'), 80),
        'lastProvider': compact_text(patch.get('lastProvider') or existing.get('lastProvider'), 80),
        'source': compact_text(patch.get('source') or existing.get('source') or 'router', 40),
    }
    now = utc_now()
    conn = db()
    conn.execute(
        '''
        INSERT INTO lead_memory (
          contact_key, customer_name, lead_stage, last_intent, product_focus, product_category,
          quantity_hint, city_hint, company_name, cnpj, last_objection, next_step, summary,
          answered_slots, open_question, commercial_momentum, last_inbound_text, last_outbound_text,
          last_route_decision, last_provider, updated_at, learned_at, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(contact_key) DO UPDATE SET
          customer_name = excluded.customer_name,
          lead_stage = excluded.lead_stage,
          last_intent = excluded.last_intent,
          product_focus = excluded.product_focus,
          product_category = excluded.product_category,
          quantity_hint = excluded.quantity_hint,
          city_hint = excluded.city_hint,
          company_name = excluded.company_name,
          cnpj = excluded.cnpj,
          last_objection = excluded.last_objection,
          next_step = excluded.next_step,
          summary = excluded.summary,
          answered_slots = excluded.answered_slots,
          open_question = excluded.open_question,
          commercial_momentum = excluded.commercial_momentum,
          last_inbound_text = excluded.last_inbound_text,
          last_outbound_text = excluded.last_outbound_text,
          last_route_decision = excluded.last_route_decision,
          last_provider = excluded.last_provider,
          updated_at = excluded.updated_at,
          learned_at = excluded.learned_at,
          source = excluded.source
        ''',
        (
            contact_key,
            merged['customerName'],
            merged['leadStage'],
            merged['lastIntent'],
            merged['productFocus'],
            merged['productCategory'],
            merged['quantityHint'],
            merged['cityHint'],
            merged['companyName'],
            merged['cnpj'],
            merged['lastObjection'],
            merged['nextStep'],
            merged['summary'],
            json.dumps(merged['answeredSlots'], ensure_ascii=False),
            merged['openQuestion'],
            merged['commercialMomentum'],
            merged['lastInboundText'],
            merged['lastOutboundText'],
            merged['lastRouteDecision'],
            merged['lastProvider'],
            now,
            now,
            merged['source'],
        ),
    )
    conn.commit()
    conn.close()
    merged['updatedAt'] = now
    merged['learnedAt'] = now
    return merged


def build_memory_guidance(memory: Dict) -> List[str]:
    if not isinstance(memory, dict) or not memory:
        return []
    lines: List[str] = []
    answered_summary = summarize_answered_slots(memory.get('answeredSlots') or {})
    if answered_summary:
        lines.append(f'Campos ja respondidos pelo lead: {answered_summary}. Nao pergunte novamente esses pontos.')
    if memory.get('openQuestion'):
        lines.append(f'Pergunta comercial em aberto: {memory["openQuestion"]}')
    if memory.get('nextStep'):
        lines.append(f'Proximo passo comercial salvo: {memory["nextStep"]}')
    if memory.get('summary'):
        lines.append(f'Resumo persistente da conversa: {compact_text(memory["summary"], 260)}')
    if memory.get('lastObjection'):
        lines.append(f'Objecao ativa do lead: {memory["lastObjection"]}')
    if memory.get('commercialMomentum'):
        lines.append(f'Momento comercial atual: {memory["commercialMomentum"]}')
    return lines[:6]


def get_lid_mapping(remote_jid: str) -> Dict:
    jid = normalize_lid_jid(remote_jid)
    if not jid:
        return {}
    cached = lid_cache.get(jid)
    if cached is not None:
        return cached
    conn = db()
    row = conn.execute(
        '''
        SELECT remote_jid, phone_number, resolved_jid, push_name, source, message_id, created_at, updated_at, last_seen_at
        FROM lid_mappings
        WHERE remote_jid = ?
        ''',
        (jid,),
    ).fetchone()
    if row:
        conn.execute('UPDATE lid_mappings SET last_seen_at = ? WHERE remote_jid = ?', (utc_now(), jid))
        conn.commit()
    conn.close()
    mapping = dict(row) if row else {}
    if mapping:
        lid_cache.put(jid, mapping)
    return mapping


def upsert_lid_mapping(remote_jid: str, phone_number: str, push_name: str = '', source: str = 'log_scan', message_id: str = '') -> Dict:
    jid = normalize_lid_jid(remote_jid)
    number = digits_only(phone_number)
    if not jid or not number:
        return {}
    resolved_jid = f'{number}@s.whatsapp.net'
    now = utc_now()
    conn = db()
    conn.execute(
        '''
        INSERT INTO lid_mappings (remote_jid, phone_number, resolved_jid, push_name, source, message_id, created_at, updated_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(remote_jid) DO UPDATE SET
          phone_number = excluded.phone_number,
          resolved_jid = excluded.resolved_jid,
          push_name = CASE WHEN excluded.push_name <> '' THEN excluded.push_name ELSE lid_mappings.push_name END,
          source = excluded.source,
          message_id = CASE WHEN excluded.message_id <> '' THEN excluded.message_id ELSE lid_mappings.message_id END,
          updated_at = excluded.updated_at,
          last_seen_at = excluded.last_seen_at
        ''',
        (jid, number, resolved_jid, str(push_name or '').strip(), source, str(message_id or '').strip(), now, now, now),
    )
    conn.commit()
    conn.close()
    mapping = {
        'remote_jid': jid,
        'phone_number': number,
        'resolved_jid': resolved_jid,
        'push_name': str(push_name or '').strip(),
        'source': source,
        'message_id': str(message_id or '').strip(),
        'updated_at': now,
    }
    lid_cache.put(jid, mapping)
    return mapping


def scan_evolution_logs_for_lid(remote_jid: str, message_id: str = '') -> Dict:
    jid = normalize_lid_jid(remote_jid)
    if not jid.endswith('@lid'):
        return {}
    lid_key = jid.replace('@lid', '')
    try:
        result = subprocess.run(
            [
                'docker', 'logs', 'evolution',
                '--since', f'{max(60, LID_LOG_SCAN_SECONDS)}s',
                '--tail', str(max(200, LID_LOG_SCAN_LINES)),
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=20,
        )
    except Exception:
        return {}

    haystack = '\n'.join([result.stdout or '', result.stderr or ''])
    if not haystack:
        return {}

    exact_regex = re.compile(
        r'"from":"(?P<jid>[^"]+@lid)".*?"id":"(?P<id>[^"]+)".*?"sender_pn":"(?P<number>\d+)@s\.whatsapp\.net"',
        re.IGNORECASE,
    )
    fallback_regex = re.compile(
        r'"from":"(?P<jid>[^"]+@lid)".*?"sender_pn":"(?P<number>\d+)@s\.whatsapp\.net"',
        re.IGNORECASE,
    )

    lines = [line for line in haystack.splitlines() if lid_key in line and '@lid' in line]
    lines.reverse()

    if message_id:
        for line in lines:
            match = exact_regex.search(line)
            if not match:
                continue
            if normalize_lid_jid(match.group('jid')) != jid:
                continue
            if str(match.group('id') or '').strip() != str(message_id).strip():
                continue
            return upsert_lid_mapping(jid, match.group('number'), source='log_scan_exact', message_id=message_id)

    for line in lines:
        match = exact_regex.search(line) or fallback_regex.search(line)
        if not match:
            continue
        if normalize_lid_jid(match.group('jid')) != jid:
            continue
        return upsert_lid_mapping(jid, match.group('number'), source='log_scan_fallback', message_id=message_id)

    return {}


def resolve_recipient_payload(payload: Dict) -> Dict:
    merged = dict(payload or {})
    remote_jid = normalize_lid_jid(merged.get('remoteJid'))
    message_id = str(merged.get('messageId') or '').strip()
    push_name = str(merged.get('pushName') or '').strip()
    number = digits_only(merged.get('number'))
    resolved_jid = str(merged.get('resolvedJid') or '').strip().lower()
    resolution_status = str(merged.get('resolutionStatus') or '').strip() or 'passthrough'

    if remote_jid.endswith('@s.whatsapp.net'):
        number = digits_only(remote_jid.replace('@s.whatsapp.net', ''))
        resolved_jid = remote_jid
        resolution_status = 'resolved_direct'
    elif remote_jid.endswith('@lid'):
        mapping = get_lid_mapping(remote_jid)
        if not mapping:
            mapping = scan_evolution_logs_for_lid(remote_jid, message_id=message_id)
        if mapping:
            number = digits_only(mapping.get('phone_number'))
            resolved_jid = str(mapping.get('resolved_jid') or '').strip().lower() or f'{number}@s.whatsapp.net'
            resolution_status = 'resolved_from_lid_log'
        else:
            resolution_status = resolution_status or 'unresolved_lid'

    send_target = number
    contact_key = number or remote_jid or digits_only(push_name)

    merged.update({
        'remoteJid': remote_jid,
        'messageId': message_id,
        'pushName': push_name,
        'number': number,
        'customerNumber': number,
        'resolvedJid': resolved_jid,
        'resolutionStatus': resolution_status,
        'sendTarget': send_target,
        'contactKey': contact_key,
        'isLid': remote_jid.endswith('@lid'),
    })
    return merged


def ensure_collection(vector_size: int):
    global COLLECTION_READY, COLLECTION_DIM
    client = get_qdrant()
    if client is None:
        return
    if COLLECTION_READY and COLLECTION_DIM == vector_size:
        return
    collections = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
    else:
        info = client.get_collection(QDRANT_COLLECTION)
        current_size = int(info.config.params.vectors.size)
        if current_size != vector_size:
            client.recreate_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
    COLLECTION_READY = True
    COLLECTION_DIM = vector_size


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='ignore')


def extract_xml_text(raw: bytes) -> str:
    try:
        root = ET.fromstring(raw)
    except Exception:
        return ''
    parts: List[str] = []
    for node in root.iter():
        tag = str(getattr(node, 'tag', ''))
        if node.text and tag.endswith('}t'):
            value = re.sub(r'\s+', ' ', str(node.text)).strip()
            if value:
                parts.append(value)
    return '\n'.join(parts)


def read_docx_text(path: Path) -> str:
    parts: List[str] = []
    with zipfile.ZipFile(path, 'r') as zf:
        for name in zf.namelist():
            if name.startswith('word/') and name.endswith('.xml'):
                content = extract_xml_text(zf.read(name))
                if content:
                    parts.append(content)
    return '\n'.join(parts)


def read_xlsx_text(path: Path) -> str:
    rows: List[str] = []
    with zipfile.ZipFile(path, 'r') as zf:
        shared_strings: List[str] = []
        if 'xl/sharedStrings.xml' in zf.namelist():
            try:
                root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
                for node in root.iter():
                    if str(getattr(node, 'tag', '')).endswith('}t') and node.text:
                        shared_strings.append(str(node.text))
            except Exception:
                shared_strings = []

        for sheet_name in [n for n in zf.namelist() if n.startswith('xl/worksheets/') and n.endswith('.xml')]:
            try:
                root = ET.fromstring(zf.read(sheet_name))
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
                                value = shared_strings[idx]
                            except Exception:
                                value = raw
                        else:
                            value = raw
                value = re.sub(r'\s+', ' ', str(value)).strip()
                if value:
                    rows.append(value)
    return '\n'.join(rows)


def read_rtf_text(path: Path) -> str:
    raw = safe_read_text(path)
    text = re.sub(r'\\[a-zA-Z]+\d* ?', ' ', raw)
    text = text.replace('{', ' ').replace('}', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def read_pdf_text(path: Path) -> str:
    if HAS_PYMUPDF:
        try:
            doc = pymupdf.open(str(path))
            pages = []
            for page in doc:
                text = page.get_text().strip()
                if text:
                    pages.append(text)
            doc.close()
            result = '\n\n'.join(pages)
            if result.strip():
                log.info('pdf_parsed', path=str(path), pages=len(pages), chars=len(result))
                return result
        except Exception as exc:
            log.warning('pdf_pymupdf_failed', path=str(path), error=str(exc))
    # Fallback: regex extraction from raw bytes
    raw = path.read_bytes()
    snippets: List[str] = []
    for match in re.finditer(rb'\(([^()]{12,900})\)', raw):
        piece = match.group(1)
        text = piece.decode('latin1', errors='ignore')
        text = re.sub(r'\\[nrt]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) >= 16:
            snippets.append(text)
    dedup: List[str] = []
    seen = set()
    for item in snippets:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)
        if len(dedup) >= 800:
            break
    return '\n'.join(dedup)


def extract_text_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == '.docx':
        return read_docx_text(path)
    if ext == '.xlsx':
        return read_xlsx_text(path)
    if ext == '.pdf':
        return read_pdf_text(path)
    if ext == '.rtf':
        return read_rtf_text(path)
    if ext in TEXT_EXTENSIONS:
        return safe_read_text(path)
    return ''


def tokenize_words(text: str) -> List[str]:
    return [w for w in normalize_ascii(text).split() if len(w) >= 3 and w not in STOPWORDS]


def chunk_text(text: str, target_tokens: int = 420, min_tokens: int = 300, max_tokens: int = 800, overlap_tokens: int = 80) -> List[str]:
    paragraphs = [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n{2,}', text) if re.sub(r'\s+', ' ', p).strip()]
    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = len(tokenize_words(para))
        if para_tokens == 0:
            continue
        if para_tokens >= max_tokens:
            words = para.split()
            step = max(1, target_tokens - overlap_tokens)
            for start in range(0, len(words), step):
                piece = ' '.join(words[start:start + target_tokens])
                if len(tokenize_words(piece)) >= min_tokens:
                    chunks.append(piece)
            continue

        if current_tokens + para_tokens > target_tokens and current_tokens >= min_tokens:
            chunks.append('\n'.join(current))
            overlap = []
            if overlap_tokens > 0:
                overlap_words = ' '.join(current).split()[-overlap_tokens:]
                overlap = [' '.join(overlap_words)] if overlap_words else []
            current = overlap + [para]
            current_tokens = len(tokenize_words(' '.join(current)))
        else:
            current.append(para)
            current_tokens += para_tokens

    if current and current_tokens >= min_tokens:
        chunks.append('\n'.join(current))
    elif current and not chunks:
        chunks.append('\n'.join(current))

    cleaned = []
    for item in chunks:
        tokens = len(tokenize_words(item))
        if tokens == 0:
            continue
        cleaned.append(item[:4000])
    return cleaned[:64]


def embed_texts(texts: List[str]) -> List[List[float]]:
    global EMBEDDINGS_AVAILABLE
    if not openai_client:
        raise RuntimeError('OPENAI_API_KEY not configured for embeddings')
    if not texts:
        return []
    if not embed_limiter.wait(timeout=5.0):
        app.logger.warning('Embedding rate-limit exceeded — falling back to lexical search')
        EMBEDDINGS_AVAILABLE = False
        raise RuntimeError('Embedding rate-limit exceeded')
    try:
        response = openai_client.embeddings.create(
            model=OPENAI_EMBED_MODEL,
            input=texts,
        )
        EMBEDDINGS_AVAILABLE = True
        return [item.embedding for item in response.data]
    except Exception:
        EMBEDDINGS_AVAILABLE = False
        raise


INTENT_RULES = [
    ('atacado_quantidade', ['atacado', 'revenda', 'lote', 'quantidade', 'revender']),
    ('preco_orcamento', ['preco', 'valor', 'orcamento', 'cotacao', 'quanto custa']),
    ('prazo_entrega', ['prazo', 'entrega', 'frete', 'envio']),
    ('institucional_empresa', ['classe couro', 'sua empresa', 'sobre a empresa', 'quem sao voces', 'sobre voces']),
    ('produto_catalogo', ['catalogo', 'produto', 'carteira', 'carteiras', 'cinto', 'cintos', 'bolsa', 'bolsas', 'mochila', 'mochilas']),
    ('pagamento', ['pagamento', 'pix', 'boleto', 'cartao', 'parcelamento']),
    ('saudacao', ['oi', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'e ai']),
    ('agradecimento', ['obrigado', 'obrigada', 'valeu', 'agradeco', 'grato', 'grata']),
    ('pos_venda_reclamacao', ['reclamacao', 'problema', 'defeito', 'errado', 'nao chegou', 'nao recebi']),
    ('troca_devolucao', ['troca', 'trocar', 'devolucao', 'devolver', 'garantia']),
]


def detect_intent(text: str) -> str:
    result = detect_intent_scored(text)
    return result['intent']


def detect_intent_scored(text: str) -> Dict:
    norm = normalize_ascii(text)
    best_intent = 'geral'
    best_score = 0.0
    best_matches = []
    all_matches = []

    for intent, keywords in INTENT_RULES:
        matched = [k for k in keywords if k in norm]
        if not matched:
            continue
        hit_ratio = len(matched) / len(keywords)
        score = round(min(1.0, 0.5 + hit_ratio * 0.5), 3)
        all_matches.append({'intent': intent, 'confidence': score, 'keywords': matched})
        if score > best_score:
            best_intent = intent
            best_score = score
            best_matches = matched

    return {
        'intent': best_intent,
        'confidence': best_score if best_score > 0 else 0.1,
        'matchedKeywords': best_matches,
        'allMatches': all_matches,
    }


def classify_complexity(text: str) -> str:
    norm = normalize_ascii(text)
    token_count = len(tokenize_words(text))
    if token_count <= 6 and re.fullmatch(r'(oi|ola|bom dia|boa tarde|boa noite|obrigado|obrigada|valeu)', norm):
        return 'simple'
    if any(k in norm for k in ['cnpj', 'revenda', 'revender', 'representante', 'condicao comercial', 'orcamento']) and token_count >= 8:
        return 'complex'
    if token_count >= 22:
        return 'complex'
    if token_count <= 8:
        return 'simple'
    return 'medium'


def score_lead(text: str) -> int:
    norm = normalize_ascii(text)
    score = 0
    if any(k in norm for k in ['revenda', 'revender', 'atacado', 'lojista', 'representante']):
        score += 30
    if re.search(r'\b\d{14}\b', re.sub(r'\D', '', text)):
        score += 25
    if any(k in norm for k in ['loja fisica', 'instagram', 'cidade', 'telefone']):
        score += 15
    if re.search(r'\b\d+\b', norm):
        score += 10
    if any(k in norm for k in ['prazo', 'entrega', 'quantidade', 'volume']):
        score += 10
    if any(k in norm for k in ['couro', 'carteira', 'cinto', 'bolsa', 'mochila']):
        score += 10
    return max(0, min(100, score))


def _cache_tokens(text: str) -> set:
    tokens = [t for t in tokenize_words(text) if t and len(t) > 2 and t not in STOPWORDS]
    return set(tokens)


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a.intersection(b))
    if inter == 0:
        return 0.0
    return inter / max(1, len(a.union(b)))


def cache_lookup(normalized_message: str, intent: str = '') -> Dict:
    conn = db()
    row = conn.execute(
        '''
        SELECT normalized_message, reply_text, intent, confidence, hit_count
        FROM response_cache
        WHERE normalized_message = ? AND active = 1
        ''',
        (normalized_message,),
    ).fetchone()
    if row:
        safe_reply = sanitize_outbound_text(row['reply_text'] or '', MAX_CACHE_REPLY_CHARS)
        now = utc_now()
        conn.execute(
            '''
            UPDATE response_cache
            SET hit_count = hit_count + 1, last_hit_at = ?, updated_at = ?, reply_text = ?, active = ?
            WHERE normalized_message = ?
            ''',
            (now, now, safe_reply, 1 if safe_reply else 0, normalized_message),
        )
        conn.commit()
        conn.close()
        if not safe_reply:
            return {}
        out = dict(row)
        out['reply_text'] = safe_reply
        out['lookupType'] = 'exact'
        return out

    if not CACHE_SEMANTIC_ENABLED:
        conn.close()
        return {}

    params = []
    where_intent = ''
    if intent and intent != 'geral':
        where_intent = 'AND intent = ?'
        params.append(intent)
    params.append(max(20, CACHE_SEMANTIC_CANDIDATE_LIMIT))
    candidates = conn.execute(
        f'''
        SELECT normalized_message, reply_text, intent, confidence, hit_count
        FROM response_cache
        WHERE active = 1 {where_intent}
        ORDER BY hit_count DESC, updated_at DESC
        LIMIT ?
        ''',
        tuple(params),
    ).fetchall()
    base_tokens = _cache_tokens(normalized_message)
    best = None
    best_score = 0.0
    for cand in candidates:
        cand_msg = str(cand['normalized_message'] or '')
        score = _jaccard(base_tokens, _cache_tokens(cand_msg))
        if score > best_score:
            best_score = score
            best = cand
    if best and best_score >= CACHE_SEMANTIC_THRESHOLD:
        matched_msg = str(best['normalized_message'])
        safe_reply = sanitize_outbound_text(best['reply_text'] or '', MAX_CACHE_REPLY_CHARS)
        now = utc_now()
        conn.execute(
            '''
            UPDATE response_cache
            SET hit_count = hit_count + 1, last_hit_at = ?, updated_at = ?, reply_text = ?, active = ?
            WHERE normalized_message = ?
            ''',
            (now, now, safe_reply, 1 if safe_reply else 0, matched_msg),
        )
        conn.commit()
        conn.close()
        if not safe_reply:
            return {}
        out = dict(best)
        out['reply_text'] = safe_reply
        out['lookupType'] = 'semantic'
        out['semanticScore'] = round(float(best_score), 4)
        return out

    conn.close()
    return {}


def build_learning_memory_patch(payload: Dict, inbound: str, reply: str, intent: str) -> Dict:
    structured = payload.get('extractedEntities')
    if not isinstance(structured, dict):
        structured = payload.get('llmStructuredData') if isinstance(payload.get('llmStructuredData'), dict) else {}
    memory_update = payload.get('customerMemoryUpdate') if isinstance(payload.get('customerMemoryUpdate'), dict) else {}

    product_focus = compact_text(
        payload.get('productFocusResolved') or structured.get('product_focus') or structured.get('productFocus'),
        90,
    )
    product_category = compact_text(
        payload.get('productCategoryDetected') or structured.get('categoria_produto') or structured.get('productCategory'),
        90,
    )
    last_objection = compact_text(
        structured.get('objecao_principal') or structured.get('objection') or structured.get('objectionHint'),
        180,
    )
    customer_name = compact_text(
        payload.get('customerName') or structured.get('nome_contato') or structured.get('nome') or structured.get('customer_name'),
        120,
    )
    company_name = compact_text(
        structured.get('nome_empresa') or structured.get('companyName'),
        140,
    )
    cnpj = digits_only(structured.get('cnpj') or payload.get('cnpj') or '')
    quantity_hint = infer_quantity_hint(inbound, structured)
    city_hint = infer_city_hint(inbound, structured)
    lead_stage = compact_text(payload.get('leadStage') or structured.get('etapa_sugerida'), 60)
    next_step = compact_text(
        memory_update.get('next_step') or structured.get('proximo_passo') or payload.get('followUpQuestion'),
        220,
    )
    summary = compact_text(
        memory_update.get('notes') or payload.get('conversationSummary'),
        900,
    )

    answered_slots = {}
    for key, value in {
        'productFocus': product_focus,
        'productCategory': product_category,
        'quantityHint': quantity_hint,
        'cityHint': city_hint,
        'companyName': company_name,
        'cnpj': cnpj,
        'customerName': customer_name,
        'objection': last_objection,
    }.items():
        clean = compact_text(value, 120)
        if clean:
            answered_slots[key] = clean

    commercial_momentum = 'explorando'
    stage_norm = normalize_ascii(lead_stage)
    intent_norm = normalize_ascii(intent)
    if stage_norm in {'fechamento', 'negociacao', 'negociacao avancada'}:
        commercial_momentum = 'fechando'
    elif stage_norm in {'proposta', 'qualificando'} or intent_norm in {'preco_orcamento', 'atacado_quantidade'}:
        commercial_momentum = 'avancando'
    elif product_focus or quantity_hint or city_hint:
        commercial_momentum = 'qualificando'

    return {
        'customerName': customer_name,
        'leadStage': lead_stage,
        'lastIntent': intent,
        'productFocus': product_focus,
        'productCategory': product_category,
        'quantityHint': quantity_hint,
        'cityHint': city_hint,
        'companyName': company_name,
        'cnpj': cnpj,
        'lastObjection': last_objection,
        'nextStep': next_step,
        'summary': summary,
        'answeredSlots': answered_slots,
        'openQuestion': extract_last_question(reply),
        'commercialMomentum': commercial_momentum,
        'lastInboundText': inbound,
        'lastOutboundText': reply,
        'lastRouteDecision': compact_text(payload.get('routeDecision'), 80),
        'lastProvider': compact_text(payload.get('llmProvider') or payload.get('provider'), 80),
        'source': 'learn_response',
    }


def learn_response(payload: Dict) -> Dict:
    inbound = str(payload.get('inboundTextOriginal') or payload.get('inboundText') or '').strip()
    reply = sanitize_outbound_text(payload.get('replyText') or '', MAX_CACHE_REPLY_CHARS)
    intent = str(payload.get('intent') or '').strip() or detect_intent(inbound)
    confidence = float(payload.get('confidence') or 0)
    normalized_message = normalize_ascii(inbound)
    contact_key = str(payload.get('number') or payload.get('contactKey') or '').strip()
    route_decision = compact_text(payload.get('routeDecision'), 80)
    memory_patch = build_learning_memory_patch(payload, inbound, reply, intent)
    memory_snapshot = upsert_lead_memory(contact_key, memory_patch) if contact_key and (inbound or reply) else {}

    now = utc_now()
    if contact_key:
        conn = db()
        conn.execute(
            '''
            INSERT INTO learning_events (
              contact_key, intent, lead_stage, route_decision, inbound_text, reply_text,
              structured_data, memory_update, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                contact_key,
                intent,
                str(memory_snapshot.get('leadStage') or ''),
                route_decision,
                inbound[:1200],
                reply,
                json.dumps(payload.get('extractedEntities') or payload.get('llmStructuredData') or {}, ensure_ascii=False),
                json.dumps(payload.get('customerMemoryUpdate') or {}, ensure_ascii=False),
                now,
            ),
        )
        conn.commit()
        conn.close()

    if contact_key and reply:
        record_message(contact_key, 'outbound', reply, intent, route_decision=route_decision or 'reply_sent')

    stored = False
    reason = 'stored'
    reply_norm = normalize_ascii(reply)
    if len(normalized_message) < 8 or len(reply) < 16:
        reason = 'too_short'
    elif normalized_message in {'sim', 'nao', 'não', 'ok', 'obrigado', 'obrigada', 'oi', 'ola', 'olá'}:
        reason = 'ambiguous_shortcut'
    elif bool(payload.get('needsHuman')):
        reason = 'needs_human'
    elif confidence < CACHE_MIN_CONFIDENCE_LEARN:
        reason = 'low_confidence'
    elif intent not in SAFE_CACHE_INTENTS:
        reason = 'unsafe_intent'
    elif any(x in reply_norm for x in [
        'peco um instante',
        'assumo seu atendimento pessoalmente',
        'nao consegui responder agora',
        'atendimento automatico ativo',
        'alto volume no momento',
    ]):
        reason = 'fallback_reply'
    else:
        cache_reply = sanitize_outbound_text(reply, MAX_CACHE_REPLY_CHARS)
        if not cache_reply:
            reason = 'sanitized_empty'
            return {
                'stored': False,
                'reason': reason,
                'normalizedMessage': normalized_message,
                'leadMemoryUpdated': bool(memory_snapshot),
                'memoryGuidance': build_memory_guidance(memory_snapshot),
            }
        conn = db()
        conn.execute(
            '''
            INSERT INTO response_cache (normalized_message, reply_text, intent, confidence, source, active, hit_count, created_at, updated_at, last_hit_at)
            VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?, NULL)
            ON CONFLICT(normalized_message) DO UPDATE SET
              reply_text = excluded.reply_text,
              intent = excluded.intent,
              confidence = excluded.confidence,
              source = excluded.source,
              active = 1,
              updated_at = excluded.updated_at
            ''',
            (normalized_message, cache_reply, intent, confidence, 'auto_learn', now, now),
        )
        conn.commit()
        conn.close()
        stored = True

    return {
        'stored': stored,
        'reason': reason,
        'normalizedMessage': normalized_message,
        'leadMemoryUpdated': bool(memory_snapshot),
        'memoryGuidance': build_memory_guidance(memory_snapshot),
    }


def log_route(payload: Dict, route_decision: str, message_complexity: str, cache_hit: bool, lead_score: int, rag_hits: List[Dict]):
    conn = db()
    top_score = float(rag_hits[0]['score']) if rag_hits else 0.0
    conn.execute(
        '''
        INSERT INTO route_logs (number, push_name, inbound_text, normalized_message, route_decision, message_complexity, cache_hit, lead_score, rag_hit_count, rag_top_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            str(payload.get('number') or ''),
            str(payload.get('pushName') or ''),
            str(payload.get('inboundText') or ''),
            normalize_ascii(str(payload.get('inboundText') or '')),
            route_decision,
            message_complexity,
            1 if cache_hit else 0,
            int(lead_score),
            len(rag_hits),
            top_score,
            utc_now(),
        ),
    )
    conn.commit()
    conn.close()


def search_rag(query_text: str, limit: int = 5) -> List[Dict]:
    global COLLECTION_READY
    client = get_qdrant()
    if client is not None and not COLLECTION_READY:
        collections = [c.name for c in client.get_collections().collections]
        COLLECTION_READY = QDRANT_COLLECTION in collections
    if client is not None and COLLECTION_READY and openai_client and EMBEDDINGS_AVAILABLE:
        try:
            vector = embed_texts([query_text])[0]
            results = client.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=vector,
                limit=limit,
                with_payload=True,
            )
            hits = []
            for item in results:
                payload = item.payload or {}
                hits.append({
                    'score': float(item.score),
                    'fileName': str(payload.get('file_name') or ''),
                    'filePath': str(payload.get('file_path') or ''),
                    'text': str(payload.get('text') or '').strip(),
                    'source': 'vector',
                })
            if hits:
                return hits
        except Exception as exc:
            log.warning('rag_vector_search_failed', query=query_text[:60], error=str(exc))
    return lexical_search(query_text, limit=limit)


def lexical_search(query_text: str, limit: int = 5) -> List[Dict]:
    query_words = tokenize_words(query_text)
    if not query_words:
        return []
    query_set = set(query_words)
    conn = db()
    rows = conn.execute(
        '''
        SELECT rc.file_path, rc.file_name, rc.chunk_text, rc.normalized_text
        FROM rag_chunks rc
        JOIN rag_documents rd ON rd.file_path = rc.file_path
        WHERE rd.status = 'active'
        '''
    ).fetchall()
    conn.close()

    if not rows:
        return []

    # Build BM25 index from all active chunks
    corpus_tokens = []
    valid_rows = []
    for row in rows:
        normalized = str(row['normalized_text'] or '')
        if not normalized:
            continue
        tokens = normalized.split()
        if not tokens:
            continue
        corpus_tokens.append(tokens)
        valid_rows.append(row)

    if not corpus_tokens:
        return []

    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(query_words)

    # Normalize BM25 scores to 0-1 range
    max_score = max(scores) if len(scores) > 0 else 1.0
    if max_score <= 0:
        max_score = 1.0

    scored = []
    for idx, bm25_score in enumerate(scores):
        if bm25_score <= 0:
            continue
        norm_score = min(0.99, bm25_score / max_score)
        row = valid_rows[idx]
        scored.append({
            'score': round(norm_score, 4),
            'fileName': str(row['file_name'] or ''),
            'filePath': str(row['file_path'] or ''),
            'text': str(row['chunk_text'] or '').strip(),
            'source': 'lexical_bm25',
        })

    scored.sort(key=lambda item: item['score'], reverse=True)
    if scored:
        log.debug('lexical_bm25_search', query=query_text[:80], results=len(scored[:limit]))
        return scored[:limit]

    overlap_hits = []
    for row in valid_rows:
        normalized = str(row['normalized_text'] or '')
        row_tokens = set(normalized.split())
        if not row_tokens:
            continue
        overlap = query_set & row_tokens
        if not overlap:
            continue
        score = round(len(overlap) / max(1, len(query_set)), 4)
        overlap_hits.append({
            'score': score,
            'fileName': str(row['file_name'] or ''),
            'filePath': str(row['file_path'] or ''),
            'text': str(row['chunk_text'] or '').strip(),
            'source': 'lexical_overlap',
        })

    overlap_hits.sort(key=lambda item: item['score'], reverse=True)
    if overlap_hits:
        log.debug('lexical_overlap_search', query=query_text[:80], results=len(overlap_hits[:limit]))
        return overlap_hits[:limit]

    log.debug('lexical_bm25_search', query=query_text[:80], results=len(scored[:limit]))
    return []


def route_message(payload: Dict) -> Dict:
    resolved_payload = resolve_recipient_payload(payload)
    inbound_text = str(resolved_payload.get('inboundText') or '').strip()
    audio_transcription = {'ok': False, 'reason': 'not_needed', 'text': ''}
    if not inbound_text:
        audio_transcription = transcribe_inbound_audio(resolved_payload)
        if audio_transcription.get('ok') and audio_transcription.get('text'):
            inbound_text = str(audio_transcription.get('text') or '').strip()
            resolved_payload['inboundText'] = inbound_text
    if not inbound_text:
        result = {
            'routeDecision': 'audio_untranscribed',
            'cacheHit': False,
            'cachedReplyText': '',
            'routeIntent': 'geral',
            'messageComplexity': 'simple',
            'leadScore': 0,
            'ragContextLines': [],
            'ragContextSummary': '',
            'ragTopScore': 0,
            'conversationHistory': [],
            'contextCarryover': {
                'carriedIntent': '',
                'effectiveIntent': 'geral',
                'isContextCarry': False,
                'maxLeadScore': 0,
                'conversationTurns': 0,
            },
            'audioTranscription': audio_transcription,
            'llmReplyText': 'Nao consegui entender seu audio agora. Pode me enviar novamente ou, se preferir, me escrever em texto para eu te responder com prioridade.',
            'llmProvider': 'system',
            'llmModel': OPENAI_TRANSCRIBE_MODEL,
            'llmLatencyMs': 0,
            'llmStructuredData': {},
            'llmLeadScore': {},
        }
        log_route(resolved_payload, 'audio_untranscribed', 'simple', False, 0, [])
        return result
    maybe_refresh_knowledge()
    normalized_message = normalize_ascii(inbound_text)
    contact_key = str(resolved_payload.get('contactKey') or '').strip()
    intent = detect_intent(inbound_text)
    complexity = classify_complexity(inbound_text)
    lead_score = score_lead(inbound_text)

    lead_memory = get_lead_memory(contact_key)
    conversation = get_conversation_history(contact_key)
    context = build_context_carryover(conversation, intent, inbound_text, lead_memory)
    effective_intent = context['effectiveIntent']

    record_message(contact_key, 'inbound', inbound_text, effective_intent, complexity, lead_score)
    lead_memory = upsert_lead_memory(contact_key, {
        'lastIntent': effective_intent,
        'lastInboundText': inbound_text,
        'source': 'route',
    }) if contact_key else {}
    memory_guidance = build_memory_guidance(lead_memory)

    cached = cache_lookup(normalized_message, effective_intent)
    if cached:
        lookup_type = str(cached.get('lookupType') or 'exact')
        route_decision = 'cache_semantic' if lookup_type == 'semantic' else 'cache'
        result = {
            'routeDecision': route_decision,
            'cacheHit': True,
            'cachedReplyText': sanitize_outbound_text(cached.get('reply_text') or '', MAX_CACHE_REPLY_CHARS),
            'routeIntent': str(cached.get('intent') or effective_intent),
            'cacheLookupType': lookup_type,
            'cacheSemanticScore': float(cached.get('semanticScore') or 0),
            'messageComplexity': complexity,
            'leadScore': lead_score,
            'ragContextLines': [],
            'ragContextSummary': '',
            'ragTopScore': 0,
            'conversationHistory': conversation,
            'contextCarryover': context,
            'leadMemory': lead_memory,
            'memoryGuidance': memory_guidance,
            'audioTranscription': audio_transcription,
        }
        log_route(resolved_payload, route_decision, complexity, True, lead_score, [])
        return result

    rag_limit = 5 if complexity == 'complex' else 3
    rag_hits = search_rag(inbound_text, limit=rag_limit) if complexity in {'medium', 'complex'} else []
    strong_hits = [
        h for h in rag_hits
        if (
            (h.get('source') == 'vector' and h['score'] >= 0.72) or
            (h.get('source') != 'vector' and h['score'] >= 0.34)
        )
    ]
    rag_lines = [
        f"[{item['fileName']}] {item['text'][:280]}"
        for item in strong_hits[:5]
    ]
    rag_summary = ' | '.join(rag_lines[:3])

    if complexity == 'simple':
        route_decision = 'gpt_direct'
    elif strong_hits:
        route_decision = 'rag_gpt'
    else:
        route_decision = 'gpt_direct'

    # --- Dual-LLM: generate reply + extraction (skip if no provider available) ---
    llm_reply_text = ''
    llm_provider = 'none'
    llm_model = 'none'
    llm_latency_ms = 0
    llm_structured = {}
    ai_lead_score = {}

    _has_any_llm = bool(multi_llm.ANTHROPIC_API_KEY or multi_llm.OPENAI_API_KEY)
    if _has_any_llm:
        try:
            llm_result = multi_llm.generate_sales_reply(
                system_prompt=SDR_SYSTEM_PROMPT,
                user_message=inbound_text,
                conversation_history=conversation,
                max_tokens=300,
                rag_context=rag_summary,
                memory_context='\n'.join(memory_guidance),
            )
            llm_reply_text = sanitize_outbound_text(llm_result.get('text', ''), MAX_CACHE_REPLY_CHARS)
            llm_provider = llm_result.get('provider', 'none')
            llm_model = llm_result.get('model', 'none')
            llm_latency_ms = llm_result.get('latency_ms', 0)
        except Exception as exc:
            log.warning('dual_llm_reply_failed', error=str(exc))

        try:
            llm_structured = multi_llm.extract_structured(inbound_text)
        except Exception as exc:
            log.warning('dual_llm_extract_failed', error=str(exc))

        try:
            ai_lead_score = multi_llm.analyze_lead_score(
                conversation_history=conversation,
                current_message=inbound_text,
                keyword_score=lead_score,
            )
            if ai_lead_score.get('score'):
                lead_score = max(lead_score, int(ai_lead_score['score']))
        except Exception as exc:
            log.warning('dual_llm_lead_score_failed', error=str(exc))
    else:
        log.debug('dual_llm_skipped', reason='no_api_keys_configured')

    # Use dual-LLM route decision labels
    if llm_reply_text and llm_provider == 'anthropic':
        route_decision = 'claude_direct' if not strong_hits else 'rag_claude'
    elif llm_reply_text and llm_provider == 'openai':
        route_decision = 'gpt_direct' if not strong_hits else 'rag_gpt'

    result = {
        'routeDecision': route_decision,
        'cacheHit': False,
        'cachedReplyText': '',
        'routeIntent': effective_intent,
        'messageComplexity': complexity,
        'leadScore': lead_score,
        'ragContextLines': rag_lines,
        'ragContextSummary': rag_summary,
        'ragTopScore': float(strong_hits[0]['score']) if strong_hits else 0,
        'conversationHistory': conversation,
        'contextCarryover': context,
        'leadMemory': lead_memory,
        'memoryGuidance': memory_guidance,
        'audioTranscription': audio_transcription,
        # Dual-LLM fields
        'llmReplyText': sanitize_outbound_text(llm_reply_text, MAX_CACHE_REPLY_CHARS),
        'llmProvider': llm_provider,
        'llmModel': llm_model,
        'llmLatencyMs': llm_latency_ms,
        'llmStructuredData': llm_structured,
        'llmLeadScore': ai_lead_score,
    }
    log_route(resolved_payload, route_decision, complexity, False, lead_score, strong_hits)
    return result


def file_is_indexable(path: Path) -> bool:
    if path.suffix.lower() not in INDEXABLE_EXTENSIONS:
        return False
    return not any(part in SKIP_DIR_NAMES for part in path.parts)


def iter_docs() -> List[Path]:
    if not ML_DIR.exists():
        return []
    docs = []
    for path in ML_DIR.rglob('*'):
        if path.is_dir():
            continue
        if file_is_indexable(path):
            docs.append(path)
    return docs


def upsert_points(points: List[models.PointStruct]):
    client = get_qdrant()
    if client is None:
        return
    if not points:
        return
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)


def normalize_qdrant_point_id(value: str):
    raw = str(value or '').strip().lower()
    if not raw:
        return ''
    if re.fullmatch(r'[0-9a-f]{64}', raw):
        return str(uuid.UUID(raw[:32]))
    return raw


def delete_points(point_ids: List[str]):
    client = get_qdrant()
    if client is None:
        return
    if not point_ids:
        return
    normalized_ids = [normalize_qdrant_point_id(point_id) for point_id in point_ids if normalize_qdrant_point_id(point_id)]
    if not normalized_ids:
        return
    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=models.PointIdsList(points=normalized_ids),
    )


def ingest_document(path: Path):
    text = extract_text_from_file(path)
    text = re.sub(r'\s+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if len(text) < 120:
        return

    file_hash = sha_text(text)
    modified = path.stat().st_mtime
    conn = db()
    try:
        _ingest_document_inner(conn, path, text, file_hash, modified)
    finally:
        conn.close()


def _ingest_document_inner(conn, path: Path, text: str, file_hash: str, modified: float):
    existing = conn.execute('SELECT file_hash FROM rag_documents WHERE file_path = ?', (str(path),)).fetchone()
    if existing and str(existing['file_hash']) == file_hash:
        return

    chunks = chunk_text(text)
    if not chunks:
        return

    old_chunk_rows = conn.execute('SELECT chunk_id FROM rag_chunks WHERE file_path = ?', (str(path),)).fetchall()
    old_chunk_ids = [str(r['chunk_id']) for r in old_chunk_rows]

    points: List[models.PointStruct] = []
    now = utc_now()
    new_chunk_ids: List[str] = []
    vectors: List[List[float]] = []
    vector_mode = False
    try:
        vectors = embed_texts(chunks)
        if vectors:
            ensure_collection(len(vectors[0]))
            vector_mode = True
    except Exception as exc:
        log.warning('embed_for_ingest_failed', error=str(exc))
        vectors = []
        vector_mode = False

    for idx, chunk in enumerate(chunks, start=1):
        chunk_hash = sha_text(f'{file_hash}:{idx}:{chunk}')
        chunk_id = normalize_qdrant_point_id(chunk_hash)
        new_chunk_ids.append(chunk_id)
        token_count = len(tokenize_words(chunk))
        if vector_mode:
            points.append(
                models.PointStruct(
                    id=chunk_id,
                    vector=vectors[idx - 1],
                    payload={
                        'file_name': path.name,
                        'file_path': str(path),
                        'chunk_index': idx,
                        'text': chunk[:3500],
                        'token_count': token_count,
                        'updated_at': now,
                    },
                )
            )
        conn.execute(
            '''
            INSERT INTO rag_chunks (chunk_id, file_path, file_name, chunk_hash, chunk_text, normalized_text, token_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
              file_name = excluded.file_name,
              chunk_text = excluded.chunk_text,
              normalized_text = excluded.normalized_text,
              token_count = excluded.token_count,
              updated_at = excluded.updated_at
            ''',
            (chunk_id, str(path), path.name, chunk_hash, chunk[:3500], normalize_ascii(chunk)[:3500], token_count, now, now),
        )

    if vector_mode:
        upsert_points(points)
    stale_ids = [cid for cid in old_chunk_ids if cid not in new_chunk_ids]
    if stale_ids:
        delete_points(stale_ids)
        conn.executemany('DELETE FROM rag_chunks WHERE chunk_id = ?', [(cid,) for cid in stale_ids])

    conn.execute(
        '''
        INSERT INTO rag_documents (file_path, file_name, extension, file_hash, last_modified, chunk_count, indexed_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        ON CONFLICT(file_path) DO UPDATE SET
          file_name = excluded.file_name,
          extension = excluded.extension,
          file_hash = excluded.file_hash,
          last_modified = excluded.last_modified,
          chunk_count = excluded.chunk_count,
          indexed_at = excluded.indexed_at,
          status = 'active'
        ''',
        (str(path), path.name, path.suffix.lower(), file_hash, modified, len(chunks), now),
    )
    conn.commit()


def purge_missing_docs(current_paths: List[Path]):
    current_set = {str(p) for p in current_paths}
    conn = db()
    try:
        rows = conn.execute('SELECT file_path FROM rag_documents WHERE status = "active"').fetchall()
        stale = [str(r['file_path']) for r in rows if str(r['file_path']) not in current_set]
        if not stale:
            return

        for file_path in stale:
            chunk_rows = conn.execute('SELECT chunk_id FROM rag_chunks WHERE file_path = ?', (file_path,)).fetchall()
            delete_points([str(r['chunk_id']) for r in chunk_rows])
            conn.execute('DELETE FROM rag_chunks WHERE file_path = ?', (file_path,))
            conn.execute('UPDATE rag_documents SET status = "inactive", indexed_at = ? WHERE file_path = ?', (utc_now(), file_path))

        conn.commit()
    finally:
        conn.close()


def run_ingest_cycle():
    global LAST_INGEST_AT, LAST_INGEST_EPOCH
    docs = iter_docs()
    purge_missing_docs(docs)
    for path in docs:
        try:
            ingest_document(path)
        except Exception as exc:
            log.error('ingest_document_failed', path=str(path), error=str(exc))
            continue
    LAST_INGEST_EPOCH = now_epoch()
    LAST_INGEST_AT = utc_now()


def maybe_refresh_knowledge(force: bool = False):
    should_run = force or (
        INGEST_REFRESH_ON_ROUTE_SECONDS > 0 and
        ((now_epoch() - int(LAST_INGEST_EPOCH or 0)) >= INGEST_REFRESH_ON_ROUTE_SECONDS)
    )
    if not should_run:
        return
    if not INGEST_LOCK.acquire(blocking=False):
        return
    try:
        try:
            run_ingest_cycle()
        except Exception as exc:
            log.error('refresh_knowledge_failed', error=str(exc))
    finally:
        INGEST_LOCK.release()


def watch_loop():
    while True:
        try:
            run_ingest_cycle()
        except Exception as exc:
            log.error('watch_loop_cycle_failed', error=str(exc))
        time.sleep(WATCH_INTERVAL_SECONDS)


@app.get('/health')
def health():
    conn = db()
    cache_count = conn.execute('SELECT COUNT(*) AS c FROM response_cache WHERE active = 1').fetchone()['c']
    doc_count = conn.execute('SELECT COUNT(*) AS c FROM rag_documents WHERE status = "active"').fetchone()['c']
    chunk_count = conn.execute('SELECT COUNT(*) AS c FROM rag_chunks').fetchone()['c']
    conn.close()
    llm_info = multi_llm.llm_status()
    return jsonify({
        'ok': True,
        'topology': topology_metadata(),
        'mlDir': str(ML_DIR),
        'dbPath': str(DB_PATH),
        'vectorPath': str(QDRANT_PATH),
        'collection': QDRANT_COLLECTION,
        'cacheItems': int(cache_count),
        'activeDocuments': int(doc_count),
        'activeChunks': int(chunk_count),
        'embeddingsAvailable': EMBEDDINGS_AVAILABLE,
        'embeddingRateLimit': embed_limiter.stats,
        'lidCache': lid_cache.stats,
        'qdrantDisabled': QDRANT_DISABLED,
        'watchIntervalSeconds': WATCH_INTERVAL_SECONDS,
        'ingestRefreshOnRouteSeconds': INGEST_REFRESH_ON_ROUTE_SECONDS,
        'lastIngestAt': LAST_INGEST_AT,
        'audioTranscription': {
            'enabled': bool(openai_client),
            'model': OPENAI_TRANSCRIBE_MODEL,
            'maxAudioBytes': MAX_AUDIO_BYTES,
        },
        'routerTestGateEnforced': ROUTER_ENFORCE_TEST_GATE,
        'dualLlm': llm_info,
    })


@app.post('/route')
def route_endpoint():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        resolved_payload = resolve_recipient_payload(payload)
        blocked_set = get_all_blocked_numbers()
        allowed_set = get_all_always_allowed_numbers()
        recipient_number = digits_only(resolved_payload.get('number') or resolved_payload.get('customerNumber'))
        if allowed_set and recipient_number not in allowed_set:
            return jsonify({
                **resolved_payload,
                'routeDecision': 'test_gate_blocked',
                'cacheHit': False,
                'cachedReplyText': '',
                'routeIntent': '',
                'messageComplexity': 'blocked',
                'leadScore': 0,
                'ragContextLines': [],
                'ragContextSummary': '',
                'ragTopScore': 0,
                'conversationHistory': [],
                'contextCarryover': {
                    'answeringOpenQuestion': False,
                    'carriedIntent': '',
                    'conversationTurns': 0,
                    'effectiveIntent': '',
                    'isContextCarry': False,
                    'maxLeadScore': 0,
                    'memoryLeadStage': '',
                    'pendingQuestion': '',
                },
                'leadMemory': {},
                'memoryGuidance': [],
                'audioTranscription': {
                    'ok': False,
                    'reason': 'test_gate_blocked',
                    'text': '',
                },
                'llmReplyText': '',
                'llmProvider': '',
                'llmModel': '',
                'llmLatencyMs': 0,
                'llmStructuredData': {},
                'llmLeadScore': {},
                'blockedByTestGate': True,
                'routerOk': True,
                'dynamicBlockedNumbers': list(blocked_set),
                'dynamicAlwaysAllowedNumbers': list(allowed_set),
            })
        decision = route_message(resolved_payload)
        return jsonify({
            **resolved_payload,
            **decision,
            'topology': topology_metadata(),
            'routerOk': True,
            'routerTestGateEnforced': ROUTER_ENFORCE_TEST_GATE,
            'dynamicBlockedNumbers': list(blocked_set),
            'dynamicAlwaysAllowedNumbers': list(allowed_set),
        })
    except Exception as exc:
        return jsonify({
            **dict(payload or {}),
            'topology': topology_metadata(),
            'routerOk': False,
            'routerError': str(exc),
        })


@app.post('/resolve-recipient')
def resolve_recipient_endpoint():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        return jsonify({
            **resolve_recipient_payload(payload),
            'topology': topology_metadata(),
            'resolveOk': True,
        })
    except Exception as exc:
        return jsonify({
            **dict(payload or {}),
            'topology': topology_metadata(),
            'resolveOk': False,
            'resolveError': str(exc),
        })


@app.get('/llm-status')
def llm_status_endpoint():
    """Return status of dual-LLM providers (Claude + GPT)."""
    return jsonify({**multi_llm.llm_status(), 'topology': topology_metadata()})


@app.post('/generate-reply')
def generate_reply_endpoint():
    """Direct endpoint for LLM reply generation (used by n8n as alternative to OpenAI node)."""
    payload = request.get_json(force=True, silent=True) or {}
    try:
        result = multi_llm.generate_sales_reply(
            system_prompt=str(payload.get('systemPrompt') or SDR_SYSTEM_PROMPT),
            user_message=str(payload.get('userMessage') or ''),
            conversation_history=payload.get('conversationHistory'),
            max_tokens=int(payload.get('maxTokens', 300)),
            rag_context=str(payload.get('ragContext') or ''),
        )
        return jsonify({**result, 'ok': True})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc), 'text': ''})


@app.post('/extract-structured')
def extract_structured_endpoint():
    """Direct endpoint for structured data extraction from customer messages."""
    payload = request.get_json(force=True, silent=True) or {}
    try:
        data = multi_llm.extract_structured(
            user_message=str(payload.get('userMessage') or ''),
            schema_description=str(payload.get('schemaDescription') or ''),
            max_tokens=int(payload.get('maxTokens', 200)),
        )
        return jsonify({'ok': True, 'data': data})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc), 'data': {}})


@app.post('/summarize-conversation')
def summarize_conversation_endpoint():
    """Direct endpoint for conversation summarization (CRM notes)."""
    payload = request.get_json(force=True, silent=True) or {}
    try:
        summary = multi_llm.summarize_conversation(
            messages=payload.get('messages') or [],
            max_tokens=int(payload.get('maxTokens', 150)),
        )
        return jsonify({'ok': True, 'summary': summary})
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc), 'summary': ''})


@app.post('/learn-response')
def learn_response_endpoint():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        result = learn_response(payload)
        return jsonify({
            **dict(payload or {}),
            'topology': topology_metadata(),
            'routerLearnStored': bool(result.get('stored')),
            'routerLearnReason': str(result.get('reason') or ''),
        })
    except Exception as exc:
        return jsonify({
            **dict(payload or {}),
            'topology': topology_metadata(),
            'routerLearnStored': False,
            'routerLearnReason': str(exc),
        })


@app.post('/reindex')
def reindex_endpoint():
    run_ingest_cycle()
    return jsonify({'ok': True, 'reindexedAt': utc_now()})


@app.get('/metrics')
def metrics_endpoint():
    conn = db()
    total_routes = conn.execute('SELECT COUNT(*) AS c FROM route_logs').fetchone()['c']
    cache_hits = conn.execute("SELECT COUNT(*) AS c FROM route_logs WHERE cache_hit = 1").fetchone()['c']
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    today_routes = conn.execute("SELECT COUNT(*) AS c FROM route_logs WHERE created_at >= ?", (today,)).fetchone()['c']
    today_cache = conn.execute("SELECT COUNT(*) AS c FROM route_logs WHERE cache_hit = 1 AND created_at >= ?", (today,)).fetchone()['c']

    intent_rows = conn.execute(
        "SELECT route_decision, COUNT(*) AS c FROM route_logs WHERE created_at >= ? GROUP BY route_decision ORDER BY c DESC",
        (today,),
    ).fetchall()

    complexity_rows = conn.execute(
        "SELECT message_complexity, COUNT(*) AS c FROM route_logs WHERE created_at >= ? GROUP BY message_complexity ORDER BY c DESC",
        (today,),
    ).fetchall()

    top_intents_rows = conn.execute(
        '''SELECT normalized_message, route_decision, COUNT(*) AS c
           FROM route_logs WHERE created_at >= ? GROUP BY normalized_message ORDER BY c DESC LIMIT 10''',
        (today,),
    ).fetchall()

    recent_rows = conn.execute(
        '''SELECT number, push_name, inbound_text, route_decision, cache_hit, lead_score, created_at
           FROM route_logs ORDER BY created_at DESC LIMIT 20''',
    ).fetchall()

    conv_count = conn.execute('SELECT COUNT(DISTINCT contact_key) AS c FROM conversation_history').fetchone()['c']
    blocked_count = conn.execute('SELECT COUNT(*) AS c FROM blocked_numbers').fetchone()['c']
    always_allowed_count = conn.execute('SELECT COUNT(*) AS c FROM always_allowed_numbers').fetchone()['c']
    cache_count = conn.execute('SELECT COUNT(*) AS c FROM response_cache WHERE active = 1').fetchone()['c']

    conn.close()

    cache_rate = round(cache_hits / max(1, total_routes) * 100, 1)
    today_cache_rate = round(today_cache / max(1, today_routes) * 100, 1)

    return jsonify({
        'ok': True,
        'generatedAt': utc_now(),
        'totals': {
            'routes': total_routes,
            'cacheHits': cache_hits,
            'cacheHitRate': cache_rate,
            'cachedResponses': cache_count,
            'trackedConversations': conv_count,
            'blockedNumbers': blocked_count,
            'alwaysAllowedNumbers': always_allowed_count,
        },
        'today': {
            'routes': today_routes,
            'cacheHits': today_cache,
            'cacheHitRate': today_cache_rate,
        },
        'todayByRouteDecision': [dict(r) for r in intent_rows],
        'todayByComplexity': [dict(r) for r in complexity_rows],
        'todayTopMessages': [dict(r) for r in top_intents_rows],
        'recentRoutes': [dict(r) for r in recent_rows],
        'embeddingRateLimit': embed_limiter.stats,
        'lidCache': lid_cache.stats,
    })


@app.get('/dashboard')
def dashboard_endpoint():
    from flask import make_response
    html = '''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta http-equiv="refresh" content="30">
<title>Router Dashboard</title>
<style>
  body{font-family:system-ui,sans-serif;margin:0;padding:20px;background:#0f172a;color:#e2e8f0}
  h1{color:#38bdf8;font-size:1.4rem;margin-bottom:4px}
  .sub{color:#94a3b8;font-size:.85rem;margin-bottom:20px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}
  .card{background:#1e293b;border-radius:8px;padding:16px;text-align:center}
  .card .val{font-size:2rem;font-weight:700;color:#38bdf8}
  .card .label{font-size:.75rem;color:#94a3b8;margin-top:4px}
  table{width:100%;border-collapse:collapse;font-size:.82rem}
  th{text-align:left;padding:6px 8px;background:#1e293b;color:#94a3b8;font-weight:600}
  td{padding:6px 8px;border-bottom:1px solid #1e293b}
  .tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.72rem;font-weight:600}
  .tag-cache{background:#065f46;color:#6ee7b7}
  .tag-rag{background:#7c2d12;color:#fdba74}
  .tag-gpt{background:#312e81;color:#a5b4fc}
  #data{opacity:0;transition:opacity .3s} #data.loaded{opacity:1}
</style></head>
<body>
<h1>Router Dashboard — WhatsApp Inside Sales</h1>
<div class="sub" id="ts">Carregando...</div>
<div class="grid" id="cards"></div>
<h2 style="font-size:1rem;color:#94a3b8">Ultimas 20 rotas</h2>
<table><thead><tr><th>Hora</th><th>Numero</th><th>Nome</th><th>Decisao</th><th>Cache</th><th>Lead</th><th>Texto</th></tr></thead>
<tbody id="routes"></tbody></table>
<div id="data"></div>
<script>
async function load(){
  try{
    const r=await fetch('/metrics');const d=await r.json();
    document.getElementById('ts').textContent='Atualizado: '+new Date(d.generatedAt).toLocaleString('pt-BR')+' (auto-refresh 30s)';
    const t=d.totals,td=d.today;
    document.getElementById('cards').innerHTML=[
      card(t.routes,'Rotas total'),card(td.routes,'Rotas hoje'),
      card(td.cacheHitRate+'%','Cache hit hoje'),card(t.cacheHitRate+'%','Cache hit total'),
      card(t.cachedResponses,'Respostas em cache'),card(t.trackedConversations,'Conversas rastreadas'),
      card(t.blockedNumbers,'Numeros bloqueados'),
      card(d.embeddingRateLimit.totalThrottled,'Embed throttled'),
      card(d.lidCache.hitRate*100+'%','LID cache hit'),
    ].join('');
    const rows=d.recentRoutes||[];
    document.getElementById('routes').innerHTML=rows.map(r=>{
      const t=new Date(r.created_at).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
      const dec=r.route_decision;
      const cls=dec==='cache'?'cache':dec.includes('rag')?'rag':'gpt';
      return '<tr><td>'+t+'</td><td>'+mask(r.number)+'</td><td>'+(r.push_name||'-')+'</td><td><span class="tag tag-'+cls+'">'+dec+'</span></td><td>'+(r.cache_hit?'SIM':'')+'</td><td>'+r.lead_score+'</td><td>'+esc(r.inbound_text||'').slice(0,60)+'</td></tr>';
    }).join('');
  }catch(e){document.getElementById('ts').textContent='Erro: '+e.message}
}
function card(v,l){return '<div class="card"><div class="val">'+v+'</div><div class="label">'+l+'</div></div>'}
function mask(n){return n?n.slice(0,4)+'****'+n.slice(-3):'?'}
function esc(s){return s.replace(/</g,'&lt;').replace(/>/g,'&gt;')}
load();
</script></body></html>'''
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp


@app.get('/blocked-numbers')
def blocked_numbers_list():
    conn = db()
    rows = conn.execute('SELECT number, reason, added_at FROM blocked_numbers ORDER BY added_at DESC').fetchall()
    conn.close()
    return jsonify({'ok': True, 'count': len(rows), 'numbers': [dict(r) for r in rows]})


@app.post('/blocked-numbers')
def blocked_numbers_add():
    payload = request.get_json(force=True, silent=True) or {}
    number = re.sub(r'\D', '', str(payload.get('number', '')))
    reason = str(payload.get('reason', '')).strip()[:200]
    if not number:
        return jsonify({'ok': False, 'error': 'number required'}), 400
    conn = db()
    conn.execute(
        'INSERT OR REPLACE INTO blocked_numbers (number, reason, added_at) VALUES (?, ?, ?)',
        (number, reason, utc_now()),
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'added': number})


@app.delete('/blocked-numbers')
def blocked_numbers_remove():
    payload = request.get_json(force=True, silent=True) or {}
    number = re.sub(r'\D', '', str(payload.get('number', '')))
    if not number:
        return jsonify({'ok': False, 'error': 'number required'}), 400
    conn = db()
    conn.execute('DELETE FROM blocked_numbers WHERE number = ?', (number,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'removed': number})


def get_all_blocked_numbers() -> set:
    conn = db()
    rows = conn.execute('SELECT number FROM blocked_numbers').fetchall()
    conn.close()
    return {r['number'] for r in rows}


@app.get('/always-allowed-numbers')
def always_allowed_numbers_list():
    conn = db()
    rows = conn.execute('SELECT number, reason, added_at FROM always_allowed_numbers ORDER BY added_at DESC').fetchall()
    conn.close()
    return jsonify({'ok': True, 'count': len(rows), 'numbers': [dict(r) for r in rows]})


@app.post('/always-allowed-numbers')
def always_allowed_numbers_add():
    payload = request.get_json(force=True, silent=True) or {}
    number = re.sub(r'\D', '', str(payload.get('number', '')))
    reason = str(payload.get('reason', '')).strip()[:200]
    if not number:
        return jsonify({'ok': False, 'error': 'number required'}), 400
    conn = db()
    conn.execute(
        'INSERT OR REPLACE INTO always_allowed_numbers (number, reason, added_at) VALUES (?, ?, ?)',
        (number, reason, utc_now()),
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'added': number})


@app.delete('/always-allowed-numbers')
def always_allowed_numbers_remove():
    payload = request.get_json(force=True, silent=True) or {}
    number = re.sub(r'\D', '', str(payload.get('number', '')))
    if not number:
        return jsonify({'ok': False, 'error': 'number required'}), 400
    conn = db()
    conn.execute('DELETE FROM always_allowed_numbers WHERE number = ?', (number,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'removed': number})


def get_all_always_allowed_numbers() -> set:
    conn = db()
    rows = conn.execute('SELECT number FROM always_allowed_numbers').fetchall()
    conn.close()
    return {r['number'] for r in rows}


CONVERSATION_HISTORY_LIMIT = int(os.getenv('ROUTER_CONVERSATION_HISTORY_LIMIT', '10'))
CONVERSATION_HISTORY_HOURS = int(os.getenv('ROUTER_CONVERSATION_HISTORY_HOURS', '48'))


def record_message(contact_key: str, direction: str, message_text: str,
                   intent: str = '', complexity: str = '', lead_score: float = 0,
                   route_decision: str = ''):
    if not contact_key or not message_text:
        return
    safe_text = sanitize_outbound_text(message_text, 2000) if str(direction or '').strip().lower() == 'outbound' else str(message_text or '')[:2000]
    if not safe_text:
        return
    conn = db()
    conn.execute(
        '''INSERT INTO conversation_history
           (contact_key, direction, message_text, intent, complexity, lead_score, route_decision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (contact_key, direction, safe_text, intent, complexity, lead_score, route_decision, utc_now()),
    )
    conn.commit()
    conn.close()


def get_conversation_history(contact_key: str, limit: int = 0) -> List[Dict]:
    if not contact_key:
        return []
    limit = limit or CONVERSATION_HISTORY_LIMIT
    conn = db()
    rows = conn.execute(
        '''SELECT direction, message_text, intent, complexity, lead_score, route_decision, created_at
           FROM conversation_history
           WHERE contact_key = ?
             AND created_at >= datetime('now', ?)
           ORDER BY created_at DESC
           LIMIT ?''',
        (contact_key, f'-{CONVERSATION_HISTORY_HOURS} hours', limit),
    ).fetchall()
    conn.close()
    out = []
    for row in reversed(rows):
        item = dict(row)
        if str(item.get('direction') or '').strip().lower() == 'outbound':
            item['message_text'] = sanitize_outbound_text(item.get('message_text') or '', 2000)
        out.append(item)
    return out


def purge_disallowed_outbound_artifacts():
    conn = db()

    def _rewrite_table(table: str, key_col: str, text_cols: List[str], where: str = ''):
        select_cols = [key_col] + [col for col in text_cols if col != key_col]
        rows = conn.execute(
            f"SELECT {', '.join(select_cols)} FROM {table} {where}"
        ).fetchall()
        changed = 0
        for row in rows:
            payload = {}
            for col in text_cols:
                raw = row[col]
                safe = sanitize_outbound_text(raw or '', 0)
                if safe != str(raw or ''):
                    payload[col] = safe
            if payload:
                assignments = ', '.join([f'{col} = ?' for col in payload.keys()])
                conn.execute(
                    f'UPDATE {table} SET {assignments} WHERE {key_col} = ?',
                    (*payload.values(), row[key_col]),
                )
                changed += 1
        return changed

    _rewrite_table('response_cache', 'normalized_message', ['reply_text'])
    _rewrite_table('conversation_history', 'rowid', ['message_text'], "WHERE direction = 'outbound'")
    _rewrite_table('lead_memory', 'contact_key', ['summary', 'open_question', 'last_outbound_text', 'next_step'])
    _rewrite_table('learning_events', 'id', ['reply_text'])

    conn.commit()
    conn.close()


CONTEXT_CARRY_TRIGGERS = {
    'sim', 'nao', 'não', 'ok', 'quero', 'pode', 'manda', 'mande', 'envia',
    'isso', 'exato', 'isso mesmo', 'com certeza', 'claro', 'beleza', 'blz',
    'fechado', 'bora', 'vamos', 'pode ser', 'aceito', 'confirmo',
}


def build_context_carryover(conversation: List[Dict], current_intent: str, current_text: str, lead_memory: Dict = None) -> Dict:
    """Derive context from conversation history when current message is too generic."""
    norm_text = normalize_ascii(current_text)
    tokens = tokenize_words(current_text)
    is_generic = (
        len(tokens) <= 4
        and (norm_text in CONTEXT_CARRY_TRIGGERS or current_intent == 'geral')
    )
    memory = lead_memory or {}

    prev_intents = [
        m['intent'] for m in conversation
        if m.get('direction') == 'inbound' and m.get('intent') and m['intent'] != 'geral'
    ]
    prev_scores = [m.get('lead_score', 0) for m in conversation if m.get('direction') == 'inbound']

    carried_intent = prev_intents[-1] if (is_generic and prev_intents) else ''
    if not carried_intent and is_generic:
        memory_intent = str(memory.get('lastIntent') or '').strip()
        if memory_intent and memory_intent != 'geral':
            carried_intent = memory_intent
    max_lead_score = max(prev_scores) if prev_scores else 0
    conversation_turns = len([m for m in conversation if m.get('direction') == 'inbound'])
    pending_question = compact_text(memory.get('openQuestion'), 220)

    return {
        'carriedIntent': carried_intent,
        'effectiveIntent': carried_intent or current_intent,
        'isContextCarry': bool(carried_intent),
        'maxLeadScore': max_lead_score,
        'conversationTurns': conversation_turns,
        'pendingQuestion': pending_question,
        'answeringOpenQuestion': bool(pending_question and len(tokens) <= 12),
        'memoryLeadStage': str(memory.get('leadStage') or '').strip(),
    }


def main():
    if not acquire_single_instance_lock():
        log.warning('single_instance_lock_active', action='skip_start')
        return
    validate_topology()
    log.info('attendant_topology_registered', **topology_metadata())
    ensure_db()
    purge_disallowed_outbound_artifacts()
    watcher = threading.Thread(target=watch_loop, daemon=True)
    watcher.start()
    log.info('router_starting', host='0.0.0.0', port=8091)
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=8091, threads=8)
    except ImportError:
        log.warning('waitress_not_found', fallback='flask_dev_server')
        app.run(host='0.0.0.0', port=8091, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
