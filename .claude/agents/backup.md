Faça backup dos dados e configurações críticas do Atendente Inside Sales.

Diretório de backup: `C:\AUTOMACAO\backups\` (crie se não existir, com subpasta da data)

O que fazer backup:
1. **Bancos SQLite** (CRÍTICO):
   - `crm_operacional.sqlite` — CRM com todos os leads
   - `router_runtime.sqlite` — estados e cache do router
   Use `sqlite3 DB ".backup DESTINO"` para backup consistente (não copie arquivo direto se estiver em uso)

2. **Configurações**:
   - `docker-compose.yml`
   - `guardrails.js`
   - `.env` (se existir)

3. **RAG/Cache**:
   - `rag_vector_store/`
   - `reference_patterns_cache/`
   - `product_media_catalog_snapshot.json`
   - `sales_book_asset_snapshot.json`

Nomeie a pasta de backup com data: `backup_YYYY-MM-DD_HHmm`
No final, liste o que foi salvo com tamanhos e confirme integridade.
