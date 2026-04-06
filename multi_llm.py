"""
multi_llm.py - Dual-LLM Router: Claude (Anthropic) + GPT (OpenAI)

Task routing:
- Claude Sonnet: SDR replies / conversation analysis
- Claude Haiku: summaries / lead score analysis
- GPT structured model: JSON extraction
- GPT main model: fallback for SDR replies

Reliability:
- Retry with exponential backoff for Anthropic transient failures
- Circuit-breaker cooldown after repeated overloaded (529)
- Automatic fallback across providers
"""

import json
import os
import random
import time
from typing import Dict, List, Optional

from dotenv import load_dotenv
import structlog

_env_path_mlm = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path_mlm)

log = structlog.get_logger()


def _cfg(key: str, default: str = '') -> str:
    return os.getenv(key, default).strip()


# Config
ANTHROPIC_API_KEY = _cfg('ANTHROPIC_API_KEY')
ANTHROPIC_MODEL_SALES = _cfg('ANTHROPIC_MODEL_SALES', 'claude-sonnet-4-20250514')
ANTHROPIC_MODEL_FAST = _cfg('ANTHROPIC_MODEL_FAST', 'claude-haiku-4-5-20251001')

OPENAI_API_KEY = _cfg('OPENAI_API_KEY')
OPENAI_MODEL_MAIN = _cfg('OPENAI_MODEL', 'gpt-4o-mini')
OPENAI_MODEL_STRUCTURED = _cfg('OPENAI_MODEL_STRUCTURED', 'gpt-4o-mini')

ANTHROPIC_RETRY_ATTEMPTS = int(_cfg('ANTHROPIC_RETRY_ATTEMPTS', '4') or '4')
ANTHROPIC_RETRY_BASE_DELAY_SECONDS = float(_cfg('ANTHROPIC_RETRY_BASE_DELAY_SECONDS', '0.8') or '0.8')
ANTHROPIC_RETRY_MAX_DELAY_SECONDS = float(_cfg('ANTHROPIC_RETRY_MAX_DELAY_SECONDS', '8') or '8')
ANTHROPIC_OVERLOADED_COOLDOWN_SECONDS = float(_cfg('ANTHROPIC_OVERLOADED_COOLDOWN_SECONDS', '45') or '45')

# Lazy clients
_anthropic_client = None
_openai_client = None
_anthropic_overloaded_until = 0.0


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client
    if not ANTHROPIC_API_KEY:
        return None
    try:
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY, timeout=10.0)
        log.info('anthropic_client_init', model_sales=ANTHROPIC_MODEL_SALES, model_fast=ANTHROPIC_MODEL_FAST)
        return _anthropic_client
    except Exception as exc:
        log.warning('anthropic_client_failed', error=str(exc))
        return None


def _get_openai():
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=OPENAI_API_KEY, timeout=10.0)
        return _openai_client
    except Exception as exc:
        log.warning('openai_client_failed', error=str(exc))
        return None


def _is_anthropic_overloaded_error(exc: Exception) -> bool:
    msg = str(exc or '').lower()
    return 'overloaded_error' in msg or 'status code: 529' in msg or ' 529 ' in msg


def _is_anthropic_retryable_error(exc: Exception) -> bool:
    msg = str(exc or '').lower()
    return (
        _is_anthropic_overloaded_error(exc)
        or 'rate limit' in msg
        or '429' in msg
        or 'timeout' in msg
        or 'timed out' in msg
        or 'temporarily unavailable' in msg
        or 'service unavailable' in msg
        or 'connection reset' in msg
        or 'connection error' in msg
    )


def _anthropic_cooldown_active() -> bool:
    return time.monotonic() < _anthropic_overloaded_until


def _set_anthropic_cooldown(seconds: float) -> None:
    global _anthropic_overloaded_until
    candidate = time.monotonic() + max(0.0, float(seconds))
    if candidate > _anthropic_overloaded_until:
        _anthropic_overloaded_until = candidate


def _anthropic_messages_create_with_retry(client, **kwargs):
    last_exc = None
    attempts = max(1, int(ANTHROPIC_RETRY_ATTEMPTS))

    for i in range(attempts):
        try:
            return client.messages.create(**kwargs)
        except Exception as exc:
            last_exc = exc
            retryable = _is_anthropic_retryable_error(exc)
            if not retryable or i >= attempts - 1:
                if _is_anthropic_overloaded_error(exc):
                    _set_anthropic_cooldown(ANTHROPIC_OVERLOADED_COOLDOWN_SECONDS)
                    log.warning('anthropic_cooldown_set', seconds=ANTHROPIC_OVERLOADED_COOLDOWN_SECONDS, error=str(exc))
                raise

            delay = min(
                ANTHROPIC_RETRY_MAX_DELAY_SECONDS,
                ANTHROPIC_RETRY_BASE_DELAY_SECONDS * (2 ** i),
            )
            delay += random.uniform(0.0, min(0.5, delay * 0.2))
            log.warning(
                'anthropic_retry_backoff',
                attempt=i + 1,
                max_attempts=attempts,
                delay_seconds=round(delay, 3),
                error=str(exc),
            )
            time.sleep(delay)

    if last_exc:
        raise last_exc
    raise RuntimeError('anthropic_retry_unexpected_state')


# ============================================================
# TASK: Sales SDR Response (Claude Sonnet -> GPT fallback)
# ============================================================
def generate_sales_reply(
    system_prompt: str,
    user_message: str,
    conversation_history: Optional[List[Dict]] = None,
    max_tokens: int = 300,
    rag_context: str = '',
    memory_context: str = '',
) -> Dict:
    messages = []
    if conversation_history:
        for msg in conversation_history[-6:]:
            role = 'assistant' if msg.get('direction') == 'outbound' else 'user'
            text = str(msg.get('message_text') or msg.get('text') or '')
            if text:
                messages.append({'role': role, 'content': text})

    sections = []
    if memory_context:
        sections.append(f"Contexto comercial ja confirmado:\n{memory_context}")
    if rag_context:
        sections.append(f"Contexto de produtos/servicos:\n{rag_context}")
    sections.append(f"Mensagem do cliente:\n{user_message}")
    user_content = '\n\n'.join(sections)
    messages.append({'role': 'user', 'content': user_content})

    client = _get_anthropic()
    if client and not _anthropic_cooldown_active():
        try:
            t0 = time.monotonic()
            resp = _anthropic_messages_create_with_retry(
                client,
                model=ANTHROPIC_MODEL_SALES,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            )
            latency = int((time.monotonic() - t0) * 1000)
            text = resp.content[0].text if resp.content else ''
            result = {
                'text': (text or '').strip(),
                'model': getattr(resp, 'model', ANTHROPIC_MODEL_SALES),
                'provider': 'anthropic',
                'latency_ms': latency,
                'tokens_in': getattr(resp.usage, 'input_tokens', 0),
                'tokens_out': getattr(resp.usage, 'output_tokens', 0),
            }
            log.info('llm_sales_reply', provider='anthropic', model=result['model'], latency_ms=latency,
                     tokens_in=result['tokens_in'], tokens_out=result['tokens_out'])
            return result
        except Exception as exc:
            log.warning('anthropic_sales_failed', error=str(exc))
    elif client and _anthropic_cooldown_active():
        log.warning('anthropic_sales_skipped_cooldown')

    oai = _get_openai()
    if oai:
        try:
            t0 = time.monotonic()
            oai_messages = [{'role': 'system', 'content': system_prompt}] + messages
            resp = oai.chat.completions.create(
                model=OPENAI_MODEL_MAIN,
                messages=oai_messages,
                max_tokens=max_tokens,
            )
            latency = int((time.monotonic() - t0) * 1000)
            text = resp.choices[0].message.content or ''
            result = {
                'text': text.strip(),
                'model': resp.model,
                'provider': 'openai',
                'latency_ms': latency,
                'tokens_in': getattr(resp.usage, 'prompt_tokens', 0),
                'tokens_out': getattr(resp.usage, 'completion_tokens', 0),
            }
            log.info('llm_sales_reply', provider='openai', model=resp.model, latency_ms=latency)
            return result
        except Exception as exc:
            log.error('openai_sales_failed', error=str(exc))

    return {'text': '', 'model': 'none', 'provider': 'none', 'latency_ms': 0, 'tokens_in': 0, 'tokens_out': 0}


# ============================================================
# TASK: Structured Extraction (GPT -> Claude fallback)
# ============================================================
def extract_structured(
    user_message: str,
    schema_description: str = '',
    max_tokens: int = 200,
) -> Dict:
    default_schema = (
        "- nome_contato: string (nome do lead, se mencionado)\n"
        "- nome_empresa: string (nome da empresa, se mencionado)\n"
        "- cnpj: string (CNPJ se mencionado, apenas digitos)\n"
        "- cidade: string (cidade/estado se mencionado)\n"
        "- produtos_interesse: array de strings (produtos mencionados)\n"
        "- product_focus: string (categoria principal do interesse, ex: bolsas, carteiras, cintos)\n"
        "- categoria_produto: string (categoria mais especifica, se houver)\n"
        "- quantidade: string (quantidade/volume mencionado)\n"
        "- objecao_principal: string (objeção comercial, se houver)\n"
        "- proximo_passo: string (melhor proximo passo comercial sugerido)\n"
        "- etapa_sugerida: string (novo|qualificando|proposta|negociacao|fechamento|pos_venda)\n"
        "- intent: string (saudacao|orcamento|catalogo|prazo|pagamento|reclamacao|geral)\n"
        "- urgencia: string (baixa|media|alta)"
    )
    schema_block = schema_description if schema_description else default_schema
    prompt = (
        "Extraia os seguintes dados da mensagem do cliente em JSON:\n"
        f"{schema_block}\n"
        "Responda APENAS com JSON, sem markdown.\n\n"
        f"Mensagem: \"{user_message}\""
    )

    oai = _get_openai()
    if oai:
        try:
            t0 = time.monotonic()
            resp = oai.chat.completions.create(
                model=OPENAI_MODEL_STRUCTURED,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=max_tokens,
                response_format={'type': 'json_object'},
            )
            latency = int((time.monotonic() - t0) * 1000)
            raw = resp.choices[0].message.content or '{}'
            data = json.loads(raw)
            log.info('llm_extract', provider='openai', latency_ms=latency, fields=len(data))
            return data
        except Exception as exc:
            log.warning('openai_extract_failed', error=str(exc))

    client = _get_anthropic()
    if client and not _anthropic_cooldown_active():
        try:
            t0 = time.monotonic()
            resp = _anthropic_messages_create_with_retry(
                client,
                model=ANTHROPIC_MODEL_FAST,
                max_tokens=max_tokens,
                messages=[{'role': 'user', 'content': prompt}],
            )
            latency = int((time.monotonic() - t0) * 1000)
            raw = resp.content[0].text if resp.content else '{}'
            raw = raw.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0]
            data = json.loads(raw)
            log.info('llm_extract', provider='anthropic', latency_ms=latency, fields=len(data))
            return data
        except Exception as exc:
            log.warning('anthropic_extract_failed', error=str(exc))
    elif client and _anthropic_cooldown_active():
        log.warning('anthropic_extract_skipped_cooldown')

    return {}


# ============================================================
# TASK: Conversation Summary (Claude Haiku -> GPT fallback)
# ============================================================
def summarize_conversation(
    messages: List[Dict],
    max_tokens: int = 150,
) -> str:
    conversation_text = '\n'.join([
        f"{'Cliente' if m.get('direction') == 'inbound' else 'Eduardo'}: {m.get('message_text', '')}"
        for m in messages if m.get('message_text')
    ])

    if not conversation_text.strip():
        return ''

    prompt = (
        "Resuma esta conversa comercial em 2-3 frases para registro no CRM.\n"
        "Foque em: interesse do cliente, produtos mencionados, proximos passos.\n\n"
        f"Conversa:\n{conversation_text}\n\nResumo:"
    )

    client = _get_anthropic()
    if client and not _anthropic_cooldown_active():
        try:
            resp = _anthropic_messages_create_with_retry(
                client,
                model=ANTHROPIC_MODEL_FAST,
                max_tokens=max_tokens,
                messages=[{'role': 'user', 'content': prompt}],
            )
            return (resp.content[0].text if resp.content else '').strip()
        except Exception as exc:
            log.warning('anthropic_summary_failed', error=str(exc))
    elif client and _anthropic_cooldown_active():
        log.warning('anthropic_summary_skipped_cooldown')

    oai = _get_openai()
    if oai:
        try:
            resp = oai.chat.completions.create(
                model=OPENAI_MODEL_STRUCTURED,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=max_tokens,
            )
            return (resp.choices[0].message.content or '').strip()
        except Exception as exc:
            log.warning('openai_summary_failed', error=str(exc))

    return ''


# ============================================================
# TASK: Lead Score Analysis (Claude Haiku -> GPT fallback)
# ============================================================
def analyze_lead_score(
    conversation_history: List[Dict],
    current_message: str,
    keyword_score: int = 0,
) -> Dict:
    history_text = '\n'.join([
        f"{'Cliente' if m.get('direction') == 'inbound' else 'Eduardo'}: {m.get('message_text', '')}"
        for m in (conversation_history or [])[-8:] if m.get('message_text')
    ])

    prompt = (
        "Analise este lead B2B de revenda de acessorios de couro.\n"
        f"Score de keywords atual: {keyword_score}/100\n\n"
        f"Historico:\n{history_text}\n\n"
        f"Mensagem atual do cliente: \"{current_message}\"\n\n"
        "Responda em JSON:\n"
        "{\"score\": <0-100>, \"reasoning\": \"<1 frase>\", \"next_action\": \"<sugestao de proximo passo para o vendedor>\"}"
    )

    client = _get_anthropic()
    if client and not _anthropic_cooldown_active():
        try:
            resp = _anthropic_messages_create_with_retry(
                client,
                model=ANTHROPIC_MODEL_FAST,
                max_tokens=150,
                messages=[{'role': 'user', 'content': prompt}],
            )
            raw = (resp.content[0].text if resp.content else '{}').strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0]
            return json.loads(raw)
        except Exception as exc:
            log.warning('anthropic_lead_score_failed', error=str(exc))
    elif client and _anthropic_cooldown_active():
        log.warning('anthropic_lead_score_skipped_cooldown')

    oai = _get_openai()
    if oai:
        try:
            resp = oai.chat.completions.create(
                model=OPENAI_MODEL_STRUCTURED,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=150,
                response_format={'type': 'json_object'},
            )
            return json.loads(resp.choices[0].message.content or '{}')
        except Exception as exc:
            log.warning('openai_lead_score_failed', error=str(exc))

    return {'score': keyword_score, 'reasoning': 'fallback', 'next_action': ''}


# ============================================================
# Status / Health
# ============================================================
def llm_status() -> Dict:
    return {
        'anthropic': {
            'available': bool(ANTHROPIC_API_KEY and _get_anthropic()),
            'model_sales': ANTHROPIC_MODEL_SALES,
            'model_fast': ANTHROPIC_MODEL_FAST,
            'cooldown_active': _anthropic_cooldown_active(),
        },
        'openai': {
            'available': bool(OPENAI_API_KEY and _get_openai()),
            'model_main': OPENAI_MODEL_MAIN,
            'model_structured': OPENAI_MODEL_STRUCTURED,
        },
        'retry': {
            'anthropic_attempts': ANTHROPIC_RETRY_ATTEMPTS,
            'anthropic_base_delay_seconds': ANTHROPIC_RETRY_BASE_DELAY_SECONDS,
            'anthropic_max_delay_seconds': ANTHROPIC_RETRY_MAX_DELAY_SECONDS,
            'anthropic_overloaded_cooldown_seconds': ANTHROPIC_OVERLOADED_COOLDOWN_SECONDS,
        },
        'delegation': {
            'sales_reply': 'anthropic' if ANTHROPIC_API_KEY else 'openai',
            'structured_extract': 'openai',
            'conversation_summary': 'anthropic' if ANTHROPIC_API_KEY else 'openai',
            'lead_score_analysis': 'anthropic' if ANTHROPIC_API_KEY else 'openai',
            'embeddings': 'openai',
            'speech_to_text': 'openai',
        },
    }
