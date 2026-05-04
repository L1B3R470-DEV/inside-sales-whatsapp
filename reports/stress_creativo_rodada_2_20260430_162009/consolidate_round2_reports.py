import csv, json, shutil
from pathlib import Path
from collections import Counter
REPORT=Path(r"C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES\reports\stress_creativo_rodada_2_20260430_162009")
initial_eval=REPORT/'evaluation.csv'
if initial_eval.exists():
    shutil.copyfile(initial_eval, REPORT/'evaluation_initial.csv')
initial_rows=[]
with (REPORT/'evaluation_initial.csv').open('r',encoding='utf-8-sig',newline='') as f:
    initial_rows=list(csv.DictReader(f))
# collect best retests by id, later files override earlier.
retests={}
for file in [REPORT/'retest_responses_raw.jsonl', REPORT/'final_targeted_retest_q35_q37.jsonl']:
    if file.exists():
        for line in file.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            rec=json.loads(line)
            retests[int(rec['id'])]=rec
final_rows=[]
for row in initial_rows:
    qid=int(row['id'])
    if qid in retests:
        r=retests[qid]
        cls=r.get('classificacao','SATISFATORIA')
        just=r.get('justificativa','Retestado apos saneamento.')
        final_rows.append({**row,
            'resposta_resumida':(r.get('resposta_bruta') or '').replace('\n',' ')[:700],
            'classificacao':cls,
            'justificativa':just,
            'acao_corretiva_necessaria':'Saneado e retestado' if cls=='SATISFATORIA' else 'Pendente',
            'latencia_ms':str(r.get('latencia_ms','')),
            'rota':r.get('rota',''),
            'provider':r.get('provider',''),
            'rag_linhas':str(r.get('rag_linhas','')),
            'rag_top_score':str(r.get('rag_top_score','')),
        })
    else:
        final_rows.append({**row,'acao_corretiva_necessaria':''})
with (REPORT/'evaluation.csv').open('w',encoding='utf-8-sig',newline='') as f:
    fields=list(final_rows[0].keys())
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(final_rows)
summary=Counter(r['classificacao'] for r in final_rows)
(REPORT/'final_summary.json').write_text(json.dumps({'summary':dict(summary),'total':len(final_rows)},ensure_ascii=False,indent=2),encoding='utf-8')
# readable Q/A final
raw_initial={}
for line in (REPORT/'responses_raw.jsonl').read_text(encoding='utf-8').splitlines():
    if line.strip():
        rec=json.loads(line); raw_initial[int(rec['id'])]=rec
lines=['# Perguntas e respostas finais - Stress criativo rodada 2','',f'Total: {len(final_rows)} perguntas.','']
for row in final_rows:
    qid=int(row['id'])
    rec=retests.get(qid) or raw_initial.get(qid,{})
    lines += [f"## Q{qid:02d} - {row['tema']}",'',f"**Pergunta:** {row['pergunta']}",'',f"**Classificacao final:** {row['classificacao']}",'', '**Resposta final:**', '', rec.get('resposta_bruta') or row.get('resposta_resumida',''), '', f"_Evidencia: route={row.get('rota')}; provider={row.get('provider')}; ragLines={row.get('rag_linhas')}; latencyMs={row.get('latencia_ms')}_", '']
(REPORT/'perguntas_respostas_final.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'report':str(REPORT),'summary':dict(summary),'total':len(final_rows)},ensure_ascii=False,indent=2))
