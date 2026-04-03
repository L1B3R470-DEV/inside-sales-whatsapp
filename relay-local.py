#!/usr/bin/env python3
"""
relay-local.py
Roda na MAQUINA LOCAL (Account A).

Funcao: ponte entre workspace-integration e a sessao interativa Claude Local.

Fluxo:
  1. Detecta tasks em coordination/inbox_claude/
  2. Escreve cada task no bridge OPENLAW (C:\\AUTOMACAO\\cowork\\claude_bridge\\inbox_for_claude\\)
  3. Claude Local (sessao interativa) processa via trigger OPENLAW e escreve
     o reply em coordination/outbox_claude/ diretamente.
  4. Relay detecta o reply em outbox_claude/ e faz commit+push para o git.

Nao chama claude -p. Nao bloqueia. Opera como relay puro.

Uso:
  python relay-local.py
  python relay-local.py --interval 30
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REPO_DIR = Path.home() / ".openclaw" / "workspace-integration"
REMOTE_BRANCH    = "master"
COORD            = "coordination"
INBOX_CLAUDE     = "inbox_claude"
OUTBOX_CLAUDE    = "outbox_claude"
PROCESSED_FILE   = "processed_tasks_local.txt"
PUSHED_FILE      = "pushed_replies_local.txt"
LOG_FILE         = "relay-local.log"

BRIDGE_INBOX  = Path(r"C:\AUTOMACAO\cowork\claude_bridge\inbox_for_claude")

log = logging.getLogger(__name__)


def setup_logging(log_path: Path):
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def git(args: list, cwd: Path) -> tuple:
    result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def git_pull(repo: Path):
    code, out = git(["pull", "origin", REMOTE_BRANCH], repo)
    if code != 0:
        log.warning(f"git pull falhou: {out}")


def git_commit_push(repo: Path, message: str, files: list):
    for f in files:
        git(["add", str(f)], repo)
    code, out = git(["diff", "--cached", "--name-only"], repo)
    if not out.strip():
        return
    git(["commit", "-m", message], repo)
    code, out = git(["push", "origin", REMOTE_BRANCH], repo)
    if code != 0:
        log.error(f"git push falhou: {out}")
    else:
        log.info(f"Push OK: {message}")


def load_set(path: Path) -> set:
    if path.exists():
        return set(path.read_text(encoding="utf-8").splitlines())
    return set()


def append_set(path: Path, value: str):
    with open(path, "a", encoding="utf-8") as f:
        f.write(value + "\n")


def forward_to_bridge(task: dict, repo: Path):
    """Escreve a task no bridge OPENLAW para a sessao interativa processar."""
    task_id  = task.get("task_id", "")
    cycle    = task.get("cycle", "?")
    ts       = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bridge_id = f"TASK-WS-{cycle}-{ts}"

    bridge_task = {
        "task_id":      bridge_id,
        "ws_task_id":   task_id,
        "title":        f"[OpenClaw ciclo {cycle}] {task_id}",
        "from":         "relay-local",
        "to":           "claude",
        "body":         task.get("instruction", ""),
        "context_files": task.get("context_files", []),
        "output_path":  task.get("output_path", ""),
        "red_lines":    task.get("red_lines", []),
        "ws_repo":      str(repo),
        "required_output": (
            "JSON com campos: reply_id, source_task_id, actor=claude_local, "
            f"cycle={cycle}, status=complete|BLOCKED, output (relatorio completo), "
            f"produced_at. Escrever em: {repo / task.get('output_path','')}"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if BRIDGE_INBOX.exists():
        out = BRIDGE_INBOX / f"{bridge_id}.json"
        out.write_text(json.dumps(bridge_task, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info(f"Task encaminhada ao bridge OPENLAW: {bridge_id} (ws={task_id})")
    else:
        log.warning(f"Bridge OPENLAW nao encontrado em {BRIDGE_INBOX} — task {task_id} nao encaminhada.")


def check_new_replies(repo: Path, pushed: set):
    """Detecta novos replies em outbox_claude/ e faz commit+push."""
    outbox = repo / COORD / OUTBOX_CLAUDE
    if not outbox.exists():
        return
    for f in sorted(outbox.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        reply_id = d.get("reply_id", f.stem)
        if reply_id in pushed:
            continue
        if d.get("status") not in ("complete", "BLOCKED"):
            continue
        log.info(f"Novo reply detectado para push: {reply_id} | status={d.get('status')}")
        git_commit_push(repo, f"relay-local: push reply {reply_id}", [f])
        append_set(repo / PUSHED_FILE, reply_id)
        pushed.add(reply_id)


def main():
    parser = argparse.ArgumentParser(description="Relay Local — OpenClaw Claude Local")
    parser.add_argument("--interval", type=int, default=30,
                        help="Intervalo de polling em segundos (default: 30)")
    parser.add_argument("--repo-dir", type=str, default=str(DEFAULT_REPO_DIR),
                        help="Caminho do workspace-integration local")
    args = parser.parse_args()

    repo = Path(args.repo_dir)
    if not repo.exists():
        print(f"ERRO: repo-dir nao encontrado: {repo}")
        sys.exit(1)

    setup_logging(repo / LOG_FILE)

    log.info("=" * 60)
    log.info("relay-local iniciado (modo bridge — sem claude -p)")
    log.info(f"Repo:      {repo}")
    log.info(f"Intervalo: {args.interval}s")
    log.info(f"Bridge:    {BRIDGE_INBOX}")
    log.info("=" * 60)

    processed = load_set(repo / PROCESSED_FILE)
    pushed    = load_set(repo / PUSHED_FILE)
    inbox     = repo / COORD / INBOX_CLAUDE

    while True:
        try:
            git_pull(repo)

            # 1. Encaminhar tasks novas ao bridge OPENLAW
            if inbox.exists():
                for f in sorted(inbox.glob("*.json")):
                    try:
                        task = json.loads(f.read_text(encoding="utf-8-sig"))
                    except Exception as e:
                        log.error(f"Erro ao ler {f.name}: {e}")
                        continue
                    task_id = task.get("task_id", "")
                    status  = task.get("status", "")
                    if not task_id or task_id in processed:
                        continue
                    if status not in ("pending", "accepted"):
                        continue
                    forward_to_bridge(task, repo)
                    append_set(repo / PROCESSED_FILE, task_id)
                    processed.add(task_id)

            # 2. Push de novos replies ja escritos pelo Claude Local
            check_new_replies(repo, pushed)

        except KeyboardInterrupt:
            log.info("Encerrado pelo usuario.")
            break
        except Exception as e:
            log.error(f"Erro inesperado: {e}", exc_info=True)

        time.sleep(args.interval)

    log.info("=== relay-local encerrado ===")


if __name__ == "__main__":
    main()
