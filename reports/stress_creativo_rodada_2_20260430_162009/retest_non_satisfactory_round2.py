import ast, csv, json, re, time, urllib.request
from datetime import datetime
from pathlib import Path
REPORT=Path(r"C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES\reports\stress_creativo_rodada_2_20260430_162009")
ROUTE_URL='http://localhost:8091/route'
FAILED_IDS={2,3,4,9,14,15,21,27,31,32,35,36,37,40}
source=(REPORT/'run_stress_round2.py').read_text(encoding='utf-8')
mod=ast.parse(source)
QUESTIONS=[]
for node in mod.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id=='QUESTIONS':
                QUESTIONS=ast.literal_eval(node.value)
QUESTIONS=[q for q in QUESTIONS if q['id'] in FAILED_IDS]
PROHIBITED=[('Classe Couro','nome antigo da marca'),('premium','termo premium proibido'),('Eduardo Silva','consultor incorreto')]
GENDER_RE=re.compile(r'\b(feminina|feminino|femininas|femininos|masculina|masculino|masculinas|masculinos)\b',re.I)
MEIA_OFFER_RE=re.compile(r'\b(podemos|posso|conseguimos|consigo|aceitamos|oferecemos|fazemos|da para fazer|dá para fazer)\b[^.\n]{0,50}\bmeia\s+nota\b',re.I)
def norm(s):
    s=str(s or '').lower(); tr=str.maketrans('áàãâäéèêëíìîïóòõôöúùûüç','aaaaaeeeeiiiiooooouuuuc'); return s.translate(tr)
def variants(r):
    x=norm(r); out={x, x.replace('.', ''), x.replace(',', '.')}
    if x=='30/60/90/120': out.update(['30, 60, 90 e 120','30, 60, 90 ou 120','30 60 90 120'])
    if x=='somente nota cheia': out.update(['somente com nota cheia','apenas nota cheia','trabalhamos somente com nota cheia'])
    if x=='e-commerce': out.update(['ecommerce','site oficial'])
    if x=='pre-cadastro': out.update(['interesse qualificado','cadastro','qualificado'])
    if x=='reclamacao': out.update(['reclamacoes','reclamações','registrar reclama'])
    if x=='continuo': out.update(['continua','contínua','continuo'])
    if x=='personalizado': out.update(['personalizada','personalizado'])
    if x=='garantido': out.update(['garantir','garantia','garantido','certeza'])
    return out
def has_required(reply, req):
    n=norm(reply); flat=n.replace('.','').replace(',','.')
    hits=[]
    for r in req:
        ok=any(v in n or v in flat for v in variants(r))
        hits.append(ok)
    return hits
def classify(q,reply,error):
    if error or not str(reply or '').strip(): return 'NAO_RESPONDEU','Sem resposta util do endpoint.'
    bad=[]
    for term,why in PROHIBITED:
        if term.lower() in reply.lower(): bad.append(why)
    # Ignore gender terms only when they appear as part of quoted/source category labels? For outbound, still flag.
    if GENDER_RE.search(reply): bad.append('produto definido por genero')
    if MEIA_OFFER_RE.search(reply): bad.append('oferta/aceite de meia nota')
    if re.search(r'\blucro\s+garantido\b|\bgarantia\s+de\s+lucro\b', norm(reply)) and not re.search(r'nao|não|sem', norm(reply)[max(0,norm(reply).find('lucro')-30):norm(reply).find('lucro')+60]): bad.append('promessa de lucro garantido')
    if bad: return 'RISCO_COMERCIAL','; '.join(bad)
    hits=has_required(reply,q.get('required',[])); c=sum(hits); total=len(hits)
    if c==total: return 'SATISFATORIA','Atendeu todos os criterios objetivos esperados.'
    if c>=max(1,total-1) and total>=3: return 'PARCIALMENTE_UTIL',f'Faltou parte do criterio esperado: {c}/{total} termos.'
    if c>=1: return 'FRACA',f'Resposta tocou parte do tema, mas faltou informacao essencial: {c}/{total} termos.'
    return 'INSATISFATORIA','Nao recuperou os elementos obrigatorios do material esperado.'
def send(q):
    number=f"5599821{q['id']:04d}"; payload={'number':number,'customerNumber':number,'remoteJid':f'{number}@s.whatsapp.net','pushName':f'Stress R2 Retest Q{q["id"]:02d}','messageId':f'RETEST-R2-{q["id"]:02d}-{int(time.time()*1000)}','inboundText':q['question'],'instance':'ATENDIMENTO_VENDAS_CLEAN'}
    req=urllib.request.Request(ROUTE_URL,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
    start=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=180) as resp:
            obj=json.loads(resp.read().decode('utf-8','replace')); return payload,obj,round((time.perf_counter()-start)*1000),''
    except Exception as e:
        return payload,{},round((time.perf_counter()-start)*1000),f'{type(e).__name__}: {e}'
rows=[]
with (REPORT/'retest_responses_raw.jsonl').open('w',encoding='utf-8') as f:
    for q in QUESTIONS:
        payload,obj,elapsed,error=send(q); reply=obj.get('llmReplyText') or obj.get('cachedReplyText') or ''
        cls,just=classify(q,reply,error)
        evidence={'routeDecision':obj.get('routeDecision',''),'cacheHit':obj.get('cacheHit',False),'ragLinesCount':len(obj.get('ragContextLines') or []),'ragTopScore':obj.get('ragTopScore',0),'llmProvider':obj.get('llmProvider',''),'llmModel':obj.get('llmModel',''),'llmLatencyMs':obj.get('llmLatencyMs',0),'ragContextLines':obj.get('ragContextLines') or []}
        rec={'timestamp':datetime.now().isoformat(timespec='seconds'),'id':q['id'],'tema':q['theme'],'pergunta':q['question'],'payload_enviado':payload,'resposta_bruta':reply,'raw_response':obj,'latencia_ms':elapsed,'erro':error,'rota':evidence['routeDecision'],'evidencia_tecnica':evidence,'classificacao':cls,'justificativa':just,'resposta_ideal_esperada':q['ideal']}
        f.write(json.dumps(rec,ensure_ascii=False)+'\n')
        rows.append({'id':q['id'],'tema':q['theme'],'pergunta':q['question'],'resposta_resumida':reply.replace('\n',' ')[:600],'classificacao':cls,'justificativa':just,'resposta_ideal_esperada':q['ideal'],'latencia_ms':elapsed,'rota':evidence['routeDecision'],'provider':evidence['llmProvider'],'rag_linhas':evidence['ragLinesCount'],'rag_top_score':evidence['ragTopScore']})
        print(f"RETEST Q{q['id']:02d} {cls} route={evidence['routeDecision']} provider={evidence['llmProvider']} ms={elapsed}",flush=True)
with (REPORT/'retest_evaluation.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
summary={}
for r in rows: summary[r['classificacao']]=summary.get(r['classificacao'],0)+1
(REPORT/'retest_summary.json').write_text(json.dumps({'summary':summary,'total':len(rows)},ensure_ascii=False,indent=2),encoding='utf-8')
print('RETEST_SUMMARY',json.dumps(summary,ensure_ascii=False),flush=True)
