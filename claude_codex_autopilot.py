import json
import os
import re
import time
import atexit
import ctypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


BRIDGE_ROOT = Path(os.getenv("CLAUDE_BRIDGE_ROOT", r"C:\AUTOMACAO\cowork\claude_bridge"))
INBOX_FOR_CLAUDE = BRIDGE_ROOT / "inbox_for_claude"
OUTBOX_FROM_CLAUDE = BRIDGE_ROOT / "outbox_from_claude"
ACK_FROM_CODEX = BRIDGE_ROOT / "ack_from_codex"

AUTOPLAN_INBOX = BRIDGE_ROOT / "autoplan_inbox"
AUTOPLAN_PROCESSED = BRIDGE_ROOT / "autoplan_processed"
AUTOPLAN_FAILED = BRIDGE_ROOT / "autoplan_failed"

STATE_FILE = BRIDGE_ROOT / "autopilot_state.json"
LOG_FILE = BRIDGE_ROOT / "autopilot.log"
POLL_SECONDS = int(os.getenv("CLAUDE_AUTOPILOT_POLL_SECONDS", "4"))
LOCK_FILE = BRIDGE_ROOT / "autopilot.lock"
MUTEX_NAME = os.getenv("CLAUDE_AUTOPILOT_MUTEX_NAME", r"Local\WA_Claude_Codex_Autopilot")
MUTEX_HANDLE = None

AGENT_BY_KIND = {
    "debug": "debug-lead",
    "qa": "test-msg",
    "integration": "flow",
    "cost": "metrics",
    "docs": "status",
    "implementation": "router",
}

MCP_HINT_BY_KIND = {
    "debug": ["sqlite-router", "fetch"],
    "qa": ["fetch"],
    "integration": ["fetch", "sqlite-router"],
    "cost": ["fetch", "sqlite-router"],
    "docs": ["fetch"],
    "implementation": ["sqlite-router", "fetch"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def write_log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def ensure_dirs() -> None:
    for p in [
        BRIDGE_ROOT,
        INBOX_FOR_CLAUDE,
        OUTBOX_FROM_CLAUDE,
        ACK_FROM_CODEX,
        AUTOPLAN_INBOX,
        AUTOPLAN_PROCESSED,
        AUTOPLAN_FAILED,
    ]:
        p.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        state = {
            "seen_replies": [],
            "seen_master_tasks": [],
            "created_subtasks": [],
            "created_at": now_iso(),
        }
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def acquire_lock() -> bool:
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

    if LOCK_FILE.exists():
        try:
            old_pid = int((LOCK_FILE.read_text(encoding="utf-8") or "0").strip())
            if _pid_alive(old_pid):
                if MUTEX_HANDLE and os.name == "nt":
                    ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(MUTEX_HANDLE))
                    MUTEX_HANDLE = None
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
        if MUTEX_HANDLE and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(MUTEX_HANDLE))
            MUTEX_HANDLE = None
        return False


def release_lock() -> None:
    try:
        if LOCK_FILE.exists():
            owner = int((LOCK_FILE.read_text(encoding="utf-8") or "0").strip())
            if owner == os.getpid():
                LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    if MUTEX_HANDLE and os.name == "nt":
        try:
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(MUTEX_HANDLE))
        except Exception:
            pass


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, payload: Dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> Dict:
    return read_json(
        STATE_FILE,
        {
            "seen_replies": [],
            "seen_master_tasks": [],
            "created_subtasks": [],
            "created_at": now_iso(),
        },
    )


def save_state(state: Dict) -> None:
    write_json(STATE_FILE, state)


def normalize_text(value: str) -> str:
    text = str(value or "").lower()
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def ack_outbox_replies(state: Dict) -> int:
    seen = set(state.get("seen_replies", []))
    changed = 0
    for f in sorted(OUTBOX_FROM_CLAUDE.glob("REPLY-*.json"), key=lambda p: p.stat().st_mtime):
        reply = read_json(f, {})
        reply_id = str(reply.get("reply_id") or f.stem).strip()
        if not reply_id or reply_id in seen:
            continue

        ack_payload = {
            "reply_id": reply_id,
            "acked_at": now_iso(),
            "from": "codex-autopilot",
            "to": "claude",
            "status": "received",
            "source_file": str(f),
        }
        ack_file = ACK_FROM_CODEX / f"ACK-{reply_id}.json"
        write_json(ack_file, ack_payload)

        seen.add(reply_id)
        changed += 1
        write_log(f"ACK criado para {reply_id}")

    if changed:
        state["seen_replies"] = sorted(seen)
    return changed


def parse_master_task(path: Path) -> Tuple[str, Dict]:
    if path.suffix.lower() == ".json":
        task = read_json(path, {})
        task_id = str(task.get("task_id") or path.stem).strip()
        title = str(task.get("title") or "Tarefa sem titulo").strip()
        body = str(task.get("body") or "").strip()
        refs = task.get("references") or []
        refs = [str(x).strip() for x in refs if str(x).strip()]
        preferred_agent = str(task.get("preferred_agent") or "").strip()
    else:
        body = path.read_text(encoding="utf-8-sig").strip()
        task_id = path.stem
        title = f"Tarefa importada de arquivo: {path.name}"
        refs = []
        preferred_agent = ""

    payload = {
        "task_id": task_id,
        "title": title,
        "body": body,
        "references": refs,
        "preferred_agent": preferred_agent,
        "created_at": now_iso(),
    }
    return task_id, payload


def classify_subtasks(task: Dict) -> List[Dict]:
    title = str(task.get("title", "")).strip()
    body = str(task.get("body", "")).strip()
    text = normalize_text(f"{title} {body}")

    def has_any(words: List[str]) -> bool:
        return any(w in text for w in words)

    subtasks: List[Dict] = []

    if has_any(["erro", "falha", "bug", "exception", "traceback", "crash", "timeout"]):
        subtasks.append(
            {
                "kind": "debug",
                "title": f"[DEBUG] {title}",
                "body": (
                    f"Diagnostique e proponha correcao para o problema abaixo:\n\n{body}\n\n"
                    "Entregue causa raiz, patch sugerido e validacao."
                ),
            }
        )

    if has_any(["teste", "validar", "qa", "homolog", "checagem"]):
        subtasks.append(
            {
                "kind": "qa",
                "title": f"[QA] {title}",
                "body": (
                    f"Monte plano de testes para:\n\n{body}\n\n"
                    "Liste casos felizes, borda e regressao com criterio de aceite."
                ),
            }
        )

    if has_any(["n8n", "evolution", "api", "webhook", "router", "integracao"]):
        subtasks.append(
            {
                "kind": "integration",
                "title": f"[INTEGRACAO] {title}",
                "body": (
                    f"Detalhe a implementacao de integracao para:\n\n{body}\n\n"
                    "Entregue payloads, endpoints e pontos de falha/retentativa."
                ),
            }
        )

    if has_any(["custo", "token", "modelo", "latencia", "preco", "econom"]):
        subtasks.append(
            {
                "kind": "cost",
                "title": f"[CUSTO] {title}",
                "body": (
                    f"Otimize custo e desempenho para:\n\n{body}\n\n"
                    "Entregue proposta com tradeoffs e configuracoes recomendadas."
                ),
            }
        )

    if has_any(["doc", "document", "dossie", "manual", "readme", "handoff"]):
        subtasks.append(
            {
                "kind": "docs",
                "title": f"[DOCUMENTACAO] {title}",
                "body": (
                    f"Produza documentacao objetiva para:\n\n{body}\n\n"
                    "Entregue formato operacional para execucao em ambiente real."
                ),
            }
        )

    if not subtasks:
        subtasks.append(
            {
                "kind": "implementation",
                "title": f"[IMPLEMENTACAO] {title}",
                "body": (
                    f"Quebre em passos de implementacao e entregue plano executavel:\n\n{body}\n\n"
                    "Saida: passos, riscos, validacao."
                ),
            }
        )

    # limite de 3 subtarefas para manter controle
    return subtasks[:3]


def create_subtask_file(master_task: Dict, subtask: Dict, idx: int, total: int) -> Path:
    master_id = str(master_task.get("task_id") or f"MASTER-{now_stamp()}").strip()
    task_id = f"{master_id}-S{idx}"
    preferred_agent = str(master_task.get("preferred_agent") or "").strip()
    target_agent = preferred_agent or AGENT_BY_KIND.get(subtask["kind"], "router")
    mcp_hints = MCP_HINT_BY_KIND.get(subtask["kind"], ["fetch"])
    payload = {
        "task_id": task_id,
        "created_at": now_iso(),
        "from": "codex-autopilot",
        "to": "claude",
        "target_agent": target_agent,
        "title": subtask["title"],
        "body": (
            f"{subtask['body']}\n\n"
            f"Contexto da tarefa mae: {master_id}\n"
            f"Subtarefa {idx}/{total} tipo={subtask['kind']}.\n"
            f"Executar preferencialmente com o agente Claude: {target_agent}."
        ),
        "references": master_task.get("references", []),
        "required_output": "JSON com status, summary, changes, risks, next_steps.",
        "meta": {
            "master_task_id": master_id,
            "subtask_index": idx,
            "subtask_total": total,
            "subtask_kind": subtask["kind"],
            "target_agent": target_agent,
            "mcp_servers_hint": mcp_hints,
        },
    }
    target = INBOX_FOR_CLAUDE / f"{task_id}.json"
    write_json(target, payload)
    return target


def process_master_tasks(state: Dict) -> int:
    seen = set(state.get("seen_master_tasks", []))
    created = set(state.get("created_subtasks", []))
    changed = 0

    candidates = sorted(
        [*AUTOPLAN_INBOX.glob("*.json"), *AUTOPLAN_INBOX.glob("*.txt")],
        key=lambda p: p.stat().st_mtime,
    )

    for f in candidates:
        try:
            master_id, master = parse_master_task(f)
            if not master_id or master_id in seen:
                continue

            subtasks = classify_subtasks(master)
            total = len(subtasks)
            for idx, st in enumerate(subtasks, start=1):
                created_file = create_subtask_file(master, st, idx, total)
                created.add(created_file.name)
                write_log(f"Subtarefa criada: {created_file.name}")

            seen.add(master_id)
            changed += 1
            f.rename(AUTOPLAN_PROCESSED / f.name)
        except Exception as exc:
            write_log(f"Falha ao processar {f.name}: {exc}")
            try:
                f.rename(AUTOPLAN_FAILED / f.name)
            except Exception:
                pass

    if changed:
        state["seen_master_tasks"] = sorted(seen)
        state["created_subtasks"] = sorted(created)
    return changed


def main() -> None:
    ensure_dirs()
    if not acquire_lock():
        print("[autopilot] outra instancia ja esta ativa. encerrando.", flush=True)
        return
    atexit.register(release_lock)
    write_log("Autopilot iniciado.")
    while True:
        state = load_state()
        a = ack_outbox_replies(state)
        b = process_master_tasks(state)
        if a or b:
            save_state(state)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
