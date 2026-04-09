from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP


BRIDGE_ROOT = Path(os.getenv("CLAUDE_BRIDGE_ROOT", r"C:\AUTOMACAO\cowork\claude_bridge"))
ATTENDANT_OPERATIONAL_HOST_ROLE = os.getenv("ATTENDANT_OPERATIONAL_HOST_ROLE", "PC_CLS").strip() or "PC_CLS"
ATTENDANT_OPERATIONAL_HOST_IP = os.getenv("ATTENDANT_OPERATIONAL_HOST_IP", "100.113.13.27").strip() or "100.113.13.27"
ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE = os.getenv("ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE", ATTENDANT_OPERATIONAL_HOST_ROLE).strip() or ATTENDANT_OPERATIONAL_HOST_ROLE
ATTENDANT_OPERATIONAL_DOCKER_HOST_IP = os.getenv("ATTENDANT_OPERATIONAL_DOCKER_HOST_IP", ATTENDANT_OPERATIONAL_HOST_IP).strip() or ATTENDANT_OPERATIONAL_HOST_IP
ATTENDANT_INTERACTIVE_HOST_ROLE = os.getenv("ATTENDANT_INTERACTIVE_HOST_ROLE", "PC_LBN").strip() or "PC_LBN"
ATTENDANT_INTERACTIVE_HOST_IP = os.getenv("ATTENDANT_INTERACTIVE_HOST_IP", "100.101.106.95").strip() or "100.101.106.95"
ATTENDANT_INTERACTIVE_MODE_ONLY = os.getenv("ATTENDANT_INTERACTIVE_MODE_ONLY", "true").strip().lower() in {"1", "true", "yes", "on"}
INBOX_FOR_CLAUDE = BRIDGE_ROOT / "inbox_for_claude"
OUTBOX_FROM_CLAUDE = BRIDGE_ROOT / "outbox_from_claude"
ACK_FROM_CODEX = BRIDGE_ROOT / "ack_from_codex"
AUTOPLAN_INBOX = BRIDGE_ROOT / "autoplan_inbox"
AUTOPLAN_PROCESSED = BRIDGE_ROOT / "autoplan_processed"
AUTOPLAN_FAILED = BRIDGE_ROOT / "autoplan_failed"
LOG_FILE = BRIDGE_ROOT / "autopilot.log"

mcp = FastMCP("bridge-monitor")


def _safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _list_json_files(folder: Path, pattern: str = "*.json", limit: int = 20) -> List[Path]:
    if not folder.exists():
        return []
    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[: max(1, min(200, int(limit)))]


def _fmt_ts(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat()
    except Exception:
        return ""


def _topology_metadata() -> Dict[str, Any]:
    return {
        "operationalHostRole": ATTENDANT_OPERATIONAL_HOST_ROLE,
        "operationalHostIp": ATTENDANT_OPERATIONAL_HOST_IP,
        "operationalDockerHostRole": ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE,
        "operationalDockerHostIp": ATTENDANT_OPERATIONAL_DOCKER_HOST_IP,
        "interactiveHostRole": ATTENDANT_INTERACTIVE_HOST_ROLE,
        "interactiveHostIp": ATTENDANT_INTERACTIVE_HOST_IP,
        "interactiveModeOnly": ATTENDANT_INTERACTIVE_MODE_ONLY,
    }


@mcp.tool()
def bridge_status() -> Dict[str, Any]:
    """Resumo do estado da ponte Codex<->Claude (contadores e caminhos)."""
    status = {
        "bridgeRoot": str(BRIDGE_ROOT),
        "topology": _topology_metadata(),
        "paths": {
            "inboxForClaude": str(INBOX_FOR_CLAUDE),
            "outboxFromClaude": str(OUTBOX_FROM_CLAUDE),
            "ackFromCodex": str(ACK_FROM_CODEX),
            "autoplanInbox": str(AUTOPLAN_INBOX),
            "autoplanProcessed": str(AUTOPLAN_PROCESSED),
            "autoplanFailed": str(AUTOPLAN_FAILED),
        },
        "counts": {
            "inboxForClaude": len(_list_json_files(INBOX_FOR_CLAUDE, "*.json", 5000)),
            "outboxFromClaude": len(_list_json_files(OUTBOX_FROM_CLAUDE, "*.json", 5000)),
            "ackFromCodex": len(_list_json_files(ACK_FROM_CODEX, "*.json", 5000)),
            "autoplanInbox": len(_list_json_files(AUTOPLAN_INBOX, "*.json", 5000))
            + len(_list_json_files(AUTOPLAN_INBOX, "*.txt", 5000)),
            "autoplanProcessed": len(_list_json_files(AUTOPLAN_PROCESSED, "*.json", 5000))
            + len(_list_json_files(AUTOPLAN_PROCESSED, "*.txt", 5000)),
            "autoplanFailed": len(_list_json_files(AUTOPLAN_FAILED, "*.json", 5000))
            + len(_list_json_files(AUTOPLAN_FAILED, "*.txt", 5000)),
        },
    }
    return status


@mcp.tool()
def recent_replies(limit: int = 10) -> List[Dict[str, Any]]:
    """Ultimas respostas do Claude (outbox_from_claude)."""
    out: List[Dict[str, Any]] = []
    for f in _list_json_files(OUTBOX_FROM_CLAUDE, "REPLY-*.json", limit):
        payload = _safe_read_json(f)
        out.append(
            {
                "file": f.name,
                "modifiedAt": _fmt_ts(f),
                "reply_id": payload.get("reply_id", f.stem),
                "task_id": payload.get("task_id", ""),
                "status": payload.get("status", ""),
                "summary": str(payload.get("summary", ""))[:300],
            }
        )
    return out


@mcp.tool()
def pending_tasks(limit: int = 20) -> List[Dict[str, Any]]:
    """Tarefas pendentes para Claude (inbox_for_claude)."""
    out: List[Dict[str, Any]] = []
    for f in _list_json_files(INBOX_FOR_CLAUDE, "*.json", limit):
        payload = _safe_read_json(f)
        out.append(
            {
                "file": f.name,
                "modifiedAt": _fmt_ts(f),
                "task_id": payload.get("task_id", f.stem),
                "title": payload.get("title", ""),
                "target_agent": payload.get("target_agent", payload.get("meta", {}).get("target_agent", "")),
                "required_output": payload.get("required_output", ""),
            }
        )
    return out


@mcp.tool()
def recent_acks(limit: int = 10) -> List[Dict[str, Any]]:
    """Ultimos ACKs do Codex autopilot para respostas do Claude."""
    out: List[Dict[str, Any]] = []
    for f in _list_json_files(ACK_FROM_CODEX, "ACK-*.json", limit):
        payload = _safe_read_json(f)
        out.append(
            {
                "file": f.name,
                "modifiedAt": _fmt_ts(f),
                "reply_id": payload.get("reply_id", ""),
                "acked_at": payload.get("acked_at", ""),
                "status": payload.get("status", ""),
            }
        )
    return out


@mcp.tool()
def tail_autopilot_log(lines: int = 40) -> List[str]:
    """Retorna as ultimas linhas do autopilot.log."""
    n = max(1, min(500, int(lines)))
    if not LOG_FILE.exists():
        return []
    content = LOG_FILE.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    return content[-n:]


if __name__ == "__main__":
    mcp.run()

