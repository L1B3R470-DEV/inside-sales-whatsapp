import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from ai_capacity_registry import (
    STATUS_AVAILABLE,
    STATUS_DEGRADED,
    STATUS_SESSION_UNAVAILABLE,
    STATUS_UNKNOWN,
    bootstrap_registry,
    mark_agent_heartbeat,
    summarize_registry,
    update_agent_status,
)


load_dotenv(Path(__file__).resolve().parent / ".env")

BRIDGE_ROOT = Path(os.getenv("CLAUDE_BRIDGE_ROOT", r"C:\AUTOMACAO\cowork\claude_bridge"))
WORKER_STATE_FILE = BRIDGE_ROOT / "worker_state.json"
AUTOPILOT_STATE_FILE = BRIDGE_ROOT / "autopilot_state.json"
CLAUDE_PRO_CLS_PROBE_FILE = BRIDGE_ROOT / "claude_pro_pc_cls_probe.json"
POLL_SECONDS = int(os.getenv("AI_CAPACITY_MONITOR_POLL_SECONDS", "20"))


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _status_from_probe(path: Path, agent_id: str, missing_reason: str) -> None:
    payload = _read_json(path)
    if not payload:
        update_agent_status(
            agent_id,
            status=STATUS_SESSION_UNAVAILABLE,
            availability=False,
            reason=missing_reason,
            metadata={"probe_file": str(path)},
        )
        return
    raw_status = str(payload.get("status") or STATUS_UNKNOWN).strip() or STATUS_UNKNOWN
    available = bool(payload.get("available", raw_status in {STATUS_AVAILABLE, "recovered", STATUS_DEGRADED}))
    reason = str(payload.get("reason") or "probe_update").strip()
    metadata = dict(payload.get("metadata") or {})
    metadata["probe_file"] = str(path)
    update_agent_status(
        agent_id,
        status=raw_status,
        availability=available,
        reason=reason,
        heartbeat=True,
        metadata=metadata,
    )


def _sidecar_state_probe(path: Path, agent_id: str, missing_reason: str) -> None:
    payload = _read_json(path)
    if not payload:
        update_agent_status(
            agent_id,
            status=STATUS_SESSION_UNAVAILABLE,
            availability=False,
            reason=missing_reason,
            metadata={"state_file": str(path)},
        )
        return

    raw_status = str(payload.get("status") or STATUS_AVAILABLE).strip() or STATUS_AVAILABLE
    last_error = str(payload.get("last_error") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    metadata = {
        "state_file": str(path),
        "last_task_id": payload.get("last_task_id", ""),
        "processed_count": len(payload.get("processed_tasks", []) or []),
        "last_success_at": payload.get("last_success_at", ""),
        "last_error_at": payload.get("last_error_at", ""),
    }
    if last_error:
        metadata["last_error"] = last_error
    update_agent_status(
        agent_id,
        status=raw_status,
        availability=raw_status in {STATUS_AVAILABLE, "recovered", STATUS_DEGRADED},
        reason=reason or "state_probe",
        heartbeat=True,
        metadata=metadata,
    )


def monitor_once() -> Dict[str, Any]:
    bootstrap_registry()
    mark_agent_heartbeat(
        "ai_capacity_monitor_pc_lbn",
        reason="monitor_cycle",
        metadata={"poll_seconds": POLL_SECONDS},
    )
    mark_agent_heartbeat(
        "codex_pc_lbn",
        reason="monitor_cycle",
        metadata={"runtime": "codex_desktop"},
    )

    openai_available = bool(os.getenv("OPENAI_API_KEY", "").strip())
    anthropic_available = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    update_agent_status(
        "openai_primary_pc_lbn",
        status=STATUS_AVAILABLE if openai_available else STATUS_SESSION_UNAVAILABLE,
        availability=openai_available,
        reason="env_key_present" if openai_available else "missing_openai_api_key",
    )
    update_agent_status(
        "anthropic_api_pc_lbn",
        status=STATUS_AVAILABLE if anthropic_available else STATUS_SESSION_UNAVAILABLE,
        availability=anthropic_available,
        reason="env_key_present" if anthropic_available else "missing_anthropic_api_key",
    )

    _sidecar_state_probe(
        WORKER_STATE_FILE,
        "claude_bridge_worker_pc_lbn",
        "worker_state_missing",
    )
    _sidecar_state_probe(
        AUTOPILOT_STATE_FILE,
        "claude_autopilot_pc_lbn",
        "autopilot_state_missing",
    )
    _status_from_probe(
        CLAUDE_PRO_CLS_PROBE_FILE,
        "claude_pro_pc_cls",
        "pc_cls_probe_missing",
    )
    return summarize_registry()


def main() -> None:
    print(f"[ai-capacity-monitor] online | registry={BRIDGE_ROOT / 'ai_capacity_registry.json'}", flush=True)
    while True:
        monitor_once()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
