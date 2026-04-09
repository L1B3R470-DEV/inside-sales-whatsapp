import json
import os
import re
import time
import atexit
import ctypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from ai_capacity_registry import (
    STATUS_AVAILABLE,
    STATUS_DEGRADED,
    STATUS_RECOVERED,
    STATUS_USAGE_EXHAUSTED,
    mark_agent_heartbeat,
    update_agent_status,
)

load_dotenv(Path(__file__).resolve().parent / ".env")

try:
    from anthropic import Anthropic
except Exception as exc:
    raise RuntimeError("anthropic SDK nao instalado. Rode pip install anthropic") from exc


BRIDGE_ROOT = Path(os.getenv("CLAUDE_BRIDGE_ROOT", r"C:\AUTOMACAO\cowork\claude_bridge"))
INBOX_DIR = BRIDGE_ROOT / "inbox_for_claude"
OUTBOX_DIR = BRIDGE_ROOT / "outbox_from_claude"
STATE_FILE = BRIDGE_ROOT / "worker_state.json"
POLL_SECONDS = int(os.getenv("CLAUDE_BRIDGE_POLL_SECONDS", "5"))
MUTEX_NAME = os.getenv("CLAUDE_COWORK_MUTEX_NAME", r"Local\WA_Claude_Cowork_Worker")
LOCK_FILE = BRIDGE_ROOT / "cowork_worker.lock"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL_PRIMARY = os.getenv("ANTHROPIC_MODEL_SALES", "claude-sonnet-4-20250514").strip()
MODEL_FALLBACK = os.getenv("ANTHROPIC_MODEL_FAST", "claude-haiku-4-5-20251001").strip()

RETRY_ATTEMPTS = int(os.getenv("ANTHROPIC_RETRY_ATTEMPTS", "4"))
RETRY_BASE = float(os.getenv("ANTHROPIC_RETRY_BASE_DELAY_SECONDS", "0.8"))
RETRY_MAX = float(os.getenv("ANTHROPIC_RETRY_MAX_DELAY_SECONDS", "8"))

SYSTEM = (
    "Voce e um engenheiro senior colaborando com outro agente no mesmo projeto. "
    "Responda de forma objetiva e acionavel. "
    "Saida obrigatoria: JSON valido sem markdown."
)
MUTEX_HANDLE = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    for p in (BRIDGE_ROOT, INBOX_DIR, OUTBOX_DIR):
        p.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text(
            json.dumps(
                {
                    "processed_tasks": [],
                    "status": STATUS_AVAILABLE,
                    "reason": "bootstrap",
                    "last_heartbeat_at": "",
                    "last_success_at": "",
                    "last_error_at": "",
                    "last_error": "",
                    "last_task_id": "",
                    "current_model": MODEL_PRIMARY,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _acquire_file_lock() -> bool:
    if LOCK_FILE.exists():
        try:
            old_pid = int((LOCK_FILE.read_text(encoding="utf-8") or "0").strip())
            if _pid_alive(old_pid):
                return False
        except Exception:
            pass
        try:
            LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            return False
    try:
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
        return True
    except Exception:
        return False


def _release_file_lock() -> None:
    try:
        if LOCK_FILE.exists():
            owner = int((LOCK_FILE.read_text(encoding="utf-8") or "0").strip())
            if owner == os.getpid():
                LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def acquire_single_instance() -> bool:
    global MUTEX_HANDLE
    if os.name == "nt":
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not handle:
            return False
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            return False
        MUTEX_HANDLE = handle

    if not _acquire_file_lock():
        if MUTEX_HANDLE and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(MUTEX_HANDLE))
            MUTEX_HANDLE = None
        return False

    def _release_all() -> None:
        _release_file_lock()
        if MUTEX_HANDLE and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(MUTEX_HANDLE))

    atexit.register(_release_all)
    return True


def read_state() -> Dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"processed_tasks": []}


def write_state(state: Dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_json(text: str) -> Dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}
    return {}


def _is_overloaded(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "overloaded_error" in msg or "529" in msg


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        x in msg
        for x in [
            "overloaded_error",
            "529",
            "429",
            "rate limit",
            "timeout",
            "temporarily unavailable",
            "service unavailable",
            "connection reset",
        ]
    )


def call_claude(client: Anthropic, prompt: str):
    last_exc = None
    model = MODEL_PRIMARY
    overloaded_seen = False
    for attempt in range(RETRY_ATTEMPTS):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=900,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text if resp.content else "{}"
            data = extract_json(text)
            return data or {}, model, overloaded_seen
        except Exception as exc:
            last_exc = exc
            if _is_overloaded(exc):
                overloaded_seen = True
            if overloaded_seen and model != MODEL_FALLBACK:
                model = MODEL_FALLBACK
            if (not _is_retryable(exc)) or attempt >= RETRY_ATTEMPTS - 1:
                break
            delay = min(RETRY_MAX, RETRY_BASE * (2 ** attempt))
            time.sleep(delay)
    raise RuntimeError(str(last_exc) if last_exc else "claude_call_failed")


def heartbeat_worker(state: Dict, *, status: str = STATUS_AVAILABLE, reason: str = "poll_loop") -> None:
    stamp = now_iso()
    state["status"] = status
    state["reason"] = reason
    state["last_heartbeat_at"] = stamp
    write_state(state)
    mark_agent_heartbeat(
        "claude_bridge_worker_pc_lbn",
        status=status,
        reason=reason,
        metadata={
            "last_task_id": state.get("last_task_id", ""),
            "current_model": state.get("current_model", MODEL_PRIMARY),
            "processed_count": len(state.get("processed_tasks") or []),
        },
    )


def build_prompt(task: Dict) -> str:
    task_id = str(task.get("task_id", "")).strip()
    title = str(task.get("title", "")).strip()
    body = str(task.get("body", "")).strip()
    refs = task.get("references") or []
    refs_text = "\n".join(f"- {r}" for r in refs if str(r).strip())
    required = str(task.get("required_output", "")).strip()
    return (
        "Resolva a tarefa abaixo e retorne EXCLUSIVAMENTE um JSON valido.\n\n"
        f"task_id: {task_id}\n"
        f"title: {title}\n"
        f"body:\n{body}\n\n"
        f"references:\n{refs_text if refs_text else '- (sem referencias)'}\n\n"
        f"required_output: {required}\n\n"
        "Schema obrigatorio:\n"
        "{\n"
        '  "reply_id": "REPLY-YYYYMMDD-HHMMSS",\n'
        '  "task_id": "<task_id>",\n'
        '  "created_at": "<ISO8601>",\n'
        '  "from": "claude",\n'
        '  "to": "codex",\n'
        '  "status": "done|needs_input|blocked",\n'
        '  "summary": "texto",\n'
        '  "changes": [{"file":"caminho","action":"created|updated|deleted","details":"texto"}],\n'
        '  "risks": ["texto"],\n'
        '  "next_steps": ["texto"]\n'
        "}\n"
    )


def task_files() -> List[Path]:
    return sorted(INBOX_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)


def reply_path(reply_id: str) -> Path:
    return OUTBOX_DIR / f"{reply_id}.json"


def process_task(client: Anthropic, task_file: Path, state: Dict) -> bool:
    task = json.loads(task_file.read_text(encoding="utf-8-sig"))
    task_id = str(task.get("task_id", "")).strip()
    if not task_id:
        return False

    processed = set(state.get("processed_tasks") or [])
    if task_id in processed:
        return False

    prompt = build_prompt(task)
    try:
        data, model_used, overloaded_seen = call_claude(client, prompt)
        if not data:
            data = {}
        data.setdefault("reply_id", "REPLY-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
        data.setdefault("task_id", task_id)
        data.setdefault("created_at", now_iso())
        data.setdefault("from", "claude")
        data.setdefault("to", "codex")
        data.setdefault("status", "done")
        data.setdefault("summary", "Resposta gerada automaticamente via API Claude.")
        data.setdefault("changes", [])
        data.setdefault("risks", [])
        data.setdefault("next_steps", [])
        state["status"] = STATUS_RECOVERED if overloaded_seen else STATUS_AVAILABLE
        state["reason"] = "task_processed"
        state["last_success_at"] = now_iso()
        state["last_error"] = ""
        state["last_task_id"] = task_id
        state["current_model"] = model_used
        write_state(state)
        update_agent_status(
            "anthropic_api_pc_lbn",
            status=STATUS_RECOVERED if overloaded_seen else STATUS_AVAILABLE,
            availability=True,
            reason="worker_request_succeeded",
            metadata={"model": model_used, "task_id": task_id},
        )
        mark_agent_heartbeat(
            "claude_bridge_worker_pc_lbn",
            status=STATUS_RECOVERED if overloaded_seen else STATUS_AVAILABLE,
            reason="task_processed",
            metadata={"task_id": task_id, "model": model_used},
        )
    except Exception as exc:
        overloaded = _is_overloaded(exc)
        worker_status = STATUS_USAGE_EXHAUSTED if overloaded else STATUS_DEGRADED
        data = {
            "reply_id": "REPLY-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
            "task_id": task_id,
            "created_at": now_iso(),
            "from": "claude",
            "to": "codex",
            "status": "blocked",
            "summary": f"Falha ao consultar Claude API: {exc}",
            "changes": [],
            "risks": ["Instabilidade de provedor ou credencial"],
            "next_steps": ["Repetir em alguns minutos", "Validar saldo e limites da conta Anthropic"],
        }
        state["status"] = worker_status
        state["reason"] = "task_failed"
        state["last_error_at"] = now_iso()
        state["last_error"] = str(exc)
        state["last_task_id"] = task_id
        write_state(state)
        update_agent_status(
            "anthropic_api_pc_lbn",
            status=STATUS_USAGE_EXHAUSTED if overloaded else STATUS_DEGRADED,
            availability=not overloaded,
            reason="worker_request_failed",
            metadata={"error": str(exc), "task_id": task_id},
        )
        mark_agent_heartbeat(
            "claude_bridge_worker_pc_lbn",
            status=worker_status,
            reason="task_failed",
            metadata={"task_id": task_id, "error": str(exc)},
        )

    out = reply_path(str(data["reply_id"]))
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    processed.add(task_id)
    state["processed_tasks"] = sorted(processed)
    write_state(state)
    return True


def main() -> None:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY vazio no .env")

    ensure_dirs()
    if not acquire_single_instance():
        print("[claude-cowork-worker] outra instancia ja esta ativa. encerrando.", flush=True)
        return
    client = Anthropic(api_key=ANTHROPIC_API_KEY, timeout=30.0)
    print(f"[claude-cowork-worker] online | inbox={INBOX_DIR} | outbox={OUTBOX_DIR}")
    update_agent_status(
        "anthropic_api_pc_lbn",
        status=STATUS_AVAILABLE,
        availability=True,
        reason="worker_started",
        metadata={"primary_model": MODEL_PRIMARY, "fallback_model": MODEL_FALLBACK},
    )

    while True:
        state = read_state()
        heartbeat_worker(state)
        did_any = False
        for f in task_files():
            did_any = process_task(client, f, state) or did_any
        if not did_any:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
