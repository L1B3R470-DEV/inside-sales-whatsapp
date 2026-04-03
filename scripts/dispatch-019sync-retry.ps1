$ErrorActionPreference = "Stop"

$repo = "C:\Users\murdo\workspace-integration"
Set-Location $repo

$utcNow = [DateTime]::UtcNow
$compact = $utcNow.ToString("yyyyMMddTHHmmssZ")
$createdAt = $utcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")

$task = [ordered]@{
    task_id = "task-019SYNC-$compact"
    target_actor = "codex_local"
    cycle = "019SYNC"
    instruction = "Executar UMA tentativa unica de saneamento de integracao apos o ciclo 19. Objetivo: materializar no repositorio os artefatos faltantes do ciclo 19 que ja foram referenciados e usados pelos replies validos de 19A e 19B, sem reclassificar a fila e sem iniciar analise de item novo. Trabalhe somente dentro de workspace-integration/. Nao tocar em producao, bridge local, .mcp.json ou projeto real. Nao reabrir R2 nem R6. Nao alterar o veredito vigente: queue_status deve permanecer TODOS_CONDICIONAIS e next_eligible_item deve permanecer null. Arquivos que devem existir ao final desta task, em cycle19-input/: artifact_index.json, closed_items_registry.json, remaining_queue_registry.json, queue_source_map.json, cycle19_scope_draft.json, cycle-019A-post-r2-closure-queue-assessment.json. Se algum deles nao existir mais localmente, reconstituir fielmente a partir das fontes documentais e dos replies de 19A/19B, sem introduzir fatos novos e registrando no relatorio quais arquivos foram copiados exatamente e quais foram reconstituídos fielmente. Nao gerar novo ciclo, nao revisar 19A de novo, nao criar elegibilidade nova. Sua saida deve ser um reply JSON valido no output_path com campo output contendo um relatorio textual completo e autocontido neste formato exato: INICIO DO RELATORIO; STATUS GERAL; MATERIALIZACAO DO CYCLE19-INPUT; INTEGRIDADE DOCUMENTAL; ISOLAMENTO PRESERVADO; CONCLUSAO; ARTEFATOS; FIM DO RELATORIO. No relatorio, responder explicitamente: arquivos obrigatorios presentes [sim/nao], payload 19A materializado [sim/nao], queue_status preservado = TODOS_CONDICIONAIS [sim/nao], next_eligible_item preservado = null [sim/nao], R2 e R6 permanecem excluidos [sim/nao], houve reconstituicao fiel [sim/nao], nada fora de workspace-integration foi alterado [sim/nao]."
    context_files = @(
        "coordination/outbox_codex_local/reply-019A-20260402T232410Z.json",
        "coordination/outbox_claude/reply-019B-20260402T233530Z.json",
        "output/cycle-018B-r2-iteration-closure-or-reopen-conditions-review.json",
        "output/cycle-005-write-proposals.json",
        "output/cycle-004-execution-plan.json",
        "output/cycle-003-improvement-plan.json",
        "output/cycle-002-crm-snapshot.json",
        "STATE.md"
    )
    output_path = "coordination/outbox_codex_local/reply-019SYNC-$compact.json"
    red_lines = @(
        "no_production_write",
        "no_bridge_write",
        "no_mcp_json_write"
    )
    status = "pending"
    created_at = $createdAt
}

$taskPath = Join-Path $repo "coordination\inbox_codex_local\task-019SYNC-$compact.json"
$task | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $taskPath -Encoding utf8

git add coordination/inbox_codex_local
git commit -m "orq: retry 019SYNC para codex local"
git push origin master
