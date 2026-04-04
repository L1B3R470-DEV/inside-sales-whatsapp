#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
COORD = REPO / "coordination"
OUTBOX_CODEX = COORD / "outbox_codex_local"
OUTBOX_CLAUDE = COORD / "outbox_claude"
INBOX_CODEX = COORD / "inbox_codex_local"
INBOX_CLAUDE = COORD / "inbox_claude"
ARCHIVE_CODEX = COORD / "_archive" / "inbox_codex_local"
ARCHIVE_CLAUDE = COORD / "_archive" / "inbox_claude"
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


def git_pull_ff_only():
    status = git(["status", "--porcelain"])
    if status.returncode != 0:
        log(f"Falha ao verificar status do git: {status.stdout} {status.stderr}".strip())
        return
    if status.stdout.strip():
        log("Repositorio local com modificacoes pendentes; git pull automatico ignorado nesta passada.")
        return
    fetch = git(["fetch", "origin"])
    if fetch.returncode != 0:
        log(f"Falha no git fetch: {fetch.stdout} {fetch.stderr}".strip())
        return
    pull = git(["pull", "--ff-only", "origin", "master"])
    if pull.returncode != 0:
        log(f"Falha no git pull --ff-only: {pull.stdout} {pull.stderr}".strip())
        return
    output = (pull.stdout + pull.stderr).strip()
    if output and "Already up to date." not in output:
        log(f"Repositorio sincronizado automaticamente: {output}")


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


def normalize_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


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


def task_or_reply_exists(prefix: str, folder: Path) -> bool:
    return any(p.name.startswith(prefix) for p in folder.glob("*.json"))


def find_latest_complete_reply(folder: Path, cycle_prefix: str, cycle_name: str):
    candidates = []
    for path in folder.glob(f"reply-{cycle_prefix}*.json"):
        try:
            data = load_json(path)
        except Exception:
            continue
        if data.get("status") != "complete":
            continue
        if str(data.get("cycle", "")) != cycle_name:
            continue
        candidates.append((path.stat().st_mtime, path, data))
    if not candidates:
        return None, None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1], candidates[0][2]


def find_latest_matching_reply(folder: Path, cycle_prefix: str, cycle_name: str, validator):
    candidates = []
    for path in folder.glob(f"reply-{cycle_prefix}*.json"):
        try:
            data = load_json(path)
        except Exception:
            continue
        if data.get("status") != "complete":
            continue
        if str(data.get("cycle", "")) != cycle_name:
            continue
        if not validator(data):
            continue
        candidates.append((path.stat().st_mtime, path, data))
    if not candidates:
        return None, None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1], candidates[0][2]


def valid_020a(data: dict) -> bool:
    report = data.get("report")
    if isinstance(report, dict):
        return report.get("conclusao", {}).get("pronto_para_revisao") is True
    output = data.get("output", "")
    return isinstance(output, str) and "PRIORIDADE_CONDICIONAL_DEFINIDA" in output and "pronto_para_revisao" in output.lower()


def valid_020b(data: dict) -> bool:
    output = data.get("output")
    if isinstance(output, dict):
        decision = output.get("DECISAO_SOBRE_A_PROGRESSAO", {})
        return decision.get("020B_homologado") is True and decision.get("ciclo_21_pode_ser_discutido") is True
    if isinstance(output, str):
        lowered = output.lower()
        return "020b homologado" in lowered and "ciclo 21 pode ser discutido" in lowered
    return False


def valid_021a(data: dict) -> bool:
    payload = REPO / "cycle21-input" / "cycle-021A-r5-conditional-opening-basis.json"
    if not payload.exists():
        return False
    try:
        parsed = load_json(payload)
    except Exception:
        return False
    if parsed.get("cycle_id") != "021A":
        return False
    readiness = parsed.get("readiness_classification")
    return readiness in {"OPENING_BASIS_DEFINED", "OPENING_BASIS_INCONCLUSIVA"}


def valid_021b(data: dict) -> bool:
    output = data.get("output")
    lowered = normalize_text(output)
    if isinstance(output, dict):
        decision = output.get("DECISAO_SOBRE_A_PROGRESSAO", {})
        if decision.get("021B_homologado") is True and decision.get("ciclo_22_pode_ser_discutido") is True:
            return True
    return "021b_homologado" in lowered and "ciclo 22 pode ser discutido" in lowered


def valid_022a(data: dict) -> bool:
    payload = REPO / "cycle22-input" / "cycle-022A-r5-opening-contract.json"
    if not payload.exists():
        return False
    try:
        parsed = load_json(payload)
    except Exception:
        return False
    if parsed.get("cycle_id") != "022A":
        return False
    readiness = parsed.get("readiness_classification")
    return readiness in {"OPENING_CONTRACT_DEFINED", "OPENING_CONTRACT_INCONCLUSIVO"}


def is_invalid_codex_reply(data: dict) -> bool:
    lowered = normalize_text(data.get("output"))
    markers = [
        "mensagem parece incompleta",
        "nao reconheco esse comando",
        "prompt injection",
        "potential prompt injection",
        "o que voce deseja que eu faca",
        "what do you want me to do",
        "youre out of extra usage",
        "you're out of extra usage"
    ]
    return any(marker in lowered for marker in markers)


def valid_021a_diag(data: dict) -> bool:
    output = data.get("output")
    if isinstance(output, dict):
        status = output.get("STATUS_GERAL", {})
        if status.get("021A_apto_para_retry") is True:
            return True
        validation = output.get("VALIDACAO", {})
        if normalize_text(validation.get("021A_apto_para_retry_valido")) == "sim":
            return True
        conclusion = output.get("CONCLUSAO", {})
        if "apto para retry valido" in normalize_text(conclusion.get("resumo")):
            return True
    lowered = normalize_text(output)
    return (
        "021a apto para retry valido: sim" in lowered or
        "021a apto para retry" in lowered or
        "integracao do codex local destravada: sim" in lowered or
        "texto contaminante foi removido do caminho do codex local: sim" in lowered
    )


def valid_022a_diag(data: dict) -> bool:
    output = data.get("output")
    if isinstance(output, dict):
        status = output.get("STATUS_GERAL", {})
        if status.get("022A_apto_para_retry") is True:
            return True
        validation = output.get("VALIDACAO", {})
        if normalize_text(validation.get("022A_apto_para_retry_valido")) == "sim":
            return True
        conclusion = output.get("CONCLUSAO", {})
        if "022a pronto para retry valido" in normalize_text(conclusion.get("resumo")):
            return True
    lowered = normalize_text(output)
    return (
        "022a apto para retry valido: sim" in lowered or
        "022a apto para retry" in lowered or
        "022a pronto para retry valido" in lowered or
        "causa raiz identificada e corrigida" in lowered
    )


def is_invalid_claude_reply(data: dict) -> bool:
    lowered = normalize_text(data.get("output"))
    markers = [
        "nao encontrei arquivos relacionados",
        "pode me dar mais contexto",
        "o que precisa ser feito",
        "youre out of extra usage",
        "you're out of extra usage",
        "mensagem parece incompleta",
        "nao reconheco esse comando"
    ]
    return any(marker in lowered for marker in markers)


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


def create_021a_task(reply_path: Path, retry: bool = False):
    ts = now_compact()
    task_prefix = "task-021A-RETRY" if retry else "task-021A"
    reply_prefix = "reply-021A-RETRY" if retry else "reply-021A"
    task_name = f"{task_prefix}-{ts}.json"
    reply_name = f"{reply_prefix}-{ts}.json"
    task = {
        "task_id": f"task-021A-{ts}",
        "target_actor": "codex_local",
        "cycle": "021A",
        "instruction": (
            "Voce esta autorizado a executar UMA tentativa unica do ciclo 021A, em modo MANUAL/ORQUESTRADO, estritamente documental, read-only, sem runner stateful e sem analise de conteudo real de fallback. "
            "O ciclo 020B homologou a priorizacao condicional de R5 como foco defensavel da fila remanescente. Sua missao e produzir o payload oficial do 021A para definir a base de abertura condicional de R5: "
            "quais evidencias agregadas e nao sensiveis seriam necessarias, quais criterios documentais devem ser aplicados e quais non-goals precisam ficar explicitados antes de qualquer abertura futura. "
            "Este ciclo NAO abre R5 para analise de conteudo. Este ciclo NAO autoriza live CRM, sandbox, escrita, SQL, DDL, DML, producao, bridge, .mcp.json, R2 ou R6. "
            "Fontes oficiais obrigatorias: cycle20-input/cycle-020A-conditional-queue-prioritization.json; coordination/outbox_claude/reply-020B-20260404T132226Z.json; cycle19-input/cycle-019A-post-r2-closure-queue-assessment.json; cycle19-input/queue_source_map.json; output/cycle-005-write-proposals.json; output/cycle-004-execution-plan.json; output/cycle-003-improvement-plan.json. "
            "Arquivo a criar: cycle21-input/cycle-021A-r5-conditional-opening-basis.json. "
            "O JSON deve ser parseavel e conter no minimo: cycle_id=021A; mode=r5-conditional-opening-basis; agent=manual-orchestrated; generated_at; source_precedence; inherited_constraints; focus_reference com selected_focus=R5 e condition_family=pending_validation_evidence_collection; opening_basis com required_evidence_inputs, validation_criteria, documentary_boundaries, explicit_non_goals, why_r5_and_not_others; readiness_classification com um de OPENING_BASIS_DEFINED ou OPENING_BASIS_INCONCLUSIVA; authorization_reset com todos os flags false; blockers; violations=[]; prohibitions; anomalies; evidence_trace; meta.output_file. "
            "Regra central: orientar um futuro contrato de abertura de R5 sem autorizar a abertura agora. Se a base documental nao bastar para definir criterios objetivos, prefira OPENING_BASIS_INCONCLUSIVA. "
            "Ao final, responda no formato: INICIO DO RELATORIO / STATUS GERAL / PRODUCAO DO 021A / VALIDACAO DO PAYLOAD / BASE DE ABERTURA DE R5 / ISOLAMENTO PRESERVADO / CONCLUSAO / ARTEFATOS / FIM DO RELATORIO."
        ),
        "context_files": [
            "STATE.md",
            "cycle20-input/cycle-020A-conditional-queue-prioritization.json",
            str(reply_path.relative_to(REPO)).replace("\\", "/"),
            "cycle19-input/cycle-019A-post-r2-closure-queue-assessment.json",
            "cycle19-input/queue_source_map.json"
        ],
        "output_path": f"coordination/outbox_codex_local/{reply_name}",
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
    path = INBOX_CODEX / task_name
    save_json(path, task)
    return path


def create_021a_diag_task(reply_path: Path):
    ts = now_compact()
    task_name = f"task-021A-DIAG-{ts}.json"
    reply_name = f"reply-021A-DIAG-{ts}.json"
    task = {
        "task_id": f"task-021A-DIAG-{ts}",
        "target_actor": "claude_local",
        "cycle": "021A-DIAG",
        "instruction": (
            "Voce deve diagnosticar por que o CODEX LOCAL respondeu de forma generica/incompleta ao ciclo 021A em vez de produzir o payload esperado. "
            "Objetivo: encontrar o ponto exato do caminho local que fez o prompt chegar truncado ou descaracterizado, corrigir o minimo necessario e dizer se 021A esta apto para retry valido. "
            "Leia obrigatoriamente: STATE.md; coordination/inbox_codex_local/_archive/ ou task 021A correspondente; coordination/outbox_codex_local/reply-021A*.json; poller-autonomous.ps1; logs locais relevantes. "
            "Red lines: nao tocar em producao, bridge, .mcp.json, projeto real, R2, R6. "
            "Formato obrigatorio: INICIO DO RELATORIO / STATUS GERAL / DIAGNOSTICO / CORRECOES APLICADAS / VALIDACAO / GIT / CONCLUSAO / FIM DO RELATORIO. "
            "O bloco VALIDACAO deve responder explicitamente: '021A apto para retry valido: sim/nao'."
        ),
        "context_files": [
            "STATE.md",
            str(reply_path.relative_to(REPO)).replace("\\", "/"),
            "cycle20-input/cycle-020A-conditional-queue-prioritization.json",
            "coordination/outbox_claude/reply-020B-20260404T132226Z.json"
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


def create_021b_task(reply_path: Path):
    ts = now_compact()
    task_name = f"task-021B-{ts}.json"
    reply_name = f"reply-021B-{ts}.json"
    task = {
        "task_id": f"task-021B-{ts}",
        "target_actor": "claude_local",
        "cycle": "021B",
        "instruction": (
            "Voce deve revisar o payload do ciclo 021A e decidir se a base documental de abertura condicional de R5 esta formalmente homologavel. "
            "Objetivo: confirmar se o 021A definiu criterios documentais objetivos, non-goals claros, fronteiras de autorizacao e justificativa suficiente para orientar um futuro contrato de abertura de R5 sem autorizar abertura agora. "
            "Verifique especificamente: 1. se opening_basis.required_evidence_inputs e validation_criteria sao objetivos e auditaveis; 2. se documentary_boundaries e explicit_non_goals impedem abertura implicita; "
            "3. se why_r5_and_not_others preserva a base do 020A/020B sem reabrir R1/R3/R4; 4. se readiness_classification e tecnicamente defensavel; 5. se o payload 021A e formalmente homologavel. "
            "Nao modificar nada. Nao tocar em producao, bridge, .mcp.json, projeto real, R2, R6. "
            "Formato obrigatorio da resposta: INICIO DO RELATORIO / VEREDITO / EVIDENCIAS OBRIGATORIAS RECEBIDAS / CLASSIFICACAO DO RESULTADO / AVALIACAO DA BASE DE ABERTURA / DECISAO SOBRE A PROGRESSAO / CRITERIO OBJETIVO QUE DECIDIU O CASO / O QUE NAO DEVE MUDAR / RESUMO EXECUTIVO / FIM DO RELATORIO. "
            "A decisao sobre a progressao deve responder se 021B pode ser homologado e se o ciclo 22 pode ser discutido."
        ),
        "context_files": [
            "STATE.md",
            "cycle21-input/cycle-021A-r5-conditional-opening-basis.json",
            str(reply_path.relative_to(REPO)).replace("\\", "/"),
            "cycle20-input/cycle-020A-conditional-queue-prioritization.json",
            "coordination/outbox_claude/reply-020B-20260404T132226Z.json"
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


def create_022a_task(reply_path: Path):
    ts = now_compact()
    task_name = f"task-022A-{ts}.json"
    reply_name = f"reply-022A-{ts}.json"
    task = {
        "task_id": f"task-022A-{ts}",
        "target_actor": "codex_local",
        "cycle": "022A",
        "instruction": (
            "Voce esta autorizado a executar UMA tentativa unica do ciclo 022A, em modo MANUAL/ORQUESTRADO, estritamente documental, read-only, sem runner stateful e sem coletar dados reais neste ciclo. "
            "O ciclo 021B homologou a base de abertura condicional de R5. Sua missao e produzir o payload oficial do 022A para formalizar o CONTRATO DE ABERTURA de R5, definindo exatamente como um ciclo futuro podera coletar EV1, EV2 e EV3 e aplicar VC1, VC2, VC3 e VC4, sem autorizar essa coleta agora. "
            "Este ciclo NAO executa a abertura de R5. Este ciclo NAO coleta amostras reais. Este ciclo NAO autoriza live CRM, sandbox, escrita, SQL, DDL, DML, producao, bridge, .mcp.json, R2 ou R6. "
            "Fontes oficiais obrigatorias: cycle21-input/cycle-021A-r5-conditional-opening-basis.json; coordination/outbox_claude/reply-021B-20260404T143857Z.json; cycle20-input/cycle-020A-conditional-queue-prioritization.json; coordination/outbox_claude/reply-020B-20260404T132226Z.json; cycle19-input/cycle-019A-post-r2-closure-queue-assessment.json. "
            "Arquivo a criar: cycle22-input/cycle-022A-r5-opening-contract.json. "
            "O JSON deve ser parseavel e conter no minimo: cycle_id=022A; mode=r5-opening-contract; agent=manual-orchestrated; generated_at; source_precedence; inherited_constraints; opening_reference com selected_focus=R5, readiness_inherited=OPENING_BASIS_DEFINED, homologation_basis=021B; contract_scope com objective, permitted_future_inputs (EV1, EV2, EV3), prohibited_actions_now, future_validation_protocol (VC1-VC4), acceptance_gates, execution_non_goals; collection_contract with collection_requirements, evidence_format_rules, pii_controls, isolation_requirements, future_authorization_dependencies; readiness_classification com um de OPENING_CONTRACT_DEFINED ou OPENING_CONTRACT_INCONCLUSIVO; authorization_reset com todos os flags false; blockers; violations=[]; prohibitions; anomalies; evidence_trace; meta.output_file. "
            "Regra central: transformar a base de abertura do 021A em contrato operacional futuro, mas sem iniciar a abertura agora. Se a base nao bastar para definir gates objetivos do contrato, prefira OPENING_CONTRACT_INCONCLUSIVO. "
            "Ao final, responda no formato: INICIO DO RELATORIO / STATUS GERAL / PRODUCAO DO 022A / VALIDACAO DO PAYLOAD / CONTRATO DE ABERTURA DE R5 / ISOLAMENTO PRESERVADO / CONCLUSAO / ARTEFATOS / FIM DO RELATORIO."
        ),
        "context_files": [
            "STATE.md",
            "cycle21-input/cycle-021A-r5-conditional-opening-basis.json",
            str(reply_path.relative_to(REPO)).replace("\\", "/"),
            "cycle20-input/cycle-020A-conditional-queue-prioritization.json",
            "coordination/outbox_claude/reply-020B-20260404T132226Z.json",
            "cycle19-input/cycle-019A-post-r2-closure-queue-assessment.json"
        ],
        "output_path": f"coordination/outbox_codex_local/{reply_name}",
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
    path = INBOX_CODEX / task_name
    save_json(path, task)
    return path


def create_022a_retry_task(diag_reply_path: Path):
    ts = now_compact()
    task_name = f"task-022A-RETRY-{ts}.json"
    reply_name = f"reply-022A-RETRY-{ts}.json"
    task = {
        "task_id": f"task-022A-RETRY-{ts}",
        "target_actor": "codex_local",
        "cycle": "022A",
        "instruction": (
            "Retry unico do 022A apos diagnostico conclusivo do Claude Local. Voce esta autorizado a executar UMA tentativa unica do ciclo 022A, em modo MANUAL/ORQUESTRADO, estritamente documental, read-only, sem runner stateful e sem coletar dados reais neste ciclo. "
            "O ciclo 021B homologou a base de abertura condicional de R5 e o diagnostico do 022A liberou um retry valido. Sua missao continua a mesma: produzir o payload oficial do 022A para formalizar o CONTRATO DE ABERTURA de R5, definindo exatamente como um ciclo futuro podera coletar EV1, EV2 e EV3 e aplicar VC1, VC2, VC3 e VC4, sem autorizar essa coleta agora. "
            "Este ciclo NAO executa a abertura de R5. Este ciclo NAO coleta amostras reais. Este ciclo NAO autoriza live CRM, sandbox, escrita, SQL, DDL, DML, producao, bridge, .mcp.json, R2 ou R6. "
            "Fontes oficiais obrigatorias: cycle21-input/cycle-021A-r5-conditional-opening-basis.json; coordination/outbox_claude/reply-021B-20260404T143857Z.json; cycle20-input/cycle-020A-conditional-queue-prioritization.json; coordination/outbox_claude/reply-020B-20260404T132226Z.json; cycle19-input/cycle-019A-post-r2-closure-queue-assessment.json. "
            "Arquivo a criar: cycle22-input/cycle-022A-r5-opening-contract.json. "
            "O JSON deve ser parseavel e conter no minimo: cycle_id=022A; mode=r5-opening-contract; agent=manual-orchestrated; generated_at; source_precedence; inherited_constraints; opening_reference com selected_focus=R5, readiness_inherited=OPENING_BASIS_DEFINED, homologation_basis=021B; contract_scope com objective, permitted_future_inputs (EV1, EV2, EV3), prohibited_actions_now, future_validation_protocol (VC1-VC4), acceptance_gates, execution_non_goals; collection_contract with collection_requirements, evidence_format_rules, pii_controls, isolation_requirements, future_authorization_dependencies; readiness_classification com um de OPENING_CONTRACT_DEFINED ou OPENING_CONTRACT_INCONCLUSIVO; authorization_reset com todos os flags false; blockers; violations=[]; prohibitions; anomalies; evidence_trace; meta.output_file. "
            "Regra central: transformar a base de abertura do 021A em contrato operacional futuro, mas sem iniciar a abertura agora. Se a base nao bastar para definir gates objetivos do contrato, prefira OPENING_CONTRACT_INCONCLUSIVO. "
            "Ao final, responda no formato: INICIO DO RELATORIO / STATUS GERAL / PRODUCAO DO 022A / VALIDACAO DO PAYLOAD / CONTRATO DE ABERTURA DE R5 / ISOLAMENTO PRESERVADO / CONCLUSAO / ARTEFATOS / FIM DO RELATORIO."
        ),
        "context_files": [
            "STATE.md",
            "cycle21-input/cycle-021A-r5-conditional-opening-basis.json",
            str(diag_reply_path.relative_to(REPO)).replace("\\", "/"),
            "coordination/outbox_claude/reply-021B-20260404T143857Z.json",
            "cycle20-input/cycle-020A-conditional-queue-prioritization.json",
            "coordination/outbox_claude/reply-020B-20260404T132226Z.json",
            "cycle19-input/cycle-019A-post-r2-closure-queue-assessment.json"
        ],
        "output_path": f"coordination/outbox_codex_local/{reply_name}",
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
    path = INBOX_CODEX / task_name
    save_json(path, task)
    return path


def create_022a_diag_task(reply_path: Path):
    ts = now_compact()
    task_name = f"task-022A-DIAG-{ts}.json"
    reply_name = f"reply-022A-DIAG-{ts}.json"
    task = {
        "task_id": f"task-022A-DIAG-{ts}",
        "target_actor": "claude_local",
        "cycle": "022A-DIAG",
        "instruction": (
            "Voce deve diagnosticar por que o CODEX LOCAL respondeu de forma generica/incompleta ao ciclo 022A em vez de produzir o payload esperado. "
            "Objetivo: encontrar o ponto exato do caminho local que fez o prompt chegar truncado ou descaracterizado, corrigir o minimo necessario e dizer se 022A esta apto para retry valido. "
            "Leia obrigatoriamente: STATE.md; task 022A correspondente; reply 022A correspondente; poller-autonomous.ps1; logs locais relevantes. "
            "Red lines: nao tocar em producao, bridge, .mcp.json, projeto real, R2, R6. "
            "Formato obrigatorio: INICIO DO RELATORIO / STATUS GERAL / DIAGNOSTICO / CORRECOES APLICADAS / VALIDACAO / GIT / CONCLUSAO / FIM DO RELATORIO. "
            "O bloco VALIDACAO deve responder explicitamente: '022A apto para retry valido: sim/nao'."
        ),
        "context_files": [
            "STATE.md",
            str(reply_path.relative_to(REPO)).replace("\\", "/"),
            "cycle21-input/cycle-021A-r5-conditional-opening-basis.json",
            "coordination/outbox_claude/reply-021B-20260404T143857Z.json"
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


def create_022a_diag_retry_task(invalid_diag_reply_path: Path):
    ts = now_compact()
    task_name = f"task-022A-DIAG-RETRY-{ts}.json"
    reply_name = f"reply-022A-DIAG-RETRY-{ts}.json"
    task = {
        "task_id": f"task-022A-DIAG-RETRY-{ts}",
        "target_actor": "claude_local",
        "cycle": "022A-DIAG",
        "instruction": (
            "Retry unico do diagnostico do 022A. O reply anterior do diagnostico foi generico e nao investigou o caminho real do prompt. "
            "Sua missao e identificar por que o CODEX LOCAL respondeu de forma incompleta ao 022A em vez de produzir o payload esperado do contrato de abertura de R5. "
            "Compare o caminho bem-sucedido do 021A/021B com o 022A falho e localize o ponto exato da regressao no caminho local do CODEX LOCAL. "
            "Verifique obrigatoriamente: poller-autonomous.ps1; qualquer funcao Build-Prompt ou equivalente; current_task_codex_local.txt/json; temp_prompt.txt se existir; "
            "coordination/_archive/inbox_codex_local/task-022A-20260404T182446Z.json; coordination/outbox_codex_local/reply-022A-20260404T152521Z.json; "
            "coordination/outbox_claude/reply-021B-20260404T143857Z.json; logs locais relevantes do poller. "
            "Red lines absolutas: nao tocar em producao, bridge, .mcp.json do projeto real, projeto real, R2, R6. "
            "Se precisar editar algo, faca a menor correcao segura. Se precisar reiniciar tarefa agendada/processo local, faca de modo controlado. "
            "Nao crie novo retry do 022A sem concluir o diagnostico. "
            "Formato obrigatorio da resposta: INICIO DO RELATORIO / STATUS GERAL / DIAGNOSTICO / CORRECOES APLICADAS / VALIDACAO / GIT / CONCLUSAO / FIM DO RELATORIO. "
            "Campos minimos: concluido, risco_operacional_atual, causa_raiz_identificada, ponto_exato_da_regressao, evidencias_objetivas, arquivos_logs_inspecionados, "
            "arquivos_alterados, processos_reiniciados, prompt_final_do_022A_esta_materialmente_completo_sim_nao, 022A_apto_para_retry_valido_sim_nao, "
            "mudancas_commitadas_sim_nao, commit_hash, push_realizado_sim_nao, bloqueio_remanescente, proximo_passo_sugerido. "
            "Nao responda com hipotese vaga; eu preciso do ponto exato da regressao do 022A."
        ),
        "context_files": [
            "STATE.md",
            "coordination/_archive/inbox_codex_local/task-022A-20260404T182446Z.json",
            "coordination/outbox_codex_local/reply-022A-20260404T152521Z.json",
            str(invalid_diag_reply_path.relative_to(REPO)).replace("\\", "/"),
            "coordination/outbox_claude/reply-021B-20260404T143857Z.json",
            "cycle21-input/cycle-021A-r5-conditional-opening-basis.json"
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


def archive_tasks(prefix: str, src: Path, dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    moved = []
    for candidate in src.glob(f"{prefix}*.json"):
        target = dst / candidate.name
        if candidate.exists():
            candidate.replace(target)
            moved.append(target)
    return moved


def archive_tasks_filtered(prefix: str, src: Path, dst: Path, exclude_prefixes=None):
    dst.mkdir(parents=True, exist_ok=True)
    moved = []
    exclude_prefixes = exclude_prefixes or []
    for candidate in src.glob(f"{prefix}*.json"):
        if any(candidate.name.startswith(exclude) for exclude in exclude_prefixes):
            continue
        target = dst / candidate.name
        if candidate.exists():
            candidate.replace(target)
            moved.append(target)
    return moved


def commit_push(files, message):
    relative_files = []
    for file_path in files:
        if file_path.exists():
            relative_files.append(str(file_path.relative_to(REPO)))
    if not relative_files:
        return False
    git(["add", *relative_files])
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


def update_state_after_020a(task_name: str):
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
        text += """

## Resultado consolidado do ciclo 20

| Microfase | Veredito | Observacao |
|---|---|---|
| 20A | PRODUZIDO | PRIORIZAR_CONDICAO / selected_focus = R5 |
| 20B | PENDENTE | revisao do Claude Local ainda nao executada |
"""
    STATE_MD.write_text(text, encoding="utf-8")


def update_state_after_020b(task_name: str):
    text = STATE_MD.read_text(encoding="utf-8")
    replacements = {
        "| Fase em andamento | 020A concluido — 020B pendente de revisao do Claude Local |":
            "| Fase em andamento | ciclo 20 homologado — 021A pendente de producao do CODEX LOCAL |",
        "| Próxima etapa | Claude Local revisa o payload do 020A e decide homologacao do 020B |":
            "| Próxima etapa | CODEX LOCAL produz a base documental de abertura condicional de R5 no 021A |",
        "| Status inbox_claude | task-020B-20260404T132226Z.json pendente |":
            "| Status inbox_claude | vazio (020B homologado) |",
        "| Status inbox_codex_local | vazio (020A concluido; aguardando revisao 020B) |":
            f"| Status inbox_codex_local | {task_name} pendente |",
        "| Acao em curso | Claude Local revisa o payload do 020A para confirmar ou corrigir a priorizacao condicional de R5 |":
            "| Acao em curso | CODEX LOCAL prepara a base documental de abertura condicional de R5 para o ciclo 21 |",
        "| 20B | PENDENTE | revisao do Claude Local ainda nao executada |":
            "| 20B | HOMOLOGADO | R5 confirmado como prioridade condicional defensavel |"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if "## Resultado consolidado do ciclo 21" not in text:
        text += """

## Resultado consolidado do ciclo 21

| Microfase | Veredito | Observacao |
|---|---|---|
| 21A | PENDENTE | base documental de abertura condicional de R5 ainda nao produzida |
"""
    STATE_MD.write_text(text, encoding="utf-8")


def update_state_after_021a_invalid(task_name: str):
    text = STATE_MD.read_text(encoding="utf-8")
    replacements = {
        "| Fase em andamento | ciclo 20 homologado — 021A pendente de producao do CODEX LOCAL |":
            "| Fase em andamento | 021A bloqueado por reply generico do CODEX LOCAL — diagnostico local pendente |",
        "| Próxima etapa | CODEX LOCAL produz a base documental de abertura condicional de R5 no 021A |":
            "| Próxima etapa | Claude Local diagnostica o caminho do 021A e libera retry limpo do CODEX LOCAL |",
        "| Status inbox_claude | vazio (020B homologado) |":
            f"| Status inbox_claude | {task_name} pendente |",
        "| Status inbox_codex_local | task-021A-20260404T133410Z.json pendente |":
            "| Status inbox_codex_local | vazio (task 021A arquivada apos reply generico) |",
        "| Acao em curso | CODEX LOCAL prepara a base documental de abertura condicional de R5 para o ciclo 21 |":
            "| Acao em curso | Claude Local diagnostica por que o prompt do 021A chegou incompleto ao CODEX LOCAL |",
        "| 21A | PENDENTE | base documental de abertura condicional de R5 ainda nao produzida |":
            "| 21A | BLOQUEADO | reply generico do CODEX LOCAL; diagnostico local pendente |"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    STATE_MD.write_text(text, encoding="utf-8")


def update_state_after_021a_retry(task_name: str):
    text = STATE_MD.read_text(encoding="utf-8")
    replacements = {
        "| Fase em andamento | 021A bloqueado por reply generico do CODEX LOCAL — diagnostico local pendente |":
            "| Fase em andamento | 021A em retry limpo — aguardando payload do CODEX LOCAL |",
        "| Próxima etapa | Claude Local diagnostica o caminho do 021A e libera retry limpo do CODEX LOCAL |":
            "| Próxima etapa | CODEX LOCAL reprocesa o 021A apos correcao local validada pelo Claude |",
        "| Status inbox_claude | task-021A-DIAG-":  # sentinel, no exact replace
            "| Status inbox_claude | vazio (diagnostico 021A concluido) |",
        "| Status inbox_codex_local | vazio (task 021A arquivada apos reply generico) |":
            f"| Status inbox_codex_local | {task_name} pendente |",
        "| Acao em curso | Claude Local diagnostica por que o prompt do 021A chegou incompleto ao CODEX LOCAL |":
            "| Acao em curso | CODEX LOCAL recebe retry limpo do 021A apos diagnostico local conclusivo |",
        "| 21A | BLOQUEADO | reply generico do CODEX LOCAL; diagnostico local pendente |":
            "| 21A | RETRY_EM_CURSO | aguardando nova producao do CODEX LOCAL |"
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
    text = text.replace("| Status inbox_claude | task-021A-DIAG-", "| Status inbox_claude | vazio (diagnostico 021A concluido) |")
    STATE_MD.write_text(text, encoding="utf-8")


def update_state_after_021a_success(task_name: str):
    text = STATE_MD.read_text(encoding="utf-8")
    replacements = {
        "| Fase em andamento | 021A em retry limpo — aguardando payload do CODEX LOCAL |":
            "| Fase em andamento | 021A concluido — 021B pendente de revisao do Claude Local |",
        "| Fase em andamento | ciclo 20 homologado — 021A pendente de producao do CODEX LOCAL |":
            "| Fase em andamento | 021A concluido — 021B pendente de revisao do Claude Local |",
        "| Próxima etapa | CODEX LOCAL reprocesa o 021A apos correcao local validada pelo Claude |":
            "| Próxima etapa | Claude Local revisa a base documental do 021A e decide homologacao do 021B |",
        "| Próxima etapa | CODEX LOCAL produz a base documental de abertura condicional de R5 no 021A |":
            "| Próxima etapa | Claude Local revisa a base documental do 021A e decide homologacao do 021B |",
        "| Status inbox_claude | vazio (020B homologado) |":
            f"| Status inbox_claude | {task_name} pendente |",
        "| Status inbox_codex_local | task-021A-20260404T133410Z.json pendente |":
            "| Status inbox_codex_local | vazio (021A concluido; aguardando revisao 021B) |",
        "| Status inbox_codex_local | task-021A-RETRY": "| Status inbox_codex_local | vazio (021A concluido; aguardando revisao 021B) |",
        "| Acao em curso | CODEX LOCAL prepara a base documental de abertura condicional de R5 para o ciclo 21 |":
            "| Acao em curso | Claude Local revisa a base documental do 021A para homologar ou corrigir o 021B |",
        "| Acao em curso | CODEX LOCAL recebe retry limpo do 021A apos diagnostico local conclusivo |":
            "| Acao em curso | Claude Local revisa a base documental do 021A para homologar ou corrigir o 021B |",
        "| 21A | PENDENTE | base documental de abertura condicional de R5 ainda nao produzida |":
            "| 21A | PRODUZIDO | base documental de abertura condicional de R5 produzida pelo CODEX LOCAL |",
        "| 21A | RETRY_EM_CURSO | aguardando nova producao do CODEX LOCAL |":
            "| 21A | PRODUZIDO | base documental de abertura condicional de R5 produzida pelo CODEX LOCAL |"
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
    if "021B" not in text:
        text += """
| 21B | PENDENTE | revisao do Claude Local ainda nao executada |
"""
    elif "| 21B |" not in text:
        text += "\n| 21B | PENDENTE | revisao do Claude Local ainda nao executada |\n"
    STATE_MD.write_text(text, encoding="utf-8")


def update_state_after_021b(task_name: str):
    text = STATE_MD.read_text(encoding="utf-8")
    replacements = {
        "> Atualizado em: 2026-04-04 (021A PRODUZIDO — OPENING_BASIS_DEFINED para R5; aguardando homologacao 021B)":
            "> Atualizado em: 2026-04-04 (021B homologado; 022A emitido para formalizar o contrato de abertura de R5)",
        "| Ciclo ativo | 21 |":
            "| Ciclo ativo | 22 |",
        "| Fase em andamento | 021A PRODUZIDO — aguardando homologacao (021B) |":
            "| Fase em andamento | 021B homologado — 022A pendente de producao do CODEX LOCAL |",
        "| Próxima etapa | Orquestrador homologa payload 021A; se aprovado, emite contrato de abertura de R5 (022A) |":
            "| Próxima etapa | CODEX LOCAL formaliza o contrato de abertura de R5 no 022A |",
        "| Status inbox_claude | task-021A-DIAG-20260404T133957Z.json (processado — reply existente) |":
            "| Status inbox_claude | vazio (021B homologado) |",
        "| Status inbox_codex_local | vazio (021A concluido; aguardando revisao 021B) |-20260404T142951Z.json (reply produzido por claude_local) |":
            f"| Status inbox_codex_local | {task_name} pendente |",
        "| 21A | PRODUZIDO | OPENING_BASIS_DEFINED / R5 / reply em outbox_codex_local |":
            "| 21A | PRODUZIDO | OPENING_BASIS_DEFINED / R5 / reply em outbox_codex_local |",
        "| Acao em curso | Claude Local diagnostica por que o prompt do 021A chegou incompleto ao CODEX LOCAL |":
            "| Acao em curso | CODEX LOCAL formaliza o contrato de abertura de R5 com base em EV1, EV2, EV3 e VC1-VC4 |"
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
    if "| 21B |" in text:
        text = text.replace("| 21B | PENDENTE | revisao do Claude Local ainda nao executada |", "| 21B | HOMOLOGADO | base de abertura de R5 confirmada; ciclo 22 pode ser discutido |")
    else:
        text += "\n| 21B | HOMOLOGADO | base de abertura de R5 confirmada; ciclo 22 pode ser discutido |\n"
    if "## Resultado consolidado do ciclo 22" not in text:
        text += """

## Resultado consolidado do ciclo 22

| Microfase | Veredito | Observacao |
|---|---|---|
| 22A | PENDENTE | contrato de abertura de R5 ainda nao produzido |
"""
    STATE_MD.write_text(text, encoding="utf-8")


def replace_line_starting_with(lines, prefix, new_line):
    replaced = False
    for idx, line in enumerate(lines):
        if line.startswith(prefix):
            lines[idx] = new_line
            replaced = True
            break
    if not replaced:
        lines.append(new_line)
    return lines


def reconcile_state_md():
    if not STATE_MD.exists():
        return
    text = STATE_MD.read_text(encoding="utf-8")
    lines = text.splitlines()

    latest_task_022a = next(iter(sorted(INBOX_CODEX.glob("task-022A*.json"), key=lambda p: p.stat().st_mtime, reverse=True)), None)
    latest_task_022a_diag = next(iter(sorted(INBOX_CLAUDE.glob("task-022A-DIAG*.json"), key=lambda p: p.stat().st_mtime, reverse=True)), None)
    invalid_022a_path, _ = find_latest_matching_reply(OUTBOX_CODEX, "022A", "022A", is_invalid_codex_reply)
    invalid_022a_diag_path, _ = find_latest_matching_reply(OUTBOX_CLAUDE, "022A-DIAG", "022A-DIAG", is_invalid_claude_reply)

    current_updated = "> Atualizado em: 2026-04-04 (021B homologado; 022A emitido para formalizar o contrato de abertura de R5)"
    cycle_value = "| Ciclo ativo | 22 |"
    phase_value = "| Fase em andamento | 021B homologado — 022A pendente de producao do CODEX LOCAL |"
    next_value = "| Próxima etapa | CODEX LOCAL formaliza o contrato de abertura de R5 no 022A |"
    claude_value = "| Status inbox_claude | vazio (021B homologado) |"
    codex_value = f"| Status inbox_codex_local | {latest_task_022a.name} pendente |" if latest_task_022a else "| Status inbox_codex_local | vazio |"
    latest_commit = "orq: instrucao 022A para codex local"
    current_action = "| Acao em curso | CODEX LOCAL formaliza o contrato de abertura de R5 com base em EV1, EV2, EV3 e VC1-VC4 |"
    result_21b = "| 21B | HOMOLOGADO | base de abertura de R5 confirmada; ciclo 22 pode ser discutido |"
    result_22a = "| 22A | PENDENTE | contrato de abertura de R5 ainda nao produzido |"

    if invalid_022a_path or latest_task_022a_diag:
        retry_diag = latest_task_022a_diag and "DIAG-RETRY" in latest_task_022a_diag.name
        current_updated = "> Atualizado em: 2026-04-04 (021B homologado; 022A bloqueado por reply generico; diagnostico 022A emitido automaticamente)"
        phase_value = "| Fase em andamento | 022A bloqueado por reply generico do CODEX LOCAL — diagnostico local pendente |"
        next_value = "| Próxima etapa | Claude Local diagnostica o caminho do 022A e libera retry limpo do CODEX LOCAL |"
        if latest_task_022a_diag:
            claude_value = f"| Status inbox_claude | {latest_task_022a_diag.name} pendente |"
        else:
            claude_value = "| Status inbox_claude | vazio (reply 022A generico detectado; diagnostico ainda nao emitido) |"
        codex_value = "| Status inbox_codex_local | vazio (task 022A arquivada apos reply generico) |"
        latest_commit = "orq: diagnostico 022A para claude"
        current_action = "| Acao em curso | Claude Local diagnostica por que o prompt do 022A chegou incompleto ao CODEX LOCAL |"
        result_22a = "| 22A | BLOQUEADO | reply generico do CODEX LOCAL; diagnostico local pendente |"
        if retry_diag:
            current_updated = "> Atualizado em: 2026-04-04 (021B homologado; 022A bloqueado; retry do diagnostico local pendente)"
            phase_value = "| Fase em andamento | 022A bloqueado por reply generico do CODEX LOCAL — retry diagnostico do Claude Local pendente |"
            next_value = "| Próxima etapa | Claude Local conclui o retry do diagnostico do 022A e, se conclusivo, libera retry limpo do CODEX LOCAL |"
            latest_commit = "orq: retry diagnostico 022A para claude"
            current_action = "| Acao em curso | Claude Local refaz o diagnostico do 022A com contexto mais estrito para localizar a regressao real |"
            result_22a = "| 22A | BLOQUEADO | aguardando retry diagnostico do Claude Local |"

    if invalid_022a_diag_path and not latest_task_022a_diag:
        current_updated = "> Atualizado em: 2026-04-04 (022A-DIAG respondeu genericamente; retry diagnostico do 022A pendente ou em preparo)"
        phase_value = "| Fase em andamento | 022A-DIAG falhou genericamente — aguardando retry diagnostico do Claude Local |"
        next_value = "| Próxima etapa | Reemitir diagnostico util do 022A e, se conclusivo, liberar retry limpo do CODEX LOCAL |"
        claude_value = "| Status inbox_claude | vazio (ultimo 022A-DIAG respondeu genericamente) |"
        codex_value = "| Status inbox_codex_local | vazio |"
        latest_commit = "orq: retry diagnostico 022A para claude"
        current_action = "| Acao em curso | Supervisor prepara novo diagnostico do 022A com contexto mais estrito para o Claude Local |"
        result_22a = "| 22A | BLOQUEADO | diagnostico local respondeu genericamente; retry diagnostico necessario |"

    lines = replace_line_starting_with(lines, "> Atualizado em:", current_updated)
    lines = replace_line_starting_with(lines, "| Ciclo ativo |", cycle_value)
    lines = replace_line_starting_with(lines, "| Fase em andamento |", phase_value)
    lines = replace_line_starting_with(lines, "| Próxima etapa |", next_value)
    lines = replace_line_starting_with(lines, "| Status inbox_claude |", claude_value)
    lines = replace_line_starting_with(lines, "| Status inbox_codex_local |", codex_value)
    lines = replace_line_starting_with(lines, "| coordination/inbox_claude/ |", claude_value.replace("| Status inbox_claude | ", "| coordination/inbox_claude/ | "))
    lines = replace_line_starting_with(lines, "| coordination/inbox_codex_local/ |", codex_value.replace("| Status inbox_codex_local | ", "| coordination/inbox_codex_local/ | "))
    lines = replace_line_starting_with(lines, "| Acao em curso |", current_action)
    lines = replace_line_starting_with(lines, "| 21B |", result_21b)
    lines = replace_line_starting_with(lines, "| 22A |", result_22a)

    joined = "\n".join(lines)
    joined = re.sub(r"## Ultimo commit relevante\s+```.*?```", f"## Ultimo commit relevante\n\n```\n{latest_commit}\n```", joined, flags=re.S)
    STATE_MD.write_text(joined + ("\n" if not joined.endswith("\n") else ""), encoding="utf-8")


def process_complete_020a(state):
    reply_path, reply_data = find_latest_complete_reply(OUTBOX_CODEX, "020A", "020A")
    if not reply_path or not valid_020a(reply_data):
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
    archived = archive_tasks("task-020A", INBOX_CODEX, ARCHIVE_CODEX)
    update_state_after_020a(created_task.name)
    state["processed_reply_ids"].append(reply_id)
    save_state(state)
    commit_push([created_task, reply_path, STATE_MD, *archived], "orq: instrucao 020B para claude")
    log(f"020A processado pelo supervisor. Task 020B emitida: {created_task.name}")
    return True


def process_complete_020b(state):
    reply_path, reply_data = find_latest_complete_reply(OUTBOX_CLAUDE, "020B", "020B")
    if not reply_path or not valid_020b(reply_data):
        return False

    reply_id = reply_data.get("reply_id") or reply_path.stem
    if reply_id in state["processed_reply_ids"]:
        return False

    if task_or_reply_exists("task-021A-", INBOX_CODEX) or task_or_reply_exists("reply-021A-", OUTBOX_CODEX):
        state["processed_reply_ids"].append(reply_id)
        save_state(state)
        return False

    created_task = create_021a_task(reply_path)
    reply_data["status"] = "processed"
    save_json(reply_path, reply_data)
    archived = archive_tasks("task-020B", INBOX_CLAUDE, ARCHIVE_CLAUDE)
    update_state_after_020b(created_task.name)
    state["processed_reply_ids"].append(reply_id)
    save_state(state)
    commit_push([created_task, reply_path, STATE_MD, *archived], "orq: instrucao 021A para codex local")
    log(f"020B processado pelo supervisor. Task 021A emitida: {created_task.name}")
    return True


def process_invalid_021a(state):
    reply_path, reply_data = find_latest_complete_reply(OUTBOX_CODEX, "021A", "021A")
    if not reply_path or valid_021a(reply_data) or not is_invalid_codex_reply(reply_data):
        return False

    reply_id = reply_data.get("reply_id") or reply_path.stem
    if reply_id in state["processed_reply_ids"]:
        return False

    if task_or_reply_exists("task-021A-DIAG-", INBOX_CLAUDE) or task_or_reply_exists("reply-021A-DIAG-", OUTBOX_CLAUDE):
        state["processed_reply_ids"].append(reply_id)
        save_state(state)
        return False

    created_task = create_021a_diag_task(reply_path)
    reply_data["status"] = "processed"
    save_json(reply_path, reply_data)
    archived = archive_tasks("task-021A", INBOX_CODEX, ARCHIVE_CODEX)
    update_state_after_021a_invalid(created_task.name)
    state["processed_reply_ids"].append(reply_id)
    save_state(state)
    commit_push([created_task, reply_path, STATE_MD, *archived], "orq: diagnostico 021A para claude")
    log(f"021A invalido processado pelo supervisor. Task diagnostica emitida: {created_task.name}")
    return True


def process_complete_021a_diag(state):
    reply_path, reply_data = find_latest_matching_reply(OUTBOX_CLAUDE, "021A-DIAG", "021A-DIAG", valid_021a_diag)
    if not reply_path:
        return False

    reply_id = reply_data.get("reply_id") or reply_path.stem
    if reply_id in state["processed_reply_ids"]:
        return False

    if task_or_reply_exists("task-021A-RETRY-", INBOX_CODEX) or task_or_reply_exists("reply-021A-RETRY-", OUTBOX_CODEX):
        state["processed_reply_ids"].append(reply_id)
        save_state(state)
        return False

    created_task = create_021a_task(reply_path, retry=True)
    reply_data["status"] = "processed"
    save_json(reply_path, reply_data)
    archived = archive_tasks("task-021A-DIAG-", INBOX_CLAUDE, ARCHIVE_CLAUDE)
    update_state_after_021a_retry(created_task.name)
    state["processed_reply_ids"].append(reply_id)
    save_state(state)
    commit_push([created_task, reply_path, STATE_MD, *archived], "orq: retry 021A para codex local")
    log(f"Diagnostico 021A processado pelo supervisor. Retry emitido: {created_task.name}")
    return True


def process_complete_021a(state):
    reply_path, reply_data = find_latest_complete_reply(OUTBOX_CODEX, "021A", "021A")
    if not reply_path or not valid_021a(reply_data):
        return False

    reply_id = reply_data.get("reply_id") or reply_path.stem
    if reply_id in state["processed_reply_ids"]:
        return False

    if task_or_reply_exists("task-021B-", INBOX_CLAUDE) or task_or_reply_exists("reply-021B-", OUTBOX_CLAUDE):
        state["processed_reply_ids"].append(reply_id)
        save_state(state)
        return False

    created_task = create_021b_task(reply_path)
    reply_data["status"] = "processed"
    save_json(reply_path, reply_data)
    archived = archive_tasks("task-021A", INBOX_CODEX, ARCHIVE_CODEX)
    update_state_after_021a_success(created_task.name)
    state["processed_reply_ids"].append(reply_id)
    save_state(state)
    commit_push([created_task, reply_path, STATE_MD, *archived], "orq: instrucao 021B para claude")
    log(f"021A processado pelo supervisor. Task 021B emitida: {created_task.name}")
    return True


def process_complete_021b(state):
    reply_path, reply_data = find_latest_matching_reply(OUTBOX_CLAUDE, "021B", "021B", valid_021b)
    if not reply_path:
        return False

    reply_id = reply_data.get("reply_id") or reply_path.stem
    if reply_id in state["processed_reply_ids"]:
        return False

    if task_or_reply_exists("task-022A-", INBOX_CODEX) or task_or_reply_exists("reply-022A-", OUTBOX_CODEX):
        state["processed_reply_ids"].append(reply_id)
        save_state(state)
        return False

    created_task = create_022a_task(reply_path)
    reply_data["status"] = "processed"
    save_json(reply_path, reply_data)
    archived = archive_tasks("task-021B", INBOX_CLAUDE, ARCHIVE_CLAUDE)
    update_state_after_021b(created_task.name)
    state["processed_reply_ids"].append(reply_id)
    save_state(state)
    commit_push([created_task, reply_path, STATE_MD, *archived], "orq: instrucao 022A para codex local")
    log(f"021B processado pelo supervisor. Task 022A emitida: {created_task.name}")
    return True


def process_invalid_022a(state):
    reply_path, reply_data = find_latest_matching_reply(OUTBOX_CODEX, "022A", "022A", is_invalid_codex_reply)
    if not reply_path:
        return False

    reply_id = reply_data.get("reply_id") or reply_path.stem
    if reply_id in state["processed_reply_ids"]:
        return False

    if task_or_reply_exists("task-022A-DIAG-", INBOX_CLAUDE) or task_or_reply_exists("reply-022A-DIAG-", OUTBOX_CLAUDE):
        state["processed_reply_ids"].append(reply_id)
        save_state(state)
        return False

    created_task = create_022a_diag_task(reply_path)
    reply_data["status"] = "processed"
    save_json(reply_path, reply_data)
    archived = archive_tasks("task-022A", INBOX_CODEX, ARCHIVE_CODEX)
    state["processed_reply_ids"].append(reply_id)
    save_state(state)
    reconcile_state_md()
    commit_push([created_task, reply_path, STATE_MD, *archived], "orq: diagnostico 022A para claude")
    log(f"022A invalido processado pelo supervisor. Task diagnostica emitida: {created_task.name}")
    return True


def process_complete_022a_diag(state):
    reply_path, reply_data = find_latest_matching_reply(OUTBOX_CLAUDE, "022A-DIAG", "022A-DIAG", valid_022a_diag)
    if not reply_path:
        return False

    reply_id = reply_data.get("reply_id") or reply_path.stem
    if reply_id in state["processed_reply_ids"]:
        return False

    if task_or_reply_exists("task-022A-RETRY-", INBOX_CODEX) or task_or_reply_exists("reply-022A-RETRY-", OUTBOX_CODEX):
        state["processed_reply_ids"].append(reply_id)
        save_state(state)
        return False

    created_task = create_022a_retry_task(reply_path)
    reply_data["status"] = "processed"
    save_json(reply_path, reply_data)
    archived = archive_tasks_filtered("task-022A-DIAG-", INBOX_CLAUDE, ARCHIVE_CLAUDE, exclude_prefixes=["task-022A-DIAG-RETRY-"])
    state["processed_reply_ids"].append(reply_id)
    save_state(state)
    reconcile_state_md()
    commit_push([created_task, reply_path, STATE_MD, *archived], "orq: retry 022A para codex local")
    log(f"Diagnostico 022A processado pelo supervisor. Retry emitido: {created_task.name}")
    return True


def process_invalid_022a_diag(state):
    reply_path, reply_data = find_latest_matching_reply(OUTBOX_CLAUDE, "022A-DIAG", "022A-DIAG", is_invalid_claude_reply)
    if not reply_path:
        return False

    reply_id = reply_data.get("reply_id") or reply_path.stem
    if reply_id in state["processed_reply_ids"]:
        return False

    if task_or_reply_exists("task-022A-DIAG-RETRY-", INBOX_CLAUDE) or task_or_reply_exists("reply-022A-DIAG-RETRY-", OUTBOX_CLAUDE):
        state["processed_reply_ids"].append(reply_id)
        save_state(state)
        return False

    created_task = create_022a_diag_retry_task(reply_path)
    reply_data["status"] = "processed"
    save_json(reply_path, reply_data)
    archived = archive_tasks_filtered("task-022A-DIAG-", INBOX_CLAUDE, ARCHIVE_CLAUDE, exclude_prefixes=["task-022A-DIAG-RETRY-"])
    state["processed_reply_ids"].append(reply_id)
    save_state(state)
    reconcile_state_md()
    commit_push([created_task, reply_path, STATE_MD, *archived], "orq: retry diagnostico 022A para claude")
    log(f"022A-DIAG invalido processado pelo supervisor. Retry diagnostico emitido: {created_task.name}")
    return True


def process_once():
    git_pull_ff_only()
    state = load_state()
    peer = active_local_peer()
    if peer:
        tailscale_ping(peer)

    changed = False
    if process_complete_020a(state):
        changed = True

    state = load_state()
    if process_complete_020b(state):
        changed = True

    state = load_state()
    if process_invalid_021a(state):
        changed = True

    state = load_state()
    if process_complete_021a_diag(state):
        changed = True

    state = load_state()
    if process_complete_021a(state):
        changed = True

    state = load_state()
    if process_complete_021b(state):
        changed = True

    state = load_state()
    if process_invalid_022a(state):
        changed = True

    state = load_state()
    if process_complete_022a_diag(state):
        changed = True

    state = load_state()
    if process_invalid_022a_diag(state):
        changed = True

    reconcile_state_md()

    return changed


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
