import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


BRIDGE_ROOT = Path(os.getenv("CLAUDE_BRIDGE_ROOT", r"C:\AUTOMACAO\cowork\claude_bridge"))
REGISTRY_FILE = BRIDGE_ROOT / "ai_capacity_registry.json"
LOCK_FILE = BRIDGE_ROOT / "ai_capacity_registry.lock"

STATUS_AVAILABLE = "available"
STATUS_USAGE_EXHAUSTED = "usage_exhausted"
STATUS_SESSION_UNAVAILABLE = "session_unavailable"
STATUS_DEGRADED = "degraded"
STATUS_RECOVERED = "recovered"
STATUS_UNKNOWN = "unknown"

RECRUITABLE_STATUSES = {STATUS_AVAILABLE, STATUS_RECOVERED}
BACKUP_STATUSES = {STATUS_AVAILABLE, STATUS_RECOVERED, STATUS_DEGRADED}

KNOWN_AGENTS: Dict[str, Dict[str, Any]] = {
    "claude_pro_pc_cls": {
        "label": "Claude Pro",
        "machine": "PC CLS",
        "ip": "100.113.13.27",
        "kind": "external_session",
        "eligible_roles": [
            "commercial_reasoning",
            "natural_response",
            "post_conversation_learning",
            "flow_audit",
            "fallback_cognitive",
        ],
        "max_roles": 4,
        "stale_after_seconds": 900,
        "heartbeat_required": True,
    },
    "codex_pc_lbn": {
        "label": "Codex / ChatGPT",
        "machine": "PC LBN",
        "ip": "100.101.106.95",
        "kind": "session",
        "eligible_roles": [
            "technical_sidecar",
            "runtime_validation",
            "monitoring",
            "scraping_support",
            "flow_audit",
            "fallback_cognitive",
        ],
        "max_roles": 5,
        "stale_after_seconds": 180,
        "heartbeat_required": True,
    },
    "openai_primary_pc_lbn": {
        "label": "OpenAI API",
        "machine": "PC LBN",
        "ip": "100.101.106.95",
        "kind": "provider",
        "eligible_roles": [
            "commercial_reasoning",
            "natural_response",
            "structured_extraction",
            "post_conversation_learning",
            "fallback_cognitive",
        ],
        "max_roles": 4,
        "stale_after_seconds": 600,
        "heartbeat_required": False,
    },
    "anthropic_api_pc_lbn": {
        "label": "Anthropic API",
        "machine": "PC LBN",
        "ip": "100.101.106.95",
        "kind": "provider",
        "eligible_roles": [
            "commercial_reasoning",
            "natural_response",
            "post_conversation_learning",
            "flow_audit",
            "fallback_cognitive",
        ],
        "max_roles": 4,
        "stale_after_seconds": 600,
        "heartbeat_required": False,
    },
    "claude_bridge_worker_pc_lbn": {
        "label": "Claude Cowork Worker",
        "machine": "PC LBN",
        "ip": "100.101.106.95",
        "kind": "sidecar",
        "eligible_roles": ["bridge_execution"],
        "max_roles": 1,
        "stale_after_seconds": 75,
        "heartbeat_required": True,
    },
    "claude_autopilot_pc_lbn": {
        "label": "Claude Codex Autopilot",
        "machine": "PC LBN",
        "ip": "100.101.106.95",
        "kind": "sidecar",
        "eligible_roles": ["bridge_orchestration", "monitoring"],
        "max_roles": 2,
        "stale_after_seconds": 75,
        "heartbeat_required": True,
    },
    "ai_capacity_monitor_pc_lbn": {
        "label": "AI Capacity Monitor",
        "machine": "PC LBN",
        "ip": "100.101.106.95",
        "kind": "monitor",
        "eligible_roles": ["monitoring"],
        "max_roles": 1,
        "stale_after_seconds": 90,
        "heartbeat_required": True,
    },
}

ROLE_PRIORITY: Dict[str, List[str]] = {
    "commercial_reasoning": [
        "claude_pro_pc_cls",
        "anthropic_api_pc_lbn",
        "codex_pc_lbn",
        "openai_primary_pc_lbn",
    ],
    "natural_response": [
        "claude_pro_pc_cls",
        "anthropic_api_pc_lbn",
        "openai_primary_pc_lbn",
        "codex_pc_lbn",
    ],
    "structured_extraction": [
        "openai_primary_pc_lbn",
        "codex_pc_lbn",
        "anthropic_api_pc_lbn",
        "claude_pro_pc_cls",
    ],
    "post_conversation_learning": [
        "claude_pro_pc_cls",
        "anthropic_api_pc_lbn",
        "openai_primary_pc_lbn",
        "codex_pc_lbn",
    ],
    "technical_sidecar": [
        "codex_pc_lbn",
        "claude_pro_pc_cls",
        "anthropic_api_pc_lbn",
        "openai_primary_pc_lbn",
    ],
    "runtime_validation": [
        "codex_pc_lbn",
        "claude_pro_pc_cls",
        "anthropic_api_pc_lbn",
        "openai_primary_pc_lbn",
    ],
    "monitoring": [
        "ai_capacity_monitor_pc_lbn",
        "codex_pc_lbn",
        "claude_autopilot_pc_lbn",
        "claude_pro_pc_cls",
    ],
    "scraping_support": [
        "codex_pc_lbn",
        "claude_pro_pc_cls",
        "openai_primary_pc_lbn",
        "anthropic_api_pc_lbn",
    ],
    "flow_audit": [
        "claude_pro_pc_cls",
        "codex_pc_lbn",
        "anthropic_api_pc_lbn",
        "openai_primary_pc_lbn",
    ],
    "fallback_cognitive": [
        "openai_primary_pc_lbn",
        "codex_pc_lbn",
        "anthropic_api_pc_lbn",
        "claude_pro_pc_cls",
    ],
    "bridge_execution": [
        "claude_bridge_worker_pc_lbn",
    ],
    "bridge_orchestration": [
        "claude_autopilot_pc_lbn",
        "codex_pc_lbn",
    ],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_root() -> None:
    BRIDGE_ROOT.mkdir(parents=True, exist_ok=True)


def _default_registry() -> Dict[str, Any]:
    agents: Dict[str, Dict[str, Any]] = {}
    for agent_id, meta in KNOWN_AGENTS.items():
        agents[agent_id] = {
            "agent_id": agent_id,
            "label": meta["label"],
            "machine": meta["machine"],
            "ip": meta["ip"],
            "kind": meta["kind"],
            "status": STATUS_UNKNOWN,
            "availability": False,
            "reason": "bootstrap_pending",
            "last_transition_at": "",
            "last_heartbeat_at": "",
            "last_error_at": "",
            "recruitment_state": "idle",
            "eligible_roles": list(meta.get("eligible_roles") or []),
            "max_roles": int(meta.get("max_roles") or 1),
            "stale_after_seconds": int(meta.get("stale_after_seconds") or 0),
            "heartbeat_required": bool(meta.get("heartbeat_required")),
            "metadata": {},
        }
    return {
        "updated_at": now_iso(),
        "agents": agents,
        "roles": {},
        "events": [],
    }


def _read_registry_unlocked() -> Dict[str, Any]:
    _ensure_root()
    if not REGISTRY_FILE.exists():
        data = _default_registry()
        _write_registry_unlocked(data)
        return data
    try:
        data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = _default_registry()
    agents = data.setdefault("agents", {})
    for agent_id, meta in KNOWN_AGENTS.items():
        if agent_id not in agents:
            agents[agent_id] = _default_registry()["agents"][agent_id]
        else:
            for field in ("label", "machine", "ip", "kind", "eligible_roles", "max_roles", "stale_after_seconds", "heartbeat_required"):
                agents[agent_id][field] = _default_registry()["agents"][agent_id][field]
    data.setdefault("roles", {})
    data.setdefault("events", [])
    return data


def _write_registry_unlocked(data: Dict[str, Any]) -> None:
    data["updated_at"] = now_iso()
    temp = REGISTRY_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(REGISTRY_FILE)


@contextmanager
def _locked_registry(timeout_seconds: float = 5.0):
    _ensure_root()
    deadline = time.monotonic() + max(0.2, timeout_seconds)
    while True:
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii", errors="ignore"))
            os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError("ai_capacity_registry_lock_timeout")
            time.sleep(0.05)
    try:
        data = _read_registry_unlocked()
        yield data
        _write_registry_unlocked(data)
    finally:
        try:
            LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass


def _append_event(data: Dict[str, Any], event: Dict[str, Any]) -> None:
    events = data.setdefault("events", [])
    event.setdefault("created_at", now_iso())
    events.append(event)
    if len(events) > 200:
        del events[:-200]


def _status_priority(status: str) -> int:
    if status in RECRUITABLE_STATUSES:
        return 0
    if status == STATUS_DEGRADED:
        return 1
    if status == STATUS_UNKNOWN:
        return 2
    return 3


def _recompute_roles(data: Dict[str, Any]) -> None:
    agents = data.get("agents", {})
    assignments: Dict[str, Dict[str, Any]] = {}
    loads: Dict[str, int] = {agent_id: 0 for agent_id in agents}

    for role, ordered_agents in ROLE_PRIORITY.items():
        candidates: List[str] = []
        degraded: List[str] = []
        unavailable: List[str] = []
        for agent_id in ordered_agents:
            agent = agents.get(agent_id) or {}
            status = str(agent.get("status") or STATUS_UNKNOWN)
            available = bool(agent.get("availability"))
            if not available:
                unavailable.append(agent_id)
                continue
            if role not in (agent.get("eligible_roles") or []):
                continue
            if status in RECRUITABLE_STATUSES:
                candidates.append(agent_id)
            elif status in BACKUP_STATUSES:
                degraded.append(agent_id)
            else:
                unavailable.append(agent_id)

        chosen = ""
        for agent_id in candidates:
            agent = agents.get(agent_id) or {}
            if loads.get(agent_id, 0) < int(agent.get("max_roles") or 1):
                chosen = agent_id
                loads[agent_id] = loads.get(agent_id, 0) + 1
                break
        if not chosen and degraded:
            chosen = degraded[0]
            loads[chosen] = loads.get(chosen, 0) + 1

        backups = [agent_id for agent_id in [*candidates, *degraded] if agent_id != chosen]
        assignments[role] = {
            "primary": chosen,
            "backups": backups,
            "unavailable": unavailable,
        }

    for agent_id, agent in agents.items():
        current_roles = [role for role, payload in assignments.items() if payload.get("primary") == agent_id]
        agent["assigned_roles"] = current_roles
        agent["recruitment_state"] = "recruited" if current_roles else "idle"

    data["roles"] = assignments


def _apply_stale_rules(data: Dict[str, Any]) -> None:
    current_ts = datetime.now(timezone.utc).timestamp()
    for agent_id, agent in data.get("agents", {}).items():
        if not agent.get("heartbeat_required"):
            continue
        heartbeat = str(agent.get("last_heartbeat_at") or "").strip()
        stale_after = int(agent.get("stale_after_seconds") or 0)
        if not heartbeat or stale_after <= 0:
            continue
        try:
            heartbeat_ts = datetime.fromisoformat(heartbeat.replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        if current_ts - heartbeat_ts <= stale_after:
            continue
        previous_status = str(agent.get("status") or STATUS_UNKNOWN)
        if previous_status == STATUS_SESSION_UNAVAILABLE and agent.get("reason") == "heartbeat_stale":
            continue
        agent["status"] = STATUS_SESSION_UNAVAILABLE
        agent["availability"] = False
        agent["reason"] = "heartbeat_stale"
        agent["last_transition_at"] = now_iso()
        _append_event(
            data,
            {
                "type": "status_transition",
                "agent_id": agent_id,
                "from_status": previous_status,
                "to_status": STATUS_SESSION_UNAVAILABLE,
                "reason": "heartbeat_stale",
            },
        )


def bootstrap_registry() -> Dict[str, Any]:
    with _locked_registry() as data:
        _apply_stale_rules(data)
        _recompute_roles(data)
        return data


def update_agent_status(
    agent_id: str,
    *,
    status: str,
    availability: Optional[bool] = None,
    reason: str = "",
    heartbeat: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    with _locked_registry() as data:
        agents = data.setdefault("agents", {})
        agent = agents.setdefault(agent_id, _default_registry()["agents"].get(agent_id, {
            "agent_id": agent_id,
            "label": agent_id,
            "machine": "",
            "ip": "",
            "kind": "unknown",
            "eligible_roles": [],
            "max_roles": 1,
            "stale_after_seconds": 0,
            "heartbeat_required": False,
            "metadata": {},
        }))

        previous_status = str(agent.get("status") or STATUS_UNKNOWN)
        previous_availability = bool(agent.get("availability"))
        if availability is None:
            availability = status in BACKUP_STATUSES
        changed = previous_status != status or previous_availability != bool(availability) or reason != str(agent.get("reason") or "")

        agent["status"] = status
        agent["availability"] = bool(availability)
        agent["reason"] = reason
        if heartbeat:
            agent["last_heartbeat_at"] = now_iso()
        if status in {STATUS_USAGE_EXHAUSTED, STATUS_DEGRADED, STATUS_SESSION_UNAVAILABLE}:
            agent["last_error_at"] = now_iso()
        if metadata:
            merged = dict(agent.get("metadata") or {})
            merged.update(metadata)
            agent["metadata"] = merged
        if changed:
            agent["last_transition_at"] = now_iso()
            _append_event(
                data,
                {
                    "type": "status_transition",
                    "agent_id": agent_id,
                    "from_status": previous_status,
                    "to_status": status,
                    "reason": reason,
                },
            )
        _apply_stale_rules(data)
        _recompute_roles(data)
        return data


def mark_agent_heartbeat(agent_id: str, *, status: Optional[str] = None, reason: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    target_status = status or STATUS_AVAILABLE
    return update_agent_status(
        agent_id,
        status=target_status,
        availability=target_status in BACKUP_STATUSES,
        reason=reason or "heartbeat",
        heartbeat=True,
        metadata=metadata,
    )


def get_registry_snapshot() -> Dict[str, Any]:
    with _locked_registry() as data:
        _apply_stale_rules(data)
        _recompute_roles(data)
        return json.loads(json.dumps(data))


def get_role_assignment(role: str) -> Dict[str, Any]:
    data = get_registry_snapshot()
    return data.get("roles", {}).get(role, {"primary": "", "backups": [], "unavailable": []})


def summarize_registry() -> Dict[str, Any]:
    data = get_registry_snapshot()
    agents = data.get("agents", {})
    summary_agents = {}
    for agent_id, agent in agents.items():
        summary_agents[agent_id] = {
            "label": agent.get("label", ""),
            "machine": agent.get("machine", ""),
            "status": agent.get("status", STATUS_UNKNOWN),
            "availability": bool(agent.get("availability")),
            "reason": agent.get("reason", ""),
            "assigned_roles": agent.get("assigned_roles", []),
            "last_heartbeat_at": agent.get("last_heartbeat_at", ""),
            "last_transition_at": agent.get("last_transition_at", ""),
        }
    return {
        "updated_at": data.get("updated_at", ""),
        "agents": summary_agents,
        "roles": data.get("roles", {}),
        "recent_events": data.get("events", [])[-20:],
    }
