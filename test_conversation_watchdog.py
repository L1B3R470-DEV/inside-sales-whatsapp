from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib import error, request


URL_RE = re.compile(r"\bhttps?:\/\/[^\s<>()]+", re.IGNORECASE)
WWW_RE = re.compile(r"\bwww\.[^\s<>()]+", re.IGNORECASE)
DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?:\/[^\s<>()]*)?", re.IGNORECASE)
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+", re.UNICODE)
MULTISPACE_RE = re.compile(r"[ \t]{2,}")
EVOLUTION_HEADER_TS_RE = re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\b")
EVOLUTION_DATE_TIME_RE = re.compile(r"date_time:\s*'([^']+)'")
EVOLUTION_REMOTE_JID_RE = re.compile(r"""remoteJid["']?\s*[:=]\s*["']([^"']+)["']""", re.IGNORECASE)
EVOLUTION_FROM_ME_RE = re.compile(r"""fromMe["']?\s*[:=]\s*(true|false)""", re.IGNORECASE)
EVOLUTION_NOT_READ_RE = re.compile(r"""not read messages\s+([^\s]+)""", re.IGNORECASE)
EVOLUTION_SENDING_RE = re.compile(r"""Sending message to\s+([^\s]+)""", re.IGNORECASE)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", str(value or ""))


def parse_ts(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                dt = None
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compact_json(value: Dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def strip_emoji_characters(value: str) -> str:
    return (
        str(value or "")
        .replace("\u200D", "")
        .replace("\uFE0F", "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )


def strip_unauthorized_links(value: str) -> str:
    text = str(value or "")

    def _drop(match: re.Match) -> str:
        start = match.start()
        prev = text[start - 1] if start > 0 else ""
        if prev == "@":
            return match.group(0)
        return ""

    return DOMAIN_RE.sub(_drop, WWW_RE.sub(_drop, URL_RE.sub(_drop, text)))


def sanitize_outbound_text(value: str, limit: int = 900) -> str:
    text = strip_unauthorized_links(strip_emoji_characters(value))
    text = EMOJI_RE.sub("", text)
    text = MULTISPACE_RE.sub(" ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    if limit > 0:
        text = text[:limit].strip()
    return text


def sha1_text(value: str) -> str:
    return hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()


@dataclass
class WatchdogConfig:
    authorized_number: str
    project_dir: Path
    runtime_root: Path
    router_db_path: Path
    router_base_url: str
    evolution_base_url: str
    evolution_api_key: str
    evolution_instance: str
    workflow_id: str
    response_timeout_seconds: int
    recovery_grace_seconds: int
    poll_interval_seconds: int
    contingency_cooldown_seconds: int
    docker_log_lookback_seconds: int
    bootstrap_log_lookback_seconds: int
    once: bool
    dry_send: bool

    @property
    def state_dir(self) -> Path:
        return self.runtime_root / "watchdog"

    @property
    def state_path(self) -> Path:
        return self.state_dir / f"test-conversation-watchdog-{self.authorized_number}.json"

    @property
    def log_path(self) -> Path:
        return self.runtime_root / "logs" / f"test-conversation-watchdog-{self.authorized_number}.log"

    @property
    def lock_path(self) -> Path:
        return self.state_dir / f"test-conversation-watchdog-{self.authorized_number}.lock"


def load_env_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def append_log(cfg: WatchdogConfig, level: str, message: str, **extra):
    cfg.log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": utc_now_iso(),
        "level": level,
        "message": message,
    }
    if extra:
        payload["extra"] = extra
    with cfg.log_path.open("a", encoding="utf-8") as fh:
        fh.write(compact_json(payload) + "\n")


def load_state(cfg: WatchdogConfig) -> Dict:
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    if not cfg.state_path.exists():
        return {
            "events": {},
            "seenEvolutionLines": {},
            "lastContingencySentAt": "",
        }
    try:
        return json.loads(cfg.state_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "events": {},
            "seenEvolutionLines": {},
            "lastContingencySentAt": "",
        }


def save_state(cfg: WatchdogConfig, state: Dict):
    events = state.get("events") or {}
    cutoff = utc_now() - timedelta(days=2)
    pruned_events = {}
    for key, value in events.items():
        resolved_at = parse_ts(value.get("resolvedAt"))
        if resolved_at and resolved_at < cutoff:
            continue
        pruned_events[key] = value
    seen_lines = state.get("seenEvolutionLines") or {}
    pruned_lines = {}
    for key, value in seen_lines.items():
        seen_at = parse_ts(value)
        if seen_at and seen_at < utc_now() - timedelta(hours=6):
            continue
        pruned_lines[key] = value
    state["events"] = pruned_events
    state["seenEvolutionLines"] = pruned_lines
    cfg.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def run_command(command: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def db_conn(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_watchdog_table(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS watchdog_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          contact_key TEXT NOT NULL,
          event_key TEXT NOT NULL,
          inbound_created_at TEXT NOT NULL,
          source TEXT NOT NULL,
          status TEXT NOT NULL,
          cause TEXT DEFAULT '',
          action TEXT DEFAULT '',
          details TEXT DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchdog_events_contact ON watchdog_events(contact_key, inbound_created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchdog_events_event_key ON watchdog_events(event_key)")
    conn.commit()


def record_watchdog_event(cfg: WatchdogConfig, event_key: str, inbound_created_at: str, source: str,
                          status: str, cause: str = "", action: str = "", details: Optional[Dict] = None):
    details_json = compact_json(details or {})
    conn = db_conn(cfg.router_db_path)
    ensure_watchdog_table(conn)
    now = utc_now_iso()
    conn.execute(
        """
        INSERT INTO watchdog_events
          (contact_key, event_key, inbound_created_at, source, status, cause, action, details, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cfg.authorized_number, event_key, inbound_created_at, source, status, cause, action, details_json, now, now),
    )
    conn.commit()
    conn.close()


def fetch_router_messages(cfg: WatchdogConfig) -> List[Dict]:
    conn = db_conn(cfg.router_db_path)
    rows = conn.execute(
        """
        SELECT direction, message_text, intent, complexity, lead_score, route_decision, created_at
        FROM conversation_history
        WHERE contact_key = ?
        ORDER BY created_at ASC
        """,
        (cfg.authorized_number,),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        item["created_dt"] = parse_ts(item.get("created_at"))
        result.append(item)
    return result


def fetch_route_logs(cfg: WatchdogConfig) -> List[Dict]:
    conn = db_conn(cfg.router_db_path)
    rows = conn.execute(
        """
        SELECT number, inbound_text, normalized_message, route_decision, cache_hit, lead_score, created_at
        FROM route_logs
        WHERE number = ?
        ORDER BY created_at DESC
        LIMIT 20
        """,
        (cfg.authorized_number,),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        item["created_dt"] = parse_ts(item.get("created_at"))
        result.append(item)
    return result


def check_router_health(cfg: WatchdogConfig) -> bool:
    try:
        req = request.Request(cfg.router_base_url.rstrip("/") + "/health", method="GET")
        with request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return bool(data.get("ok"))
    except Exception:
        return False


def get_container_state(name: str) -> Dict[str, str]:
    cp = run_command(["docker", "inspect", "--format", "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}", name], timeout=20)
    text = (cp.stdout or "").strip()
    if cp.returncode != 0 or not text:
        return {"status": "missing", "health": ""}
    status, _, health = text.partition("|")
    return {"status": status.strip(), "health": health.strip()}


def parse_evolution_timestamp(value: str | None) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    iso_dt = parse_ts(text)
    if iso_dt:
        return iso_dt
    try:
        dt = datetime.strptime(text, "%a %b %d %Y %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def build_authorized_jid_regex(number: str) -> re.Pattern:
    digits = digits_only(number)
    return re.compile(rf"{re.escape(digits)}(?::\d+)?@s\.whatsapp\.net", re.IGNORECASE)


def read_evolution_signals(cfg: WatchdogConfig, state: Dict) -> Dict[str, List[Dict]]:
    bootstrap_done = bool(state.get("bootstrapCompleted"))
    lookback_seconds = cfg.docker_log_lookback_seconds if bootstrap_done else cfg.bootstrap_log_lookback_seconds
    cp = run_command(["docker", "logs", "evolution", "--since", f"{lookback_seconds}s"], timeout=25)
    output = (cp.stdout or "") + "\n" + (cp.stderr or "")
    inbound: List[Dict] = []
    outbound: List[Dict] = []
    seen = state.setdefault("seenEvolutionLines", {})
    emitted = {"inbound": set(), "outbound": set()}
    now_iso = utc_now_iso()
    authorized_jid_re = build_authorized_jid_regex(cfg.authorized_number)
    current_log_dt: Optional[datetime] = None
    current_signal_dt: Optional[datetime] = None
    pending_remote_jid: Optional[str] = None
    pending_remote_jid_line = -9999

    def matches_authorized_jid(value: str | None) -> bool:
        return bool(authorized_jid_re.search(str(value or "")))

    def append_inbound(event_line: str, event_dt: datetime, raw: str, marker: str):
        dedupe_key = (marker, event_dt.replace(microsecond=0).isoformat())
        if dedupe_key in emitted["inbound"]:
            return
        line_hash = sha1_text(f"inbound:{event_line}")
        if line_hash in seen:
            return
        emitted["inbound"].add(dedupe_key)
        seen[line_hash] = now_iso
        inbound.append({
            "event_key": f"evolution:{line_hash}",
            "created_at": event_dt.isoformat(),
            "created_dt": event_dt,
            "source": "evolution_log",
            "text": "",
            "raw": raw,
        })

    def append_outbound(event_line: str, event_dt: datetime, raw: str, marker: str):
        dedupe_key = (marker, event_dt.replace(microsecond=0).isoformat())
        if dedupe_key in emitted["outbound"]:
            return
        line_hash = sha1_text(f"outbound:{event_line}")
        if line_hash in seen:
            return
        emitted["outbound"].add(dedupe_key)
        seen[line_hash] = now_iso
        outbound.append({
            "event_key": f"evolution-send:{line_hash}",
            "created_at": event_dt.isoformat(),
            "created_dt": event_dt,
            "source": "evolution_log",
            "raw": raw,
        })

    for idx, raw_line in enumerate(output.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        header_match = EVOLUTION_HEADER_TS_RE.search(line)
        if header_match:
            current_log_dt = parse_evolution_timestamp(header_match.group(0))
            current_signal_dt = None
        date_match = EVOLUTION_DATE_TIME_RE.search(line)
        if date_match:
            parsed_signal_dt = parse_evolution_timestamp(date_match.group(1))
            if parsed_signal_dt:
                current_signal_dt = parsed_signal_dt

        send_match = EVOLUTION_SENDING_RE.search(line)
        if send_match and matches_authorized_jid(send_match.group(1)):
            send_dt = current_log_dt or current_signal_dt or utc_now()
            append_outbound(line, send_dt, line, send_match.group(1))
            continue

        unread_match = EVOLUTION_NOT_READ_RE.search(line)
        if unread_match and matches_authorized_jid(unread_match.group(1)):
            unread_dt = current_log_dt or current_signal_dt or utc_now()
            append_inbound(line, unread_dt, line, unread_match.group(1))
            continue

        remote_match = EVOLUTION_REMOTE_JID_RE.search(line)
        if remote_match and matches_authorized_jid(remote_match.group(1)):
            pending_remote_jid = remote_match.group(1)
            pending_remote_jid_line = idx

        from_me_match = EVOLUTION_FROM_ME_RE.search(line)
        if from_me_match and pending_remote_jid and (idx - pending_remote_jid_line) <= 6:
            event_dt = current_signal_dt or current_log_dt or utc_now()
            if from_me_match.group(1).lower() == "false":
                append_inbound(f"{pending_remote_jid}|{idx}", event_dt, f"{pending_remote_jid} {line}", pending_remote_jid)
            else:
                append_outbound(f"{pending_remote_jid}|{idx}", event_dt, f"{pending_remote_jid} {line}", pending_remote_jid)
            pending_remote_jid = None
            pending_remote_jid_line = -9999
    return {"inbound": inbound, "outbound": outbound}


def query_n8n_recent(cfg: WatchdogConfig) -> List[Dict]:
    script = (
        "import sqlite3, json\n"
        "conn = sqlite3.connect('/data/database.sqlite')\n"
        "conn.row_factory = sqlite3.Row\n"
        "cur = conn.cursor()\n"
        f"rows = cur.execute(\"SELECT id, workflowId, status, mode, startedAt, stoppedAt, finished FROM execution_entity WHERE workflowId = ? ORDER BY id DESC LIMIT 8\", ({cfg.workflow_id!r},)).fetchall()\n"
        "print(json.dumps([dict(r) for r in rows], ensure_ascii=False))\n"
        "conn.close()\n"
    )
    cp = run_command(
        ["docker", "run", "--rm", "-v", "ai_n8n_data:/data", "python:3.11-slim", "python", "-c", script],
        timeout=40,
    )
    if cp.returncode != 0:
        return []
    stdout = (cp.stdout or "").strip().splitlines()
    if not stdout:
        return []
    try:
        return json.loads(stdout[-1])
    except Exception:
        return []


def build_inbound_events(router_messages: List[Dict], evolution_inbound: List[Dict]) -> List[Dict]:
    router_events = []
    router_times = []
    for msg in router_messages:
        if (msg.get("direction") or "") != "inbound":
            continue
        created_at = msg.get("created_at") or utc_now_iso()
        text = str(msg.get("message_text") or "")
        router_events.append({
            "event_key": f"router:{created_at}:{sha1_text(text)[:12]}",
            "created_at": created_at,
            "created_dt": msg.get("created_dt") or parse_ts(created_at) or utc_now(),
            "source": "router_history",
            "text": text,
            "raw": text,
        })
        router_times.append(msg.get("created_dt") or parse_ts(created_at) or utc_now())

    merged = list(router_events)
    for signal in evolution_inbound:
        created_dt = signal.get("created_dt") or utc_now()
        duplicate = False
        for dt in router_times:
            if abs((dt - created_dt).total_seconds()) <= 25:
                duplicate = True
                break
        if not duplicate:
            merged.append(signal)
    merged.sort(key=lambda item: item.get("created_dt") or utc_now())
    return merged


def has_outbound_after(inbound_dt: datetime, router_messages: List[Dict], evolution_outbound: List[Dict]) -> bool:
    for msg in router_messages:
        if (msg.get("direction") or "") != "outbound":
            continue
        created_dt = msg.get("created_dt") or parse_ts(msg.get("created_at")) or utc_now()
        if created_dt >= inbound_dt:
            return True
    for signal in evolution_outbound:
        created_dt = signal.get("created_dt") or utc_now()
        if created_dt >= inbound_dt:
            return True
    return False


def classify_cause(router_ok: bool, evolution_state: Dict[str, str], n8n_state: Dict[str, str],
                   route_logs: List[Dict], n8n_recent: List[Dict], event: Dict) -> str:
    if evolution_state.get("status") != "running":
        return "evolution_unavailable"
    if n8n_state.get("status") != "running":
        return "n8n_unavailable"
    if not router_ok:
        return "router_unhealthy"
    if n8n_recent:
        latest = n8n_recent[0]
        started = parse_ts(latest.get("startedAt"))
        if latest.get("status") == "error" and started and started >= (event["created_dt"] - timedelta(minutes=1)):
            return "n8n_execution_error"
    for item in route_logs:
        log_dt = item.get("created_dt") or utc_now()
        if log_dt >= event["created_dt"]:
            return "router_processed_no_outbound"
    return "pre_router_flow_gap" if event.get("source") == "evolution_log" else "processing_stalled"


def attempt_recovery(cfg: WatchdogConfig, cause: str) -> str:
    if cause == "router_unhealthy":
        script = cfg.project_dir / "router-watchdog.ps1"
        cp = run_command(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), "-ProjectDir", str(cfg.project_dir), "-RuntimeRoot", str(cfg.runtime_root)], timeout=45)
        return "router_watchdog_restart" if cp.returncode == 0 else "router_watchdog_failed"
    if cause in {"n8n_unavailable", "n8n_execution_error"}:
        cp = run_command(["docker", "restart", "n8n"], timeout=60)
        return "n8n_restart" if cp.returncode == 0 else "n8n_restart_failed"
    if cause == "evolution_unavailable":
        cp = run_command(["docker", "restart", "evolution"], timeout=60)
        return "evolution_restart" if cp.returncode == 0 else "evolution_restart_failed"
    return ""


def send_text(cfg: WatchdogConfig, text: str) -> Dict:
    clean = sanitize_outbound_text(text, 600)
    if not clean:
        return {"ok": False, "reason": "empty_after_sanitize"}
    if cfg.dry_send:
        return {"ok": True, "reason": "dry_send", "text": clean}
    url = f"{cfg.evolution_base_url.rstrip('/')}/message/sendText/{cfg.evolution_instance}"
    payload = json.dumps({"number": cfg.authorized_number, "text": clean}).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "apikey": cfg.evolution_api_key,
    }
    req = request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {"ok": True, "reason": "sent", "body": body, "text": clean}
    except error.HTTPError as exc:
        return {"ok": False, "reason": f"http_{exc.code}", "body": exc.read().decode('utf-8', errors='replace'), "text": clean}
    except Exception as exc:
        return {"ok": False, "reason": str(exc), "text": clean}


def record_outbound_to_router(cfg: WatchdogConfig, text: str, route_decision: str):
    clean = sanitize_outbound_text(text, 1200)
    if not clean:
        return
    conn = db_conn(cfg.router_db_path)
    conn.execute(
        """
        INSERT INTO conversation_history
          (contact_key, direction, message_text, intent, complexity, lead_score, route_decision, created_at)
        VALUES (?, 'outbound', ?, '', 'watchdog', 0, ?, ?)
        """,
        (cfg.authorized_number, clean, route_decision, utc_now_iso()),
    )
    conn.commit()
    conn.close()


def process_pending_event(cfg: WatchdogConfig, state: Dict, event: Dict, router_messages: List[Dict],
                          route_logs: List[Dict], evolution_outbound: List[Dict], system_state: Dict):
    event_key = event["event_key"]
    created_dt = event["created_dt"]
    created_at = event["created_at"]
    event_state = state.setdefault("events", {}).setdefault(event_key, {
        "firstSeenAt": utc_now_iso(),
        "source": event.get("source") or "",
        "inboundCreatedAt": created_at,
        "textHash": sha1_text(event.get("text") or ""),
        "recoveryAttemptedAt": "",
        "recoveryAction": "",
        "contingencySentAt": "",
        "resolvedAt": "",
        "status": "pending",
    })

    if event_state.get("resolvedAt"):
        return

    if has_outbound_after(created_dt, router_messages, evolution_outbound):
        event_state["resolvedAt"] = utc_now_iso()
        event_state["status"] = "resolved"
        record_watchdog_event(cfg, event_key, created_at, event.get("source") or "", "resolved", action="normal_outbound_detected")
        return

    age_seconds = max(0, int((utc_now() - created_dt).total_seconds()))
    if age_seconds < cfg.recovery_grace_seconds:
        return

    cause = classify_cause(
        bool(system_state.get("router_ok")),
        dict(system_state.get("evolution_state") or {}),
        dict(system_state.get("n8n_state") or {}),
        route_logs,
        list(system_state.get("n8n_recent") or []),
        event,
    )

    if not event_state.get("recoveryAttemptedAt"):
        recovery_action = attempt_recovery(cfg, cause)
        if recovery_action:
            event_state["recoveryAttemptedAt"] = utc_now_iso()
            event_state["recoveryAction"] = recovery_action
            event_state["status"] = "recovery_attempted"
            record_watchdog_event(
                cfg,
                event_key,
                created_at,
                event.get("source") or "",
                "recovery_attempted",
                cause=cause,
                action=recovery_action,
                details={"ageSeconds": age_seconds},
            )
            append_log(cfg, "WARN", "watchdog_recovery_attempt", event_key=event_key, cause=cause, action=recovery_action)
            return

    if age_seconds < cfg.response_timeout_seconds:
        return

    if event_state.get("contingencySentAt"):
        return

    last_contingency = parse_ts(state.get("lastContingencySentAt"))
    if last_contingency and (utc_now() - last_contingency).total_seconds() < cfg.contingency_cooldown_seconds:
        event_state["status"] = "cooldown_wait"
        record_watchdog_event(
            cfg,
            event_key,
            created_at,
            event.get("source") or "",
            "cooldown_wait",
            cause=cause,
            action="contingency_suppressed",
            details={"ageSeconds": age_seconds},
        )
        return

    contingency = (
        "Recebi sua mensagem e sigo com seu atendimento por aqui. "
        "Estou concluindo a resposta correta e te retorno em instantes."
    )
    send_result = send_text(cfg, contingency)
    if send_result.get("ok"):
        record_outbound_to_router(cfg, send_result.get("text") or contingency, "watchdog_contingency")
        event_state["contingencySentAt"] = utc_now_iso()
        event_state["status"] = "contingency_sent"
        state["lastContingencySentAt"] = event_state["contingencySentAt"]
        record_watchdog_event(
            cfg,
            event_key,
            created_at,
            event.get("source") or "",
            "contingency_sent",
            cause=cause,
            action="send_contingency",
            details={"ageSeconds": age_seconds, "sendReason": send_result.get("reason")},
        )
        append_log(cfg, "WARN", "watchdog_contingency_sent", event_key=event_key, cause=cause)
    else:
        event_state["status"] = "contingency_failed"
        record_watchdog_event(
            cfg,
            event_key,
            created_at,
            event.get("source") or "",
            "contingency_failed",
            cause=cause,
            action="send_contingency_failed",
            details={"ageSeconds": age_seconds, "sendReason": send_result.get("reason")},
        )
        append_log(cfg, "ERROR", "watchdog_contingency_failed", event_key=event_key, cause=cause, sendReason=send_result.get("reason"))


def process_once(cfg: WatchdogConfig, state: Dict):
    router_messages = fetch_router_messages(cfg)
    route_logs = fetch_route_logs(cfg)
    evolution_signals = read_evolution_signals(cfg, state)
    system_state = {
        "router_ok": check_router_health(cfg),
        "evolution_state": get_container_state("evolution"),
        "n8n_state": get_container_state("n8n"),
        "n8n_recent": query_n8n_recent(cfg),
    }
    inbound_events = build_inbound_events(router_messages, evolution_signals["inbound"])
    for event in inbound_events:
        process_pending_event(cfg, state, event, router_messages, route_logs, evolution_signals["outbound"], system_state)
    state["bootstrapCompleted"] = True


def acquire_lock(cfg: WatchdogConfig):
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    if cfg.lock_path.exists():
        try:
            payload = json.loads(cfg.lock_path.read_text(encoding="utf-8"))
            pid = int(payload.get("pid") or 0)
        except Exception:
            pid = 0
        if pid:
            try:
                os.kill(pid, 0)
                raise SystemExit("watchdog already running")
            except OSError:
                pass
    cfg.lock_path.write_text(json.dumps({"pid": os.getpid(), "startedAt": utc_now_iso()}, ensure_ascii=False), encoding="utf-8")


def release_lock(cfg: WatchdogConfig):
    try:
        if cfg.lock_path.exists():
            cfg.lock_path.unlink()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Authorized test-number conversation watchdog")
    parser.add_argument("--authorized-number", required=True)
    parser.add_argument("--project-dir", default=r"C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES")
    parser.add_argument("--runtime-root", default=r"C:\AUTOMACAO")
    parser.add_argument("--router-db-path", default=r"C:\AUTOMACAO\dados\router_runtime.sqlite")
    parser.add_argument("--router-base-url", default="http://localhost:8091")
    parser.add_argument("--evolution-base-url", default="http://localhost:8080")
    parser.add_argument("--evolution-instance", default="ATENDIMENTO_VENDAS_CLEAN")
    parser.add_argument("--evolution-api-key", default="")
    parser.add_argument("--workflow-id", default="zN3heKJVLO8w4dG6")
    parser.add_argument("--response-timeout-seconds", type=int, default=75)
    parser.add_argument("--recovery-grace-seconds", type=int, default=35)
    parser.add_argument("--poll-interval-seconds", type=int, default=8)
    parser.add_argument("--contingency-cooldown-seconds", type=int, default=120)
    parser.add_argument("--docker-log-lookback-seconds", type=int, default=180)
    parser.add_argument("--bootstrap-log-lookback-seconds", type=int, default=7200)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-send", action="store_true")
    args = parser.parse_args()

    env_map = load_env_file(Path(args.project_dir) / ".env")
    evolution_api_key = args.evolution_api_key or env_map.get("EVOLUTION_API_KEY", "")
    cfg = WatchdogConfig(
        authorized_number=digits_only(args.authorized_number),
        project_dir=Path(args.project_dir),
        runtime_root=Path(args.runtime_root),
        router_db_path=Path(args.router_db_path),
        router_base_url=args.router_base_url,
        evolution_base_url=args.evolution_base_url,
        evolution_api_key=evolution_api_key,
        evolution_instance=args.evolution_instance,
        workflow_id=args.workflow_id,
        response_timeout_seconds=max(30, args.response_timeout_seconds),
        recovery_grace_seconds=max(10, args.recovery_grace_seconds),
        poll_interval_seconds=max(3, args.poll_interval_seconds),
        contingency_cooldown_seconds=max(30, args.contingency_cooldown_seconds),
        docker_log_lookback_seconds=max(60, args.docker_log_lookback_seconds),
        bootstrap_log_lookback_seconds=max(args.docker_log_lookback_seconds, args.bootstrap_log_lookback_seconds),
        once=bool(args.once),
        dry_send=bool(args.dry_send),
    )

    if not cfg.authorized_number:
        raise SystemExit("authorized number is required")
    if not cfg.router_db_path.exists():
        raise SystemExit(f"router db not found: {cfg.router_db_path}")
    if not cfg.evolution_api_key and not cfg.dry_send:
        raise SystemExit("evolution api key is required unless --dry-send is used")

    acquire_lock(cfg)
    try:
        append_log(cfg, "INFO", "watchdog_started", authorizedNumber=cfg.authorized_number, once=cfg.once, drySend=cfg.dry_send)
        state = load_state(cfg)
        while True:
            process_once(cfg, state)
            save_state(cfg, state)
            if cfg.once:
                break
            time.sleep(cfg.poll_interval_seconds)
    finally:
        release_lock(cfg)


if __name__ == "__main__":
    main()
