#!/usr/bin/env python3
"""
poller-codex-remoto.py
Roda na máquina remota (Account B / CODEX REMOTO).
Monitora o branch master por novos outputs de Claude e CODEX LOCAL.

MODO RELAY (padrão e recomendado):
  O poller NÃO chama claude -p localmente. Apenas detecta replies em
  outbox_claude/ e outbox_codex_local/, registra como seen e aguarda
  o CLAUDE LOCAL (relay-local.py na máquina local) processar via git.

  Use --relay=false APENAS se claude CLI estiver autenticado localmente
  e você quiser execução autônoma na máquina remota.

Uso:
  python poller-codex-remoto.py
  python poller-codex-remoto.py --interval 30 --repo-dir /caminho/do/repo --relay true

Instalar como tarefa (Windows): Task Scheduler apontando para este script
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

DEFAULT_REPO_DIR   = Path.home() / "workspace-integration"
REMOTE_BRANCH      = "master"
COORDINATION_DIR   = "coordination"
OUTBOX_CLAUDE      = "outbox_claude"
OUTBOX_CODEX_LOCAL = "outbox_codex_local"
INBOX_CLAUDE       = "inbox_claude"
INBOX_CODEX_LOCAL  = "inbox_codex_local"
PROCESSED_FILE     = "processed_replies.txt"
LOG_FILE           = "poller-remoto.log"
PROMPT_FILE        = "current_output_for_analysis.txt"

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
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd, capture_output=True, text=True
    )
    return result.returncode, (result.stdout + result.stderr).strip()

def git_pull(repo: Path) -> bool:
    code, out = git(["pull", "origin", REMOTE_BRANCH], repo)
    if code != 0:
        log.warning(f"git pull falhou: {out}")
    return code == 0

def git_commit_push(repo: Path, message: str, files: list[Path]) -> bool:
    for f in files:
        git(["add", str(f)], repo)
    code, out = git(["diff", "--cached", "--name-only"], repo)
    if not out.strip():
        return False  # nada staged
    git(["commit", "-m", message], repo)
    code, out = git(["push", "origin", REMOTE_BRANCH], repo)
    if code != 0:
        log.error(f"git push falhou: {out}")
        return False
    return True

# ─── PROCESSAMENTO ───────────────────────────────────────────────────────────

def load_processed(processed_file: Path) -> set:
    if processed_file.exists():
        return set(processed_file.read_text(encoding="utf-8").splitlines())
    return set()

def mark_processed(processed_file: Path, reply_id: str):
    with open(processed_file, "a", encoding="utf-8") as f:
        f.write(reply_id + "\n")

def build_analysis_prompt(reply_data: dict, state_md: str, bootstrap_md: str) -> str:
    actor  = reply_data.get("actor", "desconhecido")
    cycle  = reply_data.get("cycle", "?")
    status = reply_data.get("status", "?")
    output = reply_data.get("output", "")

    return f"""
OPENLAW — OUTPUT RECEBIDO PARA ANÁLISE DO ORQUESTRADOR
=======================================================
Actor:  {actor}
Ciclo:  {cycle}
Status: {status}

OUTPUT COMPLETO:
{json.dumps(output, indent=2, ensure_ascii=False) if isinstance(output, dict) else str(output)}

---
CONTEXTO DO PROCESSO (STATE.md):
{state_md}

---
BOOTSTRAP DO ORQUESTRADOR (resumo):
{bootstrap_md[:2000]}...

---
INSTRUÇÃO PARA O ORQUESTRADOR:
1. Analise o output acima conforme o checklist do ciclo {cycle}.
2. Decida: HOMOLOGADO / REJEITADO / CONDICIONAL.
3. Produza o próximo task file para o ator correto.
4. Escreva o arquivo JSON em: coordination/inbox_claude/ OU coordination/inbox_codex_local/
5. Use o schema de PROTOCOL.md (campo task_id, target_actor, cycle, instruction, context_files, status, created_at).
6. Nunca escreva fora de workspace-integration/.
7. Nunca reabra R2 nem R6.
8. Se o status for BLOCKED: pare e sinalize Rodrigo.

Após escrever o arquivo JSON do próximo task, faça commit e push:
  git add coordination/
  git commit -m "orq: instrucao {cycle} para [ator]"
  git push origin master
""".strip()

def invoke_claude(prompt: str, prompt_file: Path, repo: Path, claude_path: str = "claude") -> tuple[bool, str]:
    """
    Aciona Claude Code CLI em modo não-interativo.
    Retorna (sucesso, output).
    """
    prompt_file.write_text(prompt, encoding="utf-8")
    log.info(f"Prompt salvo em: {prompt_file}")

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
            log.warning(f"Claude CLI retornou erro (code {result.returncode}): {result.stderr[:300]}")
            return False, f"ERRO: {result.stderr[:300]}"
    except FileNotFoundError:
        log.error("Claude CLI não encontrado no PATH. Instale: npm install -g @anthropic-ai/claude-code")
        return False, "BLOCKED: claude CLI não encontrado"
    except subprocess.TimeoutExpired:
        log.error("Claude CLI timeout (>10min).")
        return False, "BLOCKED: timeout"
    except Exception as e:
        log.error(f"Erro ao acionar Claude CLI: {e}")
        return False, f"ERRO: {e}"

def process_reply(
    reply_file: Path,
    repo: Path,
    processed: set,
    state_md: str,
    bootstrap_md: str,
    claude_path: str = "claude",
) -> bool:
    try:
        data = json.loads(reply_file.read_text(encoding="utf-8-sig"))
    except Exception as e:
        log.error(f"Falha ao ler {reply_file.name}: {e}")
        return False

    reply_id = data.get("reply_id", "")
    status   = data.get("status", "")
    cycle    = data.get("cycle", "?")

    if not reply_id or status not in ("complete", "BLOCKED"):
        return False
    if reply_id in processed:
        return False

    log.info(f"Novo reply detectado: {reply_id} | status={status} | ciclo={cycle}")

    if status == "BLOCKED":
        log.error(f"BLOCKED detectado em {reply_id} — ciclo {cycle} suspenso. Notificar Rodrigo.")
        # Não processar automaticamente — marcar como processed para não lopar
        data["status"] = "processed_blocked"
        reply_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8-sig")
        git_commit_push(repo, f"orq: BLOCKED {reply_id}", [reply_file])
        mark_processed(repo / PROCESSED_FILE, reply_id)
        processed.add(reply_id)
        return False

    # Construir prompt de análise + orquestração
    prompt_file = repo / PROMPT_FILE
    prompt = build_analysis_prompt(data, state_md, bootstrap_md)

    # Acionar Claude CLI como CODEX REMOTO
    success, claude_output = invoke_claude(prompt, prompt_file, repo, claude_path)

    if not success or "BLOCKED" in claude_output or "ERRO" in claude_output:
        log.error(f"Claude CLI falhou para {reply_id}: {claude_output[:200]}")
        data["status"] = "processed_error"
        data["error"] = claude_output[:500]
    else:
        log.info(f"Claude CLI produziu output para {reply_id} ({len(claude_output)} chars)")
        # Salvar output do orquestrador para referência
        output_log = repo / f"orq-output-{reply_id}.txt"
        output_log.write_text(claude_output, encoding="utf-8-sig")
        data["status"] = "processed"
    reply_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    git_commit_push(repo, f"orq: processado {reply_id}", [reply_file])
    mark_processed(repo / PROCESSED_FILE, reply_id)
    processed.add(reply_id)

    log.info(f"Reply {reply_id} processado.")
    return True

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Poller CODEX REMOTO — OpenClaw")
    parser.add_argument("--interval", type=int, default=60, help="Intervalo de polling em segundos (default: 60)")
    parser.add_argument("--repo-dir", type=str, default=str(DEFAULT_REPO_DIR), help="Caminho local do repositório clonado")
    parser.add_argument("--claude-path", type=str, default="claude", help="Caminho completo do claude CLI (default: claude)")
    parser.add_argument("--relay", type=str, default="true", help="Modo relay: não chama claude -p localmente (default: true). Use false para execução autônoma local.")
    args = parser.parse_args()

    repo = Path(args.repo_dir)
    if not repo.exists():
        print(f"ERRO: repo-dir não encontrado: {repo}")
        sys.exit(1)

    coord = repo / COORDINATION_DIR
    setup_logging(repo / LOG_FILE)

    log.info("=" * 60)
    log.info("poller-codex-remoto iniciado")
    log.info(f"Repo:     {repo}")
    log.info(f"Intervalo: {args.interval}s")
    log.info(f"Branch:   {REMOTE_BRANCH}")
    log.info("=" * 60)

    claude_path = args.claude_path
    relay_mode  = args.relay.lower() != "false"
    processed   = load_processed(repo / PROCESSED_FILE)

    if relay_mode:
        log.info("Modo RELAY ativo — respostas não serão processadas localmente.")
        log.info("Claude LOCAL (relay-local.py) é responsável por processar inbox_claude/.")

    while True:
        try:
            # Pull
            git_pull(repo)

            if relay_mode:
                # Em modo relay: apenas registra replies como "seen" (não processa)
                outbox_claude = coord / OUTBOX_CLAUDE
                if outbox_claude.exists():
                    for f in sorted(outbox_claude.glob("*.json")):
                        try:
                            data = json.loads(f.read_text(encoding="utf-8-sig"))
                            rid = data.get("reply_id", "")
                            if rid and rid not in processed and data.get("status") in ("complete",):
                                log.info(f"[RELAY] Reply detectado (aguardando Claude LOCAL): {rid}")
                                mark_processed(repo / PROCESSED_FILE, rid)
                                processed.add(rid)
                        except Exception:
                            pass
            else:
                # Modo autônomo local (requer claude autenticado nesta máquina)
                state_md = ""
                bootstrap_md = ""
                state_path     = repo / "STATE.md"
                bootstrap_path = repo / "BOOTSTRAP_REMOTE_v2.md"
                if state_path.exists():
                    state_md = state_path.read_text(encoding="utf-8-sig", errors="replace")
                if bootstrap_path.exists():
                    bootstrap_md = bootstrap_path.read_text(encoding="utf-8-sig", errors="replace")

                outbox_claude = coord / OUTBOX_CLAUDE
                if outbox_claude.exists():
                    for f in sorted(outbox_claude.glob("*.json")):
                        process_reply(f, repo, processed, state_md, bootstrap_md, claude_path)

                outbox_codex = coord / OUTBOX_CODEX_LOCAL
                if outbox_codex.exists():
                    for f in sorted(outbox_codex.glob("*.json")):
                        process_reply(f, repo, processed, state_md, bootstrap_md, claude_path)

        except KeyboardInterrupt:
            log.info("Encerrado pelo usuário.")
            break
        except Exception as e:
            log.error(f"Erro inesperado no loop principal: {e}", exc_info=True)

        time.sleep(args.interval)

    log.info("=== poller-codex-remoto encerrado ===")

if __name__ == "__main__":
    main()
