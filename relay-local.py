#!/usr/bin/env python3
"""
relay-local.py
Roda na MÁQUINA LOCAL (Account A).
Monitora inbox_claude/ no workspace-integration via git e processa cada task
usando o Claude Code CLI LOCAL (autenticado nesta máquina).
Escreve respostas em outbox_claude/ e faz commit+push.

Uso:
  python relay-local.py
  python relay-local.py --interval 60 --claude-path claude
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

DEFAULT_REPO_DIR  = Path.home() / ".openclaw" / "workspace-integration"
REMOTE_BRANCH     = "master"
COORD             = "coordination"
INBOX_CLAUDE      = "inbox_claude"
OUTBOX_CLAUDE     = "outbox_claude"
PROCESSED_FILE    = "processed_tasks_local.txt"
LOG_FILE          = "relay-local.log"

# ─── LOGGING ─────────────────────────────────────────────────────────────────

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

log = logging.getLogger(__name__)

# ─── GIT ─────────────────────────────────────────────────────────────────────

def git(args: list, cwd: Path) -> tuple[int, str]:
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

# ─── PROCESSAMENTO ───────────────────────────────────────────────────────────

def load_processed(path: Path) -> set:
    if path.exists():
        return set(path.read_text(encoding="utf-8").splitlines())
    return set()

def mark_processed(path: Path, task_id: str):
    with open(path, "a", encoding="utf-8") as f:
        f.write(task_id + "\n")

def build_prompt(task: dict, repo: Path) -> str:
    instruction = task.get("instruction", "")
    context_files = task.get("context_files", [])
    cycle = task.get("cycle", "?")
    task_id = task.get("task_id", "?")
    output_path = task.get("output_path", "")
    red_lines = task.get("red_lines", [])

    ctx_content = ""
    for cf in context_files:
        p = repo / cf
        if p.exists():
            ctx_content += f"\n\n--- {cf} ---\n{p.read_text(encoding='utf-8-sig', errors='replace')}"
        else:
            ctx_content += f"\n\n--- {cf} --- (arquivo não encontrado)"

    return f"""OPENLAW — TASK PARA CLAUDE LOCAL
================================
task_id:    {task_id}
ciclo:      {cycle}
output_path: {output_path}
red_lines:  {', '.join(red_lines)}

INSTRUÇÃO:
{instruction}

ARQUIVOS DE CONTEXTO:{ctx_content}

---
IMPORTANTE:
- Produza um reply JSON válido conforme o schema do PROTOCOL.md
- Escreva o arquivo de saída em: {repo / output_path}
- status deve ser "complete" se concluído, "BLOCKED" se violar red_lines
- NÃO modifique nada fora de workspace-integration/
- NÃO toque em produção, bridge local, .mcp.json ou bancos reais
""".strip()

def invoke_claude(prompt: str, repo: Path, claude_path: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [claude_path, "-p", prompt],
            capture_output=True, text=True, timeout=600,
            cwd=str(repo)
        )
        if result.returncode == 0:
            log.info("Claude CLI concluiu com sucesso.")
            return True, result.stdout.strip()
        else:
            log.warning(f"Claude CLI erro (code {result.returncode}): {result.stderr[:300]}")
            return False, f"ERRO: {result.stderr[:300]}"
    except FileNotFoundError:
        log.error("Claude CLI não encontrado. Verifique instalação e PATH.")
        return False, "BLOCKED: claude CLI não encontrado"
    except subprocess.TimeoutExpired:
        log.error("Claude CLI timeout (>10min).")
        return False, "BLOCKED: timeout"
    except Exception as e:
        log.error(f"Erro ao acionar Claude CLI: {e}")
        return False, f"ERRO: {e}"

def process_task(task_file: Path, repo: Path, processed: set, claude_path: str):
    try:
        task = json.loads(task_file.read_text(encoding="utf-8-sig"))
    except Exception as e:
        log.error(f"Erro ao ler {task_file.name}: {e}")
        return

    task_id = task.get("task_id", "")
    status  = task.get("status", "")
    cycle   = task.get("cycle", "?")
    output_path = task.get("output_path", "")

    if not task_id or status not in ("pending", "accepted"):
        return
    if task_id in processed:
        return
    if not output_path:
        log.error(f"Task {task_id} sem output_path — ignorada.")
        return

    log.info(f"Processando task: {task_id} | ciclo={cycle}")

    # Marcar como accepted no git
    task["status"] = "accepted"
    task_file.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding="utf-8")
    git_commit_push(repo, f"relay-local: accepted {task_id}", [task_file])

    # Construir prompt e chamar Claude local
    prompt = build_prompt(task, repo)
    success, output = invoke_claude(prompt, repo, claude_path)

    # Construir reply
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    reply_id = f"reply-{cycle}-{ts}"
    reply = {
        "reply_id": reply_id,
        "source_task_id": task_id,
        "actor": "claude_local",
        "cycle": cycle,
        "output": output if success else "",
        "status": "complete" if success else "processed_error",
        "produced_at": datetime.now(timezone.utc).isoformat(),
    }
    if not success:
        reply["error"] = output

    # Escrever reply no output_path definido pela task
    out_file = repo / output_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(reply, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Reply escrito: {out_file}")

    # Commit e push
    git_commit_push(repo, f"relay-local: reply {reply_id} (ciclo {cycle})", [out_file])
    mark_processed(repo / PROCESSED_FILE, task_id)
    processed.add(task_id)
    log.info(f"Task {task_id} concluída.")

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Relay Local — OpenClaw Claude Local")
    parser.add_argument("--interval",    type=int, default=60,        help="Intervalo de polling em segundos (default: 60)")
    parser.add_argument("--repo-dir",    type=str, default=str(DEFAULT_REPO_DIR), help="Caminho do workspace-integration local")
    parser.add_argument("--claude-path", type=str, default="claude",  help="Caminho do claude CLI (default: claude)")
    args = parser.parse_args()

    repo = Path(args.repo_dir)
    if not repo.exists():
        print(f"ERRO: repo-dir não encontrado: {repo}")
        sys.exit(1)

    setup_logging(repo / LOG_FILE)

    log.info("=" * 60)
    log.info("relay-local iniciado (Claude LOCAL como executor)")
    log.info(f"Repo:      {repo}")
    log.info(f"Intervalo: {args.interval}s")
    log.info(f"Claude:    {args.claude_path}")
    log.info("=" * 60)

    processed = load_processed(repo / PROCESSED_FILE)
    inbox = repo / COORD / INBOX_CLAUDE

    while True:
        try:
            git_pull(repo)

            if inbox.exists():
                for f in sorted(inbox.glob("*.json")):
                    process_task(f, repo, processed, args.claude_path)

        except KeyboardInterrupt:
            log.info("Encerrado pelo usuário.")
            break
        except Exception as e:
            log.error(f"Erro inesperado: {e}", exc_info=True)

        time.sleep(args.interval)

    log.info("=== relay-local encerrado ===")

if __name__ == "__main__":
    main()
