from pathlib import Path
import os
project = Path(r"C:\Users\User\Desktop\PROJETO ATENDIMENTO WHATSAPP INSIDE SALES")
runtime = Path(r"C:\AUTOMACAO")
env_file = project / '.env'
for line in env_file.read_text(encoding='utf-8', errors='ignore').splitlines():
    if not line or line.strip().startswith('#') or '=' not in line:
        continue
    k,v = line.split('=',1)
    os.environ[k.strip()] = v.strip()
os.environ['AUTOMACAO_ROOT'] = str(runtime)
os.environ['ROUTER_ML_DIR'] = str(runtime / 'rag' / 'knowledge')
os.environ['ROUTER_DB_PATH'] = str(runtime / 'dados' / 'router_runtime.sqlite')
os.environ['ROUTER_QDRANT_PATH'] = str(runtime / 'rag' / 'vector_store')
os.environ['ROUTER_QDRANT_COLLECTION'] = 'knowledge_chunks'
os.environ['ROUTER_OPENAI_EMBED_MODEL'] = 'text-embedding-3-small'
os.environ['ROUTER_WATCH_INTERVAL_SECONDS'] = '900'
import router_service
import multi_llm
router_service.validate_topology()
router_service.log.info('attendant_topology_registered', **router_service.topology_metadata())
multi_llm.ensure_topology_logged()
from waitress import serve
serve(router_service.app, host='0.0.0.0', port=8092, threads=8)
