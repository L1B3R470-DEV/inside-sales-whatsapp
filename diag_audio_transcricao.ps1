# diag_audio_transcricao.ps1
# Diagnostico completo de falha na transcricao de audios do router WhatsApp.
# Execute como Administrador no diretorio do projeto.
# Saida gravada em C:\AUTOMACAO\logs\diag_audio_TIMESTAMP.txt

$ErrorActionPreference = "Continue"
$Ts = (Get-Date -Format "yyyyMMdd_HHmmss")
$LogFile = "C:\AUTOMACAO\logs\diag_audio_$Ts.txt"
New-Item -ItemType Directory -Force -Path "C:\AUTOMACAO\logs" | Out-Null

function W { param([string]$msg, [string]$color = "White")
    Write-Host $msg -ForegroundColor $color
    Add-Content -Path $LogFile -Value $msg
}

W "============================================================" "Cyan"
W "DIAGNOSTICO AUDIO TRANSCRICAO — $Ts" "Cyan"
W "============================================================" "Cyan"
W ""

# ─── SECAO 1: TAILSCALE / REDE ───────────────────────────────
W "=== [1] TAILSCALE E INTERFACES DE REDE ===" "Yellow"
try {
    $ts_ips = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -match '^100\.' } | Select-Object -ExpandProperty IPAddress)
    if ($ts_ips) {
        W "  Tailscale IPs detectados: $($ts_ips -join ', ')" "Green"
    } else {
        W "  AVISO: Nenhum IP Tailscale (100.x.x.x) encontrado" "Red"
    }
} catch { W "  ERRO ao listar IPs: $_" "Red" }

try {
    $all_ips = Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, IPAddress
    $all_ips | ForEach-Object { W "    Interface: $($_.InterfaceAlias) => $($_.IPAddress)" }
} catch { W "  ERRO ao listar interfaces: $_" "Red" }
W ""

# ─── SECAO 2: CONTAINERS DOCKER ──────────────────────────────
W "=== [2] STATUS DOS CONTAINERS DOCKER ===" "Yellow"
try {
    $containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1
    W $containers
} catch { W "  ERRO docker ps: $_" "Red" }
W ""

# ─── SECAO 3: VARIAVEIS DE AMBIENTE DO ROUTER ────────────────
W "=== [3] ENV VARS DO CONTAINER ROUTER ===" "Yellow"
$env_vars = @(
    "OPENAI_API_KEY",
    "ROUTER_OPENAI_TRANSCRIBE_MODEL",
    "ROUTER_OPENAI_TRANSCRIBE_TIMEOUT_SECONDS",
    "ROUTER_MAX_AUDIO_BYTES",
    "ROUTER_CRM_PATH",
    "ROUTER_DB_PATH",
    "ROUTER_ML_DIR",
    "S3_ENDPOINT",
    "S3_ENABLED"
)
foreach ($v in $env_vars) {
    $val = docker exec router printenv $v 2>&1
    if ($LASTEXITCODE -eq 0) {
        if ($v -eq "OPENAI_API_KEY") {
            $masked = if ($val.Length -gt 10) { $val.Substring(0,6) + "..." + $val.Substring($val.Length-4) } else { "(curto/vazio)" }
            W "  $v = $masked"
        } else {
            W "  $v = $val"
        }
    } else {
        W "  $v = (NAO DEFINIDA)" "DarkGray"
    }
}
W ""

# ─── SECAO 4: TESTE OPENAI API KEY ───────────────────────────
W "=== [4] TESTE OPENAI API KEY (dentro do container) ===" "Yellow"
$openai_test = docker exec router python3 -c @"
import os, urllib.request, json
key = os.getenv('OPENAI_API_KEY','')
if not key:
    print('ERRO: OPENAI_API_KEY vazia')
else:
    req = urllib.request.Request(
        'https://api.openai.com/v1/models',
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            models = [m['id'] for m in data.get('data',[]) if 'whisper' in m['id'] or 'transcri' in m['id']]
            print(f'OK status={r.status} modelos_audio={models}')
    except Exception as e:
        print(f'ERRO: {type(e).__name__}: {e}')
"@ 2>&1
W "  Resultado: $openai_test" $(if ($openai_test -match "^OK") { "Green" } else { "Red" })
W ""

# ─── SECAO 5: FFMPEG NO CONTAINER ────────────────────────────
W "=== [5] FFMPEG NO CONTAINER ===" "Yellow"
$ff = docker exec router sh -c "ffmpeg -version 2>&1 | head -1" 2>&1
W "  $ff" $(if ($ff -match "ffmpeg version") { "Green" } else { "Red" })
$ff_path = docker exec router sh -c "which ffmpeg 2>/dev/null || echo 'not found'" 2>&1
W "  Path: $ff_path"
W ""

# ─── SECAO 6: ACESSIBILIDADE DE URL MINIO DO CONTAINER ───────
W "=== [6] MINIO ACESSIVEL DO CONTAINER ROUTER ===" "Yellow"
$minio_check = docker exec router python3 -c @"
import urllib.request
urls = [
    'http://minio:9000/minio/health/live',
    'http://localhost:9000/minio/health/live',
    'http://host.docker.internal:9000/minio/health/live',
]
for u in urls:
    try:
        with urllib.request.urlopen(u, timeout=5) as r:
            print(f'OK  {u} => status={r.status}')
    except Exception as e:
        print(f'FAIL {u} => {type(e).__name__}: {str(e)[:80]}')
"@ 2>&1
W $minio_check
W ""

# ─── SECAO 7: ULTIMO AUDIO NO route_logs ─────────────────────
W "=== [7] ULTIMOS 10 REGISTROS DE AUDIO NO route_logs ===" "Yellow"
$audio_logs = docker exec router python3 -c @"
import sqlite3, json, os
db = os.getenv('ROUTER_DB_PATH', '/app/router_runtime.sqlite')
try:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute('''
        SELECT created_at, number, route_decision, payload_snippet
        FROM route_logs
        WHERE route_decision LIKE '%audio%'
        ORDER BY created_at DESC
        LIMIT 10
    ''').fetchall()
    if not rows:
        print('Nenhum log de audio encontrado')
    for r in rows:
        snippet = str(r['payload_snippet'] or '')[:200]
        print(f'{r[\"created_at\"]} | {r[\"number\"]} | {r[\"route_decision\"]}')
        try:
            p = json.loads(snippet)
            audio = p.get('inboundAudio') or p.get('audioTranscription') or {}
            print(f'  audioTranscription.reason = {audio.get(\"reason\",\"(nao encontrado)\")}')
            print(f'  audioTranscription.ok      = {audio.get(\"ok\",\"(nao encontrado)\")}')
            ia = p.get('inboundAudio',{})
            has_b64 = bool(ia.get('base64') or ia.get('audioBase64'))
            has_url = bool(ia.get('url') or ia.get('audioUrl'))
            print(f'  inboundAudio.hasBase64     = {has_b64}')
            print(f'  inboundAudio.hasUrl        = {has_url}')
            if has_url:
                url_val = str(ia.get('url') or ia.get('audioUrl',''))[:120]
                print(f'  inboundAudio.url           = {url_val}')
        except:
            print(f'  snippet raw: {snippet[:150]}')
        print()
    con.close()
except Exception as e:
    print(f'ERRO: {type(e).__name__}: {e}')
"@ 2>&1
W $audio_logs
W ""

# ─── SECAO 8: PAYLOAD COMPLETO DO ULTIMO AUDIO ───────────────
W "=== [8] PAYLOAD COMPLETO DO ULTIMO REGISTRO DE AUDIO ===" "Yellow"
$last_audio_payload = docker exec router python3 -c @"
import sqlite3, json, os
db = os.getenv('ROUTER_DB_PATH', '/app/router_runtime.sqlite')
try:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    row = con.execute('''
        SELECT created_at, number, route_decision, payload_snippet
        FROM route_logs
        WHERE route_decision LIKE '%audio%'
        ORDER BY created_at DESC
        LIMIT 1
    ''').fetchone()
    if row:
        print(f'Timestamp: {row[\"created_at\"]}')
        print(f'Number: {row[\"number\"]}')
        print(f'Decision: {row[\"route_decision\"]}')
        try:
            p = json.loads(row['payload_snippet'] or '{}')
            # Mascarar base64 longo
            if 'inboundAudio' in p and p['inboundAudio']:
                ia = p['inboundAudio']
                for k in ('base64','audioBase64'):
                    if ia.get(k):
                        ia[k] = ia[k][:30] + '...[TRUNCADO]'
            print('payload_snippet (inboundAudio + audioTranscription):')
            interesting = {
                'inboundAudio': p.get('inboundAudio'),
                'audioTranscription': p.get('audioTranscription'),
            }
            print(json.dumps(interesting, indent=2, ensure_ascii=False))
        except Exception as je:
            print(f'JSON parse error: {je}')
            print(str(row['payload_snippet'] or '')[:500])
    else:
        print('Nenhum registro de audio encontrado')
    con.close()
except Exception as e:
    print(f'ERRO: {type(e).__name__}: {e}')
"@ 2>&1
W $last_audio_payload
W ""

# ─── SECAO 9: LOGS DO CONTAINER ROUTER (FILTRADOS) ───────────
W "=== [9] LOGS RECENTES DO ROUTER (audio/transcri - ultimas 500 linhas) ===" "Yellow"
$router_logs = docker logs router --tail 500 2>&1 | Select-String -Pattern "audio|transcri|whisper|openai|URLError|HTTPError|transcription_failed|audio_download" -CaseSensitive:$false
if ($router_logs) {
    $router_logs | ForEach-Object { W "  $_" }
} else {
    W "  Nenhuma linha com audio/transcri encontrada nas ultimas 500 linhas de log" "DarkYellow"
}
W ""

# ─── SECAO 10: TESTE DE TRANSCRICAO DIRETO ───────────────────
W "=== [10] TESTE DE TRANSCRICAO COM AUDIO SINTETICO (silencio 1s) ===" "Yellow"
$transcribe_test = docker exec router python3 -c @"
import os, tempfile, wave, struct
from openai import OpenAI

key = os.getenv('OPENAI_API_KEY','')
model = os.getenv('ROUTER_OPENAI_TRANSCRIBE_MODEL','gpt-4o-mini-transcribe')
timeout = int(os.getenv('ROUTER_OPENAI_TRANSCRIBE_TIMEOUT_SECONDS','35'))

if not key:
    print('ERRO: OPENAI_API_KEY nao definida')
else:
    # Cria WAV silencioso de 1 segundo (16kHz mono)
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
            tmp_path = tf.name
            with wave.open(tf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(struct.pack('<' + 'h'*16000, *([0]*16000)))

        client = OpenAI(api_key=key, timeout=timeout)
        with open(tmp_path, 'rb') as fh:
            resp = client.audio.transcriptions.create(
                model=model, file=fh, response_format='json'
            )
        text = getattr(resp, 'text', '') or ''
        print(f'OK modelo={model} texto=\"{text}\" (silencio esperado = texto vazio ou curto)')
    except Exception as e:
        print(f'ERRO: {type(e).__name__}: {str(e)[:300]}')
    finally:
        try: os.unlink(tmp_path)
        except: pass
"@ 2>&1
W "  Resultado: $transcribe_test" $(if ($transcribe_test -match "^OK") { "Green" } else { "Red" })
W ""

# ─── SECAO 11: TESTE DE DOWNLOAD DE URL DE AUDIO ─────────────
W "=== [11] TESTE DE DOWNLOAD DE URL DO ULTIMO AUDIO ===" "Yellow"
$url_test = docker exec router python3 -c @"
import sqlite3, json, os, urllib.request
db = os.getenv('ROUTER_DB_PATH', '/app/router_runtime.sqlite')
try:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    row = con.execute('''
        SELECT payload_snippet FROM route_logs
        WHERE route_decision LIKE '%audio%'
        ORDER BY created_at DESC LIMIT 1
    ''').fetchone()
    if not row:
        print('Sem registro de audio para testar URL')
    else:
        try:
            p = json.loads(row['payload_snippet'] or '{}')
            ia = p.get('inboundAudio') or {}
            url = str(ia.get('url') or ia.get('audioUrl') or '')
            if not url:
                print('inboundAudio.url VAZIO — audio chegou via base64 ou sem url')
                b64 = str(ia.get('base64') or ia.get('audioBase64') or '')
                print(f'base64 presente: {bool(b64)} comprimento: {len(b64)}')
            else:
                print(f'URL: {url[:120]}')
                req = urllib.request.Request(url, headers={'User-Agent':'wa-router/1.0'}, method='GET')
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = r.read(65536)
                    print(f'OK status={r.status} bytes_lidos={len(data)} content-type={r.headers.get(\"Content-Type\")}')
        except json.JSONDecodeError as je:
            print(f'JSON parse error: {je}')
        except Exception as e:
            print(f'ERRO ao baixar URL: {type(e).__name__}: {str(e)[:300]}')
    con.close()
except Exception as e:
    print(f'ERRO DB: {type(e).__name__}: {e}')
"@ 2>&1
W $url_test
W ""

# ─── SECAO 12: VERSAO OPENAI SDK NO CONTAINER ────────────────
W "=== [12] VERSAO openai SDK E PYTHON NO CONTAINER ===" "Yellow"
$py_ver = docker exec router python3 --version 2>&1
$openai_ver = docker exec router python3 -c "import openai; print(openai.__version__)" 2>&1
W "  Python: $py_ver"
W "  openai SDK: $openai_ver"
W ""

# ─── SECAO 13: ENDPOINT /health DO ROUTER ────────────────────
W "=== [13] /health DO ROUTER ===" "Yellow"
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8091/health" -TimeoutSec 5 2>&1
    W "  status: $($health.status)"
    W "  openaiClient: $($health.openaiClient)"
    W "  audioTranscription: $($health.audioTranscription)"
    W "  qdrantStatus: $($health.qdrantStatus)"
    W "  dbPath: $($health.dbPath)"
    W "  Raw: $(ConvertTo-Json $health -Compress)" "DarkGray"
} catch {
    W "  ERRO ao acessar /health: $_" "Red"
}
W ""

# ─── SECAO 14: ENDPOINT /sdr-dashboard-data ──────────────────
W "=== [14] /sdr-dashboard-data _debug.crmError ===" "Yellow"
try {
    $data = Invoke-RestMethod -Uri "http://localhost:8091/sdr-dashboard-data" -TimeoutSec 10 2>&1
    $crmErr = $data._debug.crmError
    if ($crmErr) {
        W "  _debug.crmError: $crmErr" "Red"
    } else {
        W "  _debug.crmError: (sem erro)" "Green"
    }
    W "  totalLeads: $($data.totalLeads)"
    W "  interactionsToday: $($data.interactionsToday)"
} catch {
    W "  ERRO ao acessar /sdr-dashboard-data: $_" "Red"
}
W ""

# ─── SECAO 15: normalize-payload.js — campo inboundAudio ─────
W "=== [15] INSPECAO normalize-payload.js (fonte do inboundAudio) ===" "Yellow"
$norm_path = Join-Path $PSScriptRoot "normalize-payload.js"
if (Test-Path $norm_path) {
    $lines = Get-Content $norm_path | Select-String -Pattern "inboundAudio|audio|base64|mimeType|ptt|hasAudio" -CaseSensitive:$false
    $lines | ForEach-Object { W "  $($_.LineNumber): $($_.Line.Trim())" }
} else {
    W "  normalize-payload.js nao encontrado em $norm_path" "Red"
}
W ""

W "============================================================" "Cyan"
W "DIAGNOSTICO CONCLUIDO — $Ts" "Cyan"
W "Arquivo salvo em: $LogFile" "Green"
W "============================================================" "Cyan"
W ""
W "Para analise rapida, execute:" "White"
W "  Get-Content '$LogFile' | Select-String -Pattern 'ERRO|FAIL|AVISO|OK'" "White"
\n
