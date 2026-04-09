import argparse
import json
import sqlite3
from pathlib import Path


DEFAULT_WORKFLOW_ID = "zN3heKJVLO8w4dG6"
TARGET_NODE_NAME = "Guardrails"
TARGET_NODE_TYPE = "n8n-nodes-base.code"
EXPECTED_MARKERS = [
    "isShortAcknowledgement",
    "vitrineConsentDismissedAt",
    "b2bConsentDismissedAt",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Patch the Guardrails node in an n8n workflow using guardrails.js from the repo."
    )
    parser.add_argument(
        "--db-path",
        default="/data/database.sqlite",
        help="Path to the n8n SQLite database.",
    )
    parser.add_argument(
        "--workflow-id",
        default=DEFAULT_WORKFLOW_ID,
        help="Workflow id to patch.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent),
        help="Repository root that contains guardrails.js.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report changes without writing to the database.",
    )
    return parser.parse_args()


def load_guardrails_code(repo_root: Path) -> str:
    guardrails_path = repo_root / "guardrails.js"
    if not guardrails_path.exists():
        raise FileNotFoundError(f"guardrails.js not found at {guardrails_path}")
    return guardrails_path.read_text(encoding="utf-8")


def patch_nodes_json(nodes_text: str, new_code: str):
    nodes = json.loads(nodes_text)
    matches = [
        node
        for node in nodes
        if node.get("name") == TARGET_NODE_NAME and node.get("type") == TARGET_NODE_TYPE
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly 1 {TARGET_NODE_NAME} node of type {TARGET_NODE_TYPE}, found {len(matches)}"
        )

    changed = False
    node = matches[0]
    params = node.setdefault("parameters", {})
    if params.get("language") != "javaScript":
        params["language"] = "javaScript"
        changed = True
    if params.get("jsCode") != new_code:
        params["jsCode"] = new_code
        changed = True

    if not changed:
        return None, node

    return json.dumps(nodes, ensure_ascii=False, separators=(",", ":")), node


def table_exists(cur, table_name: str) -> bool:
    cur.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    )
    return cur.fetchone()[0] == 1


def fetch_workflow_entity(cur, workflow_id: str):
    cur.execute("SELECT id, nodes FROM workflow_entity WHERE id = ?", (workflow_id,))
    return cur.fetchone()


def fetch_history_rows(cur, workflow_id: str):
    if not table_exists(cur, "workflow_history"):
        return []
    cur.execute(
        "SELECT versionId, nodes FROM workflow_history WHERE workflowId = ?",
        (workflow_id,),
    )
    return cur.fetchall()


def marker_report(code: str):
    return {marker: (marker in code) for marker in EXPECTED_MARKERS}


def main():
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    db_path = Path(args.db_path).resolve()
    new_code = load_guardrails_code(repo_root)

    if not db_path.exists():
        raise FileNotFoundError(f"database not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    entity_row = fetch_workflow_entity(cur, args.workflow_id)
    if not entity_row:
        raise RuntimeError(
            f"workflow {args.workflow_id} not found in workflow_entity at {db_path}"
        )

    entity_id, entity_nodes = entity_row
    patched_entity_nodes, entity_node = patch_nodes_json(entity_nodes, new_code)
    history_rows = fetch_history_rows(cur, args.workflow_id)

    history_changes = []
    for version_id, nodes_text in history_rows:
        patched_nodes, _ = patch_nodes_json(nodes_text, new_code)
        if patched_nodes is not None:
            history_changes.append((version_id, patched_nodes))

    current_code = entity_node.get("parameters", {}).get("jsCode", "")
    result = {
        "db_path": str(db_path),
        "workflow_id": entity_id,
        "repo_root": str(repo_root),
        "dry_run": args.dry_run,
        "entity_would_change": patched_entity_nodes is not None,
        "history_rows_total": len(history_rows),
        "history_rows_would_change": len(history_changes),
        "markers_in_repo_guardrails": marker_report(new_code),
        "markers_in_current_workflow": marker_report(current_code),
    }

    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        conn.close()
        return

    entity_changes = 0
    if patched_entity_nodes is not None:
        cur.execute(
            "UPDATE workflow_entity SET nodes = ?, updatedAt = STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW') WHERE id = ?",
            (patched_entity_nodes, args.workflow_id),
        )
        entity_changes = cur.rowcount

    history_count = 0
    for version_id, patched_nodes in history_changes:
        cur.execute(
            "UPDATE workflow_history SET nodes = ?, updatedAt = STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW') WHERE versionId = ?",
            (patched_nodes, version_id),
        )
        history_count += cur.rowcount

    conn.commit()
    cur.execute("SELECT nodes FROM workflow_entity WHERE id = ?", (args.workflow_id,))
    applied_nodes = json.loads(cur.fetchone()[0])
    applied_node = next(
        node
        for node in applied_nodes
        if node.get("name") == TARGET_NODE_NAME and node.get("type") == TARGET_NODE_TYPE
    )
    applied_code = applied_node.get("parameters", {}).get("jsCode", "")

    result.update(
        {
            "entity_changes": entity_changes,
            "history_changes": history_count,
            "markers_after_apply": marker_report(applied_code),
        }
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == "__main__":
    main()
