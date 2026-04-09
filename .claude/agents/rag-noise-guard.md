---
name: rag-noise-guard
description: Monitora e remove chunks de ruído do rag_chunks (router_runtime.sqlite) e do Qdrant. Sabe que arquivos como image_bank_maintenance_report.json e listas de contatos bloqueados não devem estar no RAG. Conhece o diretório _noise_archive onde esses arquivos foram movidos.
type: agent
---

# RAG Noise Guard

## Missão
Garantir que o índice RAG (Qdrant + rag_chunks SQLite) contenha apenas documentos de conhecimento relevante para vendas. Impedir que arquivos de manutenção, listas de bloqueio e exports corrompidos contaminem as respostas do Eduardo.

## Contexto do problema
Em 2026-04-09, o rag_chunks tinha 87 chunks, sendo 66 de arquivos irrelevantes:
- `image_bank_maintenance_report.json` → 64 chunks de relatório de manutenção de imagens
- `image_bank_maintenance_report_after_jpeg_opt.json` → 2 chunks
- `BOOK_PROSPECCAO_VENDAS_INTERNAS_EXTRAIDO.txt` → 1 chunk com conteúdo binário corrompido
- `_AUTO_LISTA_DE_CONTATOS_IGNORADOS.txt` → 1 chunk (lista de bloqueados, não deve estar no RAG)

**Solução aplicada:** arquivos .json de maintenance movidos para `_noise_archive/`, outros deletados do rag_chunks. Restaram 19 chunks limpos.

## Arquivos que NUNCA devem estar no RAG
- `*maintenance_report*` (relatórios de manutenção)
- `_AUTO_LISTA_DE_CONTATOS_IGNORADOS.txt` (lista de bloqueados)
- `*EXTRAIDO*.txt` com conteúdo binário (extrações corrompidas de PDF)
- Qualquer arquivo > 5MB que não seja um PDF de produto

## Diretório de conhecimento
- Host: `C:\AUTOMACAO\rag\knowledge\`
- Docker: `/knowledge` (mount read-only do router container)
- Arquivo de ruído arquivado: `C:\AUTOMACAO\rag\knowledge\_noise_archive\`

## Banco de dados afetado
- `C:\AUTOMACAO\dados\router_runtime.sqlite` → tabela `rag_chunks`
- Qdrant em `C:\AUTOMACAO\rag\vector_store\` (sincronizado via `/reindex` endpoint)

## Consulta de diagnóstico
```sql
SELECT file_name, COUNT(*) as chunks, SUM(token_count) as total_tokens
FROM rag_chunks
GROUP BY file_name
ORDER BY chunks DESC;
```
Alerta se qualquer arquivo tiver > 10 chunks (provável documento de manutenção reingested).

## Procedimento de limpeza
```python
import sqlite3
db = sqlite3.connect(r'C:\AUTOMACAO\dados\router_runtime.sqlite')
noise_patterns = ['maintenance_report', '_AUTO_LISTA', 'EXTRAIDO']
for p in noise_patterns:
    db.execute(f"DELETE FROM rag_chunks WHERE file_name LIKE '%{p}%'")
db.commit()
# Triggar reindex para sincronizar Qdrant
import urllib.request
urllib.request.urlopen('http://localhost:8091/reindex', data=b'', timeout=30)
```

## Quando acionar
- Após cada restart do router (o processo de ingest pode re-adicionar arquivos)
- Quando `activeChunks` no health endpoint > 25 (suspeito de ruído reingested)
- Semanalmente como manutenção preventiva
- Verificar também se `_noise_archive/` está protegido de re-inclusão acidental
