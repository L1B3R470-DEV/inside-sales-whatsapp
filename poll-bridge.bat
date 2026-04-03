@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║          BRIDGE POLL — CICLO AUTONOMO OPENLAW                ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: ── 1. GIT PULL ─────────────────────────────────────────────────
echo [1/4] Atualizando projeto (git pull)...
git pull origin main 2>&1
echo.

:: ── 2. DOCKER / SERVICOS ─────────────────────────────────────────
echo [2/4] Status dos servicos...
docker ps --format "  %-22s %-12s %s" --no-trunc 2>nul | findstr /V "NAMES"
echo.

:: ── 3. ROUTER HEALTH ─────────────────────────────────────────────
echo [3/4] Router health (localhost:8091)...
powershell -NoLogo -NonInteractive -Command ^
  "try { $r = Invoke-RestMethod http://localhost:8091/health -TimeoutSec 3; Write-Host ('  ok=' + $r.ok + '  docs=' + $r.activeDocuments + '  chunks=' + $r.activeChunks + '  cache=' + $r.cacheItems) } catch { Write-Host '  ROUTER OFFLINE' -ForegroundColor Red }"
echo.

:: ── 4. BRIDGE INBOX ──────────────────────────────────────────────
echo [4/4] Tarefas pendentes no inbox...
set INBOX=C:\AUTOMACAO\cowork\claude_bridge\inbox_for_claude
set OUTBOX=C:\AUTOMACAO\cowork\claude_bridge\outbox_from_claude
set ACKS=C:\AUTOMACAO\cowork\claude_bridge\ack_from_codex

powershell -NoLogo -NonInteractive -Command ^
  "$inbox='%INBOX%'; $outbox='%OUTBOX%'; $acks='%ACKS%';" ^
  "$i=(Get-ChildItem $inbox -Filter *.json -EA SilentlyContinue).Count;" ^
  "$o=(Get-ChildItem $outbox -Filter *.json -EA SilentlyContinue).Count;" ^
  "$a=(Get-ChildItem $acks -Filter *.json -EA SilentlyContinue).Count;" ^
  "Write-Host ('  inbox=' + $i + '  outbox(replies)=' + $o + '  acks=' + $a);" ^
  "Write-Host '';" ^
  "$tasks = Get-ChildItem $inbox -Filter *.json -EA SilentlyContinue | Sort-Object LastWriteTime -Desc | Select-Object -First 10;" ^
  "if ($tasks) { Write-Host '  Ultimas tarefas:'; foreach ($f in $tasks) { try { $j = Get-Content $f.FullName -Raw | ConvertFrom-Json; $replied = Test-Path (Join-Path $outbox ('REPLY-' + $f.BaseName.Substring($f.BaseName.IndexOf('-')+1) + '.json')); $tag = if ($replied) { '[REPLY OK]' } else { '[PENDENTE]' }; Write-Host ('  ' + $tag + ' ' + $j.task_id + ' — ' + $j.title) } catch { Write-Host ('  [?] ' + $f.Name) } } } else { Write-Host '  (inbox vazio)' }"

echo.
echo ──────────────────────────────────────────────────────────────
echo  ACKs recentes:
powershell -NoLogo -NonInteractive -Command ^
  "$a='%ACKS%';" ^
  "Get-ChildItem $a -Filter *.json -EA SilentlyContinue | Sort-Object LastWriteTime -Desc | Select-Object -First 5 | ForEach-Object { try { $j = Get-Content $_.FullName -Raw | ConvertFrom-Json; Write-Host ('  ' + $j.reply_id + ' — ' + $j.status + ' @ ' + $j.acked_at) } catch { Write-Host ('  ' + $_.Name) } }"

echo.
echo ══════════════════════════════════════════════════════════════
pause
