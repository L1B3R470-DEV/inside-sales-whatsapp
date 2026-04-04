#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
COORD = REPO / "coordination"
OUTBOX_CODEX = COORD / "outbox_codex_local"
OUTBOX_CLAUDE = COORD / "outbox_claude"
INBOX_CODEX = COORD / "inbox_codex_local"
INBOX_CLAUDE = COORD / "inbox_claude"
ARCHIVE_CODEX = COORD / "_archive" / "inbox_codex_local"
LOG_FILE = REPO / "orq-supervisor.log"
STATE_FILE = REPO / "orq-supervisor-state.json"
STATE_MD = REPO / "STATE.md"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def now_compact():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def log(message: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def git(args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed_reply_ids": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def active_local_peer():
    try:
        result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        self_dns = data.get("Self", {}).get("DNSName", "").rstrip(".")
        for peer in data.get("Peer", {}).values():
            if peer.get("Online") and peer.get("Active") and peer.get("DNSName", "").rstrip(".") != self_dns:
                return peer.get("DNSName", "").rstrip(".")
    except Exception:
        return None
    return None


def tailscale_ping(peer: str):
    if not peer:
        return
    try:
        result = subprocess.run(["tailscale", "ping", "-c", "1", peer], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            log(f"Tailscale ping ok para peer local: {peer}")
        else:
            log(f"Tailscale ping falhou para peer local: {peer} | {result.stdout} {result.stderr}".strip())
    except Exception as exc:
        log(f"Tailscale ping falhou com excecao: {exc}")


def find_latest_complete_020a_reply():
    candidates = []
    for path in OUTBOX_CODEX.glob("reply-020A*.json"):
        try:
            data = load_json(path)
        except Exception:
            continue
        if data.get("status") != "complete":
            continue
        cycle = str(data.get("cycle", ""))
        if cycle != "020A":
            continue
        candidates.append((path.stat().st_mtime, path, data))
    if not candidates:
        return None, None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1], candidates[0][2]


def reply_contains_valid_020a(data: dict) -> bool:
    if data.get("status") != "complete":
        return False
    report = data.get("report")
    if isinstance(report, dict):
        return report.get("conclusao", {}).get("pronto_para_revisao") is True
    output = data.get("output", "")
    return isinstance(output, str) and "PRIORIDADE_CONDICIONAL_DEFINIDA" in output and "pronto_para_revisao" in output.lower()


def task_or_reply_exists(prefix: str, folder: Path) -> bool:
    return any(p.name.startswith(prefix) for p in folder.glob("*.json"))


def update_state_md_for_020b(task_name: str):
    text = STATE_MD.read_text(encoding="utf-8")
    replacements = {
        "| Fase em andamento | 020A retry emitido — aguardando payload do CODEX LOCAL com poller local corrigido |":
            "| Fase em andamento | 020A concluido — 020B pendente de revisao do Claude Local |",
        "| Próxima etapa | CODEX LOCAL reprocesa o 020A usando o caminho corrigido do Invoke-ClaudeCLI |":
            "| Próxima etapa | Claude Local revisa o payload do 020A e decide homologacao do 020B |",
        "| Status inbox_claude | vazio (diagnosticos arquivados; replies processados) |":
            f"| Status inbox_claude | {task_name} pendente |",
        "| Status inbox_codex_local | task-020A-RETRY pendente |":
            "| Status inbox_codex_local | vazio (020A concluido; aguardando revisao 020B) |",
        "| Acao em curso | CODEX LOCAL recebe retry limpo do 020A, com prompt sem pipes e poller local corrigido |":
            "| Acao em curso | Claude Local revisa o payload do 020A para confirmar ou corrigir a priorizacao condicional de R5 |",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if "## Resultado consolidado do ciclo 20" not in text:
        insert = """

## Resultado consolidado do ciclo 20

| Microfase | Veredito | Observacao |
|---|---|---|
| 20A | PRODUZIDO | PRIORIZAR_CONDICAO / selected_focus = R5 |
| 20B | PENDENTE | revisao do Claude Local ainda nao executada |
"""
        text += insert
    STATE_MD.write_text(text, encoding="utf-8")


def create_020b_task(reply_path: Path):
    ts = now_compact()
    task_name = f"task-020B-{ts}.json"
    reply_name = f"reply-020B-{ts}.json"
    task = {
        "task_id": f"task-020B-{ts}",
        "target_actor": "claude_local",
        "cycle": "020B",
        "instruction": (
            "Voce deve revisar o payload do ciclo 020A e decidir se a priorizacao condicional de R5 esta formalmente homologavel. "
            "Objetivo: confirmar se PRIORIZAR_CONDICAO / selected_focus=R5 / readiness_classification=PRIORIDADE_CONDICIONAL_DEFINIDA "
            "esta suficientemente ancorado nas fontes do ciclo 19, sem analise de conteudo de item, sem reabrir R2 ou R6 e sem autorizacao implicita. "
            "Verifique especificamente: 1. se R5 e tecnicamente a condicao priorizavel mais defensavel entre R1/R3/R4/R5; 2. se R3 e R4 permaneceram com divergencia explicita sem suavizacao; "
            "3. se R1 permaneceu enfraquecido pela inversao priority_cycle3=1 vs execution_order_cycle4=6; 4. se next_cycle_contract_basis de R5 esta preciso e nao autorizante; "
            "5. se o payload 020A e formalmente homologavel. Nao modificar nada. Nao tocar em producao, bridge, .mcp.json, projeto real, R2, R6. "
            "Formato obrigatorio da resposta: INICIO DO RELATORIO / VEREDITO / EVIDENCIAS OBRIGATORIAS RECEBIDAS / CLASSIFICACAO DO RESULTADO / AVALIACAO DA PRIORIZACAO CONDICIONAL / DECISAO SOBRE A PROGRESSAO / CRITERIO OBJETIVO QUE DECIDIU O CASO / O QUE NAO DEVE MUDAR / RESUMO EXECUTIVO / FIM DO RELATORIO. "
            "Classificacao esperada: success/partial/failed/blocked. A decisao sobre a progressao deve responder se 020B pode ser homologado e se o ciclo 21 pode ser discutido. "
            "Se houver falha material na ancoragem documental, nao homologue automaticamente."
        ),
        "context_files": [
            "STATE.md",
            "cycle20-input/cycle-020A-conditional-queue-prioritization.json",
            str(reply_path.relative_to(REPO)).replace("\\", "/"),
            "cycle19-input/cycle-019A-post-r2-closure-queue-assessment.json",
            "cycle19-input/queue_source_map.json"
        ],
        "output_path": f"coordination/outbox_claude/{reply_name}",
        "red_lines": [
            "no_production_write",
            "no_bridge_write",
            "no_mcp_json_write",
            "no_r2_reopen",
            "no_r6_reopen"
        ],
        "status": "pending",
        "created_at": now_iso()
    }
    path = INBOX_CLAUDE / task_name
    save_json(path, task)
    return path


def archive_old_020a_task():
    ARCHIVE_CODEX.mkdir(parents=True, exist_ok=True)
    for candidate in INBOX_CODEX.glob("task-020A*.json"):
        if "RETRY" in candidate.name or candidate.name.startswith("task-020A-"):
            target = ARCHIVE_CODEX / candidate.name
            if candidate.exists():
                candidate.replace(target)


def commit_push(files, message):
    git(["add", *[str(p.relative_to(REPO)) for p in files]])
    diff = git(["diff", "--cached", "--name-only"])
    if diff.returncode != 0 or not diff.stdout.strip():
        return False
    commit = git(["commit", "-m", message])
    if commit.returncode != 0:
        log(f"Falha no commit: {commit.stdout} {commit.stderr}".strip())
        return False
    push = git(["push", "origin", "master"])
    if push.returncode != 0:
        log(f"Falha no push: {push.stdout} {push.stderr}".strip())
        return False
    log(f"Commit/push concluido: {message}")
    return True


def process_once():
    state = load_state()
    peer = active_local_peer()
    if peer:
        tailscale_ping(peer)

    reply_path, reply_data = find_latest_complete_020a_reply()
    if not reply_path or not reply_contains_valid_020a(reply_data):
        return False

    reply_id = reply_data.get("reply_id") or reply_path.stem
    if reply_id in state["processed_reply_ids"]:
        return False

    if task_or_reply_exists("task-020B-", INBOX_CLAUDE) or task_or_reply_exists("reply-020B-", OUTBOX_CLAUDE):
        state["processed_reply_ids"].append(reply_id)
        save_state(state)
        return False

    created_task = create_020b_task(reply_path)
    reply_data["status"] = "processed"
    save_json(reply_path, reply_data)
    archive_old_020a_task()
    update_state_md_for_020b(created_task.name)
    save_state({"processed_reply_ids": state["processed_reply_ids"] + [reply_id]})
    commit_push([created_task, reply_path, STATE_MD, STATE_FILE, *(ARCHIVE_CODEX.glob("task-020A*.json"))], "orq: instrucao 020B para claude")
    log(f"020A processado pelo supervisor. Task 020B emitida: {created_task.name}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.once:
        process_once()
        return

    log("=== orq-supervisor iniciado ===")
    while True:
        try:
            process_once()
        except Exception as exc:
            log(f"ERRO no supervisor: {exc}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
