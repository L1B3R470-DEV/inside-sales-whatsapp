import json, re, time, urllib.request
from datetime import datetime
from pathlib import Path
REPORT=Path(r"C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES\reports\stress_creativo_rodada_2_20260430_162009")
ROUTE_URL='http://localhost:8091/route'
QUESTIONS=[
 {"id":35,"theme":"Seguranca comercial","question":"Que argumentos objetivos posso usar para ter seguranca em comprar da Classe para revender?","required":["30 anos","suporte","giro"],"ideal":"Citar mais de 30 anos, qualidade/design, rankings de giro e suporte comercial."},
 {"id":37,"theme":"Objecao preco","question":"Antes de passar dados, consigo entender se os valores do book fazem sentido para revenda?","required":["PV","PVL"],"ideal":"Explicar que o book traz PV/PVL e dar exemplo curto, perguntando categoria de interesse."},
]
def norm(s):
    return str(s or '').lower().translate(str.maketrans('áàãâäéèêëíìîïóòõôöúùûüç','aaaaaeeeeiiiiooooouuuuc'))
def classify(q, reply, error):
    if error or not reply.strip(): return 'NAO_RESPONDEU','Sem resposta.'
    bad=[]
    for term in ['Classe Couro','premium','Eduardo Silva']:
        if term.lower() in reply.lower(): bad.append(term)
    if re.search(r'\b(feminina|feminino|femininas|femininos|masculina|masculino|masculinas|masculinos)\b',reply,re.I): bad.append('genero')
    if re.search(r'\b(podemos|posso|conseguimos|consigo|aceitamos|oferecemos|fazemos|da para fazer|dá para fazer)\b[^.\n]{0,50}\bmeia\s+nota\b',reply,re.I): bad.append('meia nota')
    if bad: return 'RISCO_COMERCIAL','; '.join(bad)
    n=norm(reply)
    hits=[]
    for r in q['required']:
        rr=norm(r)
        if rr=='30 anos': hits.append(('30 anos' in n) or ('mais de 30' in n))
        else: hits.append(rr in n)
    if all(hits): return 'SATISFATORIA','Atendeu criterios.'
    return 'INSATISFATORIA',f'Criterios atendidos {sum(hits)}/{len(hits)}.'
def send(q):
    number=f"5599822{q['id']:04d}"; payload={'number':number,'customerNumber':number,'remoteJid':f'{number}@s.whatsapp.net','pushName':f'Stress R2 Final Q{q["id"]:02d}','messageId':f'FINAL-R2-{q["id"]:02d}-{int(time.time()*1000)}','inboundText':q['question'],'instance':'ATENDIMENTO_VENDAS_CLEAN'}
    req=urllib.request.Request(ROUTE_URL,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
    start=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=180) as resp:
            obj=json.loads(resp.read().decode('utf-8','replace')); return payload,obj,round((time.perf_counter()-start)*1000),''
    except Exception as e: return payload,{},round((time.perf_counter()-start)*1000),f'{type(e).__name__}: {e}'
rows=[]
with (REPORT/'final_targeted_retest_q35_q37.jsonl').open('w',encoding='utf-8') as f:
    for q in QUESTIONS:
        payload,obj,elapsed,error=send(q); reply=obj.get('llmReplyText') or obj.get('cachedReplyText') or ''
        cls,just=classify(q,reply,error)
        rec={'timestamp':datetime.now().isoformat(timespec='seconds'),'id':q['id'],'tema':q['theme'],'pergunta':q['question'],'payload_enviado':payload,'resposta_bruta':reply,'latencia_ms':elapsed,'erro':error,'rota':obj.get('routeDecision',''),'provider':obj.get('llmProvider',''),'rag_linhas':len(obj.get('ragContextLines') or []),'rag_top_score':obj.get('ragTopScore',0),'ragContextLines':obj.get('ragContextLines') or [],'classificacao':cls,'justificativa':just,'resposta_ideal_esperada':q['ideal']}
        f.write(json.dumps(rec,ensure_ascii=False)+'\n')
        rows.append(rec)
        print(f"FINAL Q{q['id']} {cls} route={rec['rota']} provider={rec['provider']} ms={elapsed}")
(REPORT/'final_targeted_retest_q35_q37_summary.json').write_text(json.dumps({'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
