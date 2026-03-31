import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_PROJECT_DIR = Path(r"C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES")
DEFAULT_RUNTIME_ROOT = Path(r"C:\AUTOMACAO")
DEFAULT_WORKFLOW_ID = "zN3heKJVLO8w4dG6"


def normalize_number(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if not digits:
        raise ValueError("number_empty")
    return digits


def run(cmd, check=True, capture=False):
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
    )


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def backup_file(src: Path, dest_dir: Path, label: str, ts: str):
    if src.exists():
        target = dest_dir / f"{label}-{ts}{src.suffix}"
        shutil.copy2(src, target)
        return str(target)
    return None


def backup_n8n_db(project_dir: Path, backup_dir: Path, ts: str):
    target_name = f"n8n-database-{ts}.sqlite"
    cmd = [
        "docker", "run", "--rm",
        "-v", "ai_n8n_data:/data",
        "-v", f"{backup_dir}:/backup",
        "python:3.11-slim",
        "sh", "-lc",
        f"cp /data/database.sqlite /backup/{target_name}",
    ]
    run(cmd)
    return str(backup_dir / target_name)


def backup_evolution_db(backup_dir: Path, ts: str):
    container_tmp = f"/tmp/evolution-full-{ts}.sql"
    host_target = backup_dir / f"evolution-full-{ts}.sql"
    run([
        "docker", "exec", "evolution-postgres",
        "sh", "-lc",
        f"pg_dump -U evolution -d evolution > {container_tmp}",
    ])
    run(["docker", "cp", f"evolution-postgres:{container_tmp}", str(host_target)])
    return str(host_target)


def cleanup_sqlite_number(db_path: Path, table_map: dict[str, str], number: str, dry_run: bool):
    result = {"db": str(db_path), "tables": {}}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for table, column in table_map.items():
        count = cur.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" = ?', (number,)).fetchone()[0]
        result["tables"][table] = count
        if not dry_run and count:
            cur.execute(f'DELETE FROM "{table}" WHERE "{column}" = ?', (number,))
    if not dry_run:
        conn.commit()
    result["remaining"] = {}
    for table, column in table_map.items():
        remaining = cur.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" = ?', (number,)).fetchone()[0]
        result["remaining"][table] = remaining
    conn.close()
    return result


def prune_value(obj, needle: str):
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if needle in str(key):
                continue
            pruned = prune_value(value, needle)
            if pruned is None:
                continue
            out[key] = pruned
        return out
    if isinstance(obj, list):
        out = []
        for item in obj:
            pruned = prune_value(item, needle)
            if pruned is None:
                continue
            out.append(pruned)
        return out
    if isinstance(obj, str) and needle in obj:
        return None
    return obj


def cleanup_n8n_internal(number: str, workflow_id: str, db_path: str = "/data/database.sqlite", dry_run: bool = False):
    conn = sqlite3.connect(db_path, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()

    row = cur.execute("SELECT staticData FROM workflow_entity WHERE id = ?", (workflow_id,)).fetchone()
    static_data_raw = row["staticData"] if row else None
    static_data = json.loads(static_data_raw) if static_data_raw else {}
    static_has_number_before = number in json.dumps(static_data, ensure_ascii=False)
    pruned_static = prune_value(static_data, number)

    execution_ids = [
        r["executionId"]
        for r in cur.execute(
            "SELECT executionId FROM execution_data WHERE data LIKE ? OR workflowData LIKE ? ORDER BY executionId",
            (f"%{number}%", f"%{number}%"),
        ).fetchall()
    ]

    if not dry_run:
        cur.execute(
            'UPDATE workflow_entity SET staticData = ?, updatedAt = STRFTIME("%Y-%m-%d %H:%M:%f", "NOW") WHERE id = ?',
            (json.dumps(pruned_static, ensure_ascii=False, separators=(",", ":")), workflow_id),
        )
        if execution_ids:
            placeholders = ",".join("?" * len(execution_ids))
            annotation_ids = [
                r["id"]
                for r in cur.execute(
                    f"SELECT id FROM execution_annotations WHERE executionId IN ({placeholders})",
                    execution_ids,
                ).fetchall()
            ]
            if annotation_ids:
                ann_placeholders = ",".join("?" * len(annotation_ids))
                cur.execute(
                    f"DELETE FROM execution_annotation_tags WHERE annotationId IN ({ann_placeholders})",
                    annotation_ids,
                )
            cur.execute(f"DELETE FROM execution_annotations WHERE executionId IN ({placeholders})", execution_ids)
            cur.execute(f"DELETE FROM execution_metadata WHERE executionId IN ({placeholders})", execution_ids)
            cur.execute(
                f"DELETE FROM test_case_execution WHERE executionId IN ({placeholders}) OR pastExecutionId IN ({placeholders}) OR evaluationExecutionId IN ({placeholders})",
                execution_ids * 3,
            )
            cur.execute(f"DELETE FROM chat_hub_messages WHERE executionId IN ({placeholders})", execution_ids)
            cur.execute(f"DELETE FROM execution_data WHERE executionId IN ({placeholders})", execution_ids)
            cur.execute(f"DELETE FROM execution_entity WHERE id IN ({placeholders})", execution_ids)
        conn.commit()

    execution_count_after = cur.execute(
        "SELECT COUNT(*) FROM execution_data WHERE data LIKE ? OR workflowData LIKE ?",
        (f"%{number}%", f"%{number}%"),
    ).fetchone()[0]
    static_row_after = cur.execute("SELECT staticData FROM workflow_entity WHERE id = ?", (workflow_id,)).fetchone()
    static_has_number_after = number in ((static_row_after["staticData"] or "") if static_row_after else "")
    conn.close()
    return {
        "workflowId": workflow_id,
        "staticHasNumberBefore": static_has_number_before,
        "executionIdsMatched": len(execution_ids),
        "staticHasNumberAfter": static_has_number_after,
        "executionCountAfter": execution_count_after,
    }


def cleanup_n8n_via_docker(project_dir: Path, number: str, workflow_id: str, dry_run: bool):
    cmd = [
        "docker", "run", "--rm",
        "-v", "ai_n8n_data:/data",
        "-v", f"{project_dir}:/work",
        "python:3.11-slim",
        "python", "/work/reset-lead-state.py",
        "cleanup-n8n",
        "--number", number,
        "--workflow-id", workflow_id,
    ]
    if dry_run:
        cmd.append("--dry-run")
    result = run(cmd, capture=True)
    stdout = (result.stdout or "").strip().splitlines()
    payload = json.loads(stdout[-1]) if stdout else {}
    return payload


def verify_n8n_via_docker(project_dir: Path, number: str, workflow_id: str):
    cmd = [
        "docker", "run", "--rm",
        "-v", "ai_n8n_data:/data",
        "-v", f"{project_dir}:/work",
        "python:3.11-slim",
        "python", "/work/reset-lead-state.py",
        "verify-n8n",
        "--number", number,
        "--workflow-id", workflow_id,
    ]
    result = run(cmd, capture=True)
    stdout = (result.stdout or "").strip().splitlines()
    payload = json.loads(stdout[-1]) if stdout else {}
    return payload


def evolution_count_sql(jid: str, number: str) -> str:
    return f"""
SELECT 'Contact' AS table_name, COUNT(*) AS total FROM "Contact" WHERE "remoteJid" = '{jid}'
UNION ALL
SELECT 'Chat', COUNT(*) FROM "Chat" WHERE "remoteJid" = '{jid}'
UNION ALL
SELECT 'IsOnWhatsapp', COUNT(*) FROM "IsOnWhatsapp" WHERE "remoteJid" = '{jid}'
UNION ALL
SELECT 'MessageUpdate', COUNT(*) FROM "MessageUpdate" WHERE COALESCE(CAST("remoteJid" AS text),'') LIKE '%{jid}%' OR COALESCE(CAST(participant AS text),'') LIKE '%{number}%'
UNION ALL
SELECT 'Message', COUNT(*) FROM "Message" WHERE CAST(key AS text) LIKE '%{jid}%' OR COALESCE(CAST(participant AS text),'') LIKE '%{number}%';
""".strip()


def evolution_cleanup_sql(jid: str, number: str) -> str:
    return f"""
DELETE FROM "MessageUpdate"
WHERE COALESCE(CAST("remoteJid" AS text),'') LIKE '%{jid}%'
   OR COALESCE(CAST(participant AS text),'') LIKE '%{number}%';

DELETE FROM "Message"
WHERE CAST(key AS text) LIKE '%{jid}%'
   OR COALESCE(CAST(participant AS text),'') LIKE '%{number}%';

DELETE FROM "IsOnWhatsapp"
WHERE "remoteJid" = '{jid}';

DELETE FROM "Chat"
WHERE "remoteJid" = '{jid}';

DELETE FROM "Contact"
WHERE "remoteJid" = '{jid}';
""".strip()


def run_psql_sql(sql: str):
    cmd = ["docker", "exec", "-i", "evolution-postgres", "psql", "-U", "evolution", "-d", "evolution"]
    return subprocess.run(cmd, input=sql, text=True, check=True, capture_output=True)


def parse_count_output(output: str):
    counts = {}
    for line in (output or "").splitlines():
        line = line.strip()
        if not line or line.startswith("(") or line.startswith("table_name") or line.startswith("-"):
            continue
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 2:
            continue
        name, value = parts
        if value.isdigit():
            counts[name] = int(value)
    return counts


def evolution_counts(number: str):
    jid = f"{number}@s.whatsapp.net"
    result = run_psql_sql(evolution_count_sql(jid, number))
    return parse_count_output(result.stdout)


def evolution_cleanup(number: str, dry_run: bool):
    before = evolution_counts(number)
    if not dry_run:
        run_psql_sql(evolution_cleanup_sql(f"{number}@s.whatsapp.net", number))
    after = evolution_counts(number)
    return {"before": before, "after": after}


def restart_services():
    run(["docker", "restart", "n8n", "evolution"])


def verify_local(db_path: Path, number: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    matches = {}
    for table in tables:
        info = cur.execute(f'PRAGMA table_info("{table}")').fetchall()
        text_cols = [r[1] for r in info if ((r[2] or "").upper() in ("TEXT", "") or "CHAR" in (r[2] or "").upper() or "CLOB" in (r[2] or "").upper())]
        if not text_cols:
            continue
        where = " OR ".join([f'CAST("{col}" AS TEXT) LIKE ?' for col in text_cols])
        count = cur.execute(f'SELECT COUNT(*) FROM "{table}" WHERE {where}', [f"%{number}%"] * len(text_cols)).fetchone()[0]
        if count:
            matches[table] = count
    conn.close()
    return matches


def main_reset(args):
    number = normalize_number(args.number)
    project_dir = Path(args.project_dir)
    runtime_root = Path(args.runtime_root)
    backup_dir = runtime_root / "dados" / "backups"
    ensure_dir(backup_dir)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    result = {
        "number": number,
        "dryRun": bool(args.dry_run),
        "backups": {},
    }

    if not args.skip_backup:
        result["backups"]["router"] = backup_file(runtime_root / "dados" / "router_runtime.sqlite", backup_dir, "router_runtime", ts)
        result["backups"]["crm"] = backup_file(project_dir / "crm_operacional.sqlite", backup_dir, "crm_operacional", ts)
        result["backups"]["n8n"] = backup_n8n_db(project_dir, backup_dir, ts)
        try:
            result["backups"]["evolution"] = backup_evolution_db(backup_dir, ts)
        except Exception as exc:
            result["backups"]["evolutionError"] = str(exc)

    result["crm"] = cleanup_sqlite_number(
        project_dir / "crm_operacional.sqlite",
        {"interactions": "number", "leads": "number", "learning_backlog": "number"},
        number,
        args.dry_run,
    )
    result["router"] = cleanup_sqlite_number(
        runtime_root / "dados" / "router_runtime.sqlite",
        {"route_logs": "number"},
        number,
        args.dry_run,
    )
    result["n8n"] = cleanup_n8n_via_docker(project_dir, number, args.workflow_id, args.dry_run)
    result["evolution"] = evolution_cleanup(number, args.dry_run)

    if not args.dry_run and not args.skip_restart:
        restart_services()

    result["verify"] = {
        "crm": verify_local(project_dir / "crm_operacional.sqlite", number),
        "router": verify_local(runtime_root / "dados" / "router_runtime.sqlite", number),
        "n8n": verify_n8n_via_docker(project_dir, number, args.workflow_id),
        "evolution": evolution_counts(number),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    sub_cleanup_n8n = sub.add_parser("cleanup-n8n")
    sub_cleanup_n8n.add_argument("--number", required=True)
    sub_cleanup_n8n.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    sub_cleanup_n8n.add_argument("--dry-run", action="store_true")

    sub_verify_n8n = sub.add_parser("verify-n8n")
    sub_verify_n8n.add_argument("--number", required=True)
    sub_verify_n8n.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)

    parser.add_argument("--number")
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR))
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-backup", action="store_true")
    parser.add_argument("--skip-restart", action="store_true")

    args = parser.parse_args()

    if args.command == "cleanup-n8n":
        payload = cleanup_n8n_internal(normalize_number(args.number), args.workflow_id, dry_run=args.dry_run)
        print(json.dumps(payload, ensure_ascii=False))
        return

    if args.command == "verify-n8n":
        payload = cleanup_n8n_internal(normalize_number(args.number), args.workflow_id, dry_run=True)
        print(json.dumps(payload, ensure_ascii=False))
        return

    if not args.number:
        parser.error("--number is required")

    main_reset(args)


if __name__ == "__main__":
    main()
