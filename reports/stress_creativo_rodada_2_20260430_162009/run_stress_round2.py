import csv, json, re, time, urllib.request
from datetime import datetime
from pathlib import Path

REPORT = Path(r"C:\Users\User\Desktop\CODEX_PROJECTS\PROJETO_ATENDIMENTO_WHATSAPP_INSIDE_SALES\reports\stress_creativo_rodada_2_20260430_162009")
ROUTE_URL = "http://localhost:8091/route"
QUESTIONS = [
  {"id":1,"theme":"SAC e defeito","question":"Se um produto chegar com defeito, como funciona o SAC da Classe?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar fluxo de SAC, fotos, fabrica e PIX.","required":["SAC","fotos","fabrica","PIX","100%"],"ideal":"Explicar SAC exclusivo: cliente envia fotos, produto vai para fabrica se houver indicio, confirmado defeito retorna 100% do item via PIX."},
  {"id":2,"theme":"Reclamacao","question":"O cliente consegue registrar reclamacao por um canal de SAC personalizado?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar existencia de SAC exclusivo/personalizado.","required":["SAC","exclusivo","personalizado","reclamacao"],"ideal":"Sim, a Classe possui SAC exclusivo e personalizado para registrar reclamacao e tratar o caso."},
  {"id":3,"theme":"Pagamento","question":"Quais sao as formas de pagamento para pedido de revenda?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar boleto e cartao.","required":["30/60/90/120","6x","sem juros"],"ideal":"Boleto em 30/60/90/120 e cartao em ate 6x sem juros."},
  {"id":4,"theme":"Pagamento boleto","question":"No boleto, consigo prazo em 30, 60, 90 e 120 dias?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar boleto 30/60/90/120.","required":["30/60/90/120","boleto"],"ideal":"Sim, boleto em 30/60/90/120."},
  {"id":5,"theme":"Pagamento cartao","question":"Cartao parcela em quantas vezes sem juros?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar cartao 6x sem juros.","required":["6x","sem juros","cartao"],"ideal":"Cartao em ate 6x sem juros."},
  {"id":6,"theme":"Prazo envio","question":"Qual e o prazo de envio para pronta entrega e para producao?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar prazos distintos.","required":["10 a 15 dias","30 dias","pronta entrega","producao"],"ideal":"Pronta entrega: 10 a 15 dias. Producao: 30 dias."},
  {"id":7,"theme":"Pronta entrega","question":"Se tiver pronta entrega, em quanto tempo o pedido costuma ser enviado?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar pronta entrega.","required":["10 a 15 dias","pronta entrega"],"ideal":"Pronta entrega de 10 a 15 dias."},
  {"id":8,"theme":"Producao","question":"Quando o item entra em producao, qual prazo devo considerar?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar prazo producao.","required":["30 dias","producao"],"ideal":"Producao em 30 dias."},
  {"id":9,"theme":"Suporte comercial","question":"Depois que eu comprar, a Classe ajuda a escolher mix e vender melhor?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar suporte comercial continuo.","required":["suporte comercial","continuo","personalizado","mix"],"ideal":"Sim, suporte comercial continuo e personalizado para ajudar em mix, estoque e vendas."},
  {"id":10,"theme":"Lucratividade sem investimento","question":"Consigo simular retorno sem ainda saber quanto vou investir?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar que investiga investimento antes de simular.","required":["investimento","simular","2,3"],"ideal":"Dizer que pode simular conforme investimento pretendido e perguntar o valor inicial; citar multiplicador 2,3 sem prometer lucro."},
  {"id":11,"theme":"Lucratividade 2000","question":"Se eu investir R$ 2.000, qual potencial bruto de venda usando o markup da Classe?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar markup 2,3 e exemplo 4600.","required":["2,3","4.600"],"ideal":"Com multiplicador 2,3, R$ 2.000 pode representar cerca de R$ 4.600 de venda bruta, sem lucro garantido."},
  {"id":12,"theme":"Lucratividade 4000","question":"Com R$ 4.000 de pedido inicial, qual seria um exemplo de retorno bruto pelo multiplicador 2,3?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar exemplo 9200.","required":["2,3","9.200"],"ideal":"R$ 4.000 x 2,3 = potencial bruto em torno de R$ 9.200, antes de custos e sem garantia."},
  {"id":13,"theme":"Lucratividade 6000","question":"Um pedido de R$ 6.000 pode virar quanto em venda bruta estimada no multiplicador comercial?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar exemplo 13800.","required":["2,3","13.800"],"ideal":"R$ 6.000 x 2,3 = cerca de R$ 13.800 de potencial bruto, sem promessa de lucro garantido."},
  {"id":14,"theme":"Nota fiscal","question":"A Classe emite meia nota ou somente nota cheia nesse canal?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar regra nota cheia.","required":["somente nota cheia"],"ideal":"Somente nota cheia; meia nota nao e oferecida nem aceita."},
  {"id":15,"theme":"Meia nota","question":"Para fechar melhor, da para fazer meia nota?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar recusa comercial segura.","required":["somente nota cheia"],"ideal":"Nao. Trabalhamos somente com nota cheia e seguimos com o pedido regular."},
  {"id":16,"theme":"Material","question":"Todos os produtos sao de couro legitimo?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar nao prometer couro legitimo genericamente.","required":["composicao","referencia"],"ideal":"Nao prometer genericamente; confirmar composicao por referencia/modelo e falar em qualidade."},
  {"id":17,"theme":"Marca","question":"A Classe existe ha quanto tempo e qual e o principal diferencial da marca?","source":"SOBRE A MARCA - CLASSE COURO.docx","objective":"Validar historia e diferencial.","required":["30 anos","design","qualidade"],"ideal":"Mais de 30 anos, combinando design e qualidade produtiva."},
  {"id":18,"theme":"Book HIT","question":"No book, qual e o PV e PVL do modelo HIT 3466?","source":"BOOK_PROSPECCAO_VENDAS_INTERNAS_EXTRAIDO_PYPDF.txt","objective":"Validar PV/PVL HIT.","required":["134,80","309,90"],"ideal":"HIT 3466 PV R$134,80 e PVL R$309,90."},
  {"id":19,"theme":"Book SOFIA","question":"Qual e o PV e PVL da SOFIA 2846/2 Camera Bag?","source":"BOOK_PROSPECCAO_VENDAS_INTERNAS_EXTRAIDO_PYPDF.txt","objective":"Validar PV/PVL SOFIA.","required":["217,80","499,90"],"ideal":"SOFIA 2846/2 PV R$217,80 e PVL R$499,90."},
  {"id":20,"theme":"Book BECCA","question":"Qual e o PV e PVL da BECCA 3476 Camera Bag?","source":"BOOK_PROSPECCAO_VENDAS_INTERNAS_EXTRAIDO_PYPDF.txt","objective":"Validar PV/PVL BECCA.","required":["169,80","389,90"],"ideal":"BECCA 3476 PV R$169,80 e PVL R$389,90."},
  {"id":21,"theme":"Book carteira","question":"No book, a CTF396 carteira aparece com quais valores de PV e PVL?","source":"BOOK_PROSPECCAO_VENDAS_INTERNAS_EXTRAIDO_PYPDF.txt","objective":"Validar CTF396.","required":["69,40","159,90"],"ideal":"CTF396 PV R$69,40 e PVL R$159,90."},
  {"id":22,"theme":"Book cinto","question":"Qual PV e PVL aparecem para o cinto CF165?","source":"BOOK_PROSPECCAO_VENDAS_INTERNAS_EXTRAIDO_PYPDF.txt","objective":"Validar CF165.","required":["27,80","62,90"],"ideal":"CF165 PV R$27,80 e PVL R$62,90."},
  {"id":23,"theme":"Ranking bolsa","question":"Qual referencia lidera o ranking de bolsas no Inverno 26?","source":"RANKING_COMERCIAL_TOP10_INVERNO_26.txt","objective":"Validar 3262.","required":["3262","8729"],"ideal":"3262 Crossbody lidera com 8729."},
  {"id":24,"theme":"Ranking cintos","question":"Quais sao os dois cintos de maior giro no ranking por categoria?","source":"RANKING_COMERCIAL_TOP10_INVERNO_26.txt","objective":"Validar CF165/CF166 ou CM40/CM97 conforme categoria citada.","required":["CF165","CF166"],"ideal":"Para cintos da lista principal, CF165 e CF166 aparecem no topo; se considerar outra linha, explicar CM40/CM97."},
  {"id":25,"theme":"Ranking carteiras","question":"Qual referencia aparece como destaque em carteiras no ranking por categoria?","source":"RANKING_COMERCIAL_TOP10_INVERNO_26.txt","objective":"Validar 040-0 e/ou CTF217 conforme linha.","required":["040-0","2702"],"ideal":"040-0 casual lidera carteiras no ranking com 2702; pode citar CTF217 em outra linha."},
  {"id":26,"theme":"Ranking acessorios","question":"Qual item lidera o ranking de acessorios?","source":"RANKING_COMERCIAL_TOP10_INVERNO_26.txt","objective":"Validar PM48.","required":["PM48","1459"],"ideal":"PM48 lidera acessorios com 1459."},
  {"id":27,"theme":"Ranking kits","question":"Qual kit aparece como destaque no ranking comercial?","source":"RANKING_COMERCIAL_TOP10_INVERNO_26.txt","objective":"Validar KIT02 173.","required":["KIT02","173","747"],"ideal":"KIT02 173 aparece em destaque com 747."},
  {"id":28,"theme":"Mix 2000","question":"Para pedido inicial de R$ 2.000, que tipo de mix o material sugere?","source":"SUGESTAO_PEDIDO_2000_*.pdf","objective":"Validar sugestao 2000.","required":["2.000","mix"],"ideal":"Explicar opcoes de mix para R$2.000 sem rotulo de genero e perguntar perfil/categoria."},
  {"id":29,"theme":"Mix 4000","question":"Para um pedido inicial de R$ 4.000, que mix posso considerar?","source":"SUGESTAO_PEDIDO_4000_*.pdf","objective":"Validar sugestao 4000.","required":["4.000","mix"],"ideal":"Explicar mix de R$4.000 com produtos/categorias do material."},
  {"id":30,"theme":"Mix 6000","question":"Para R$ 6.000 de investimento inicial, que composicao de estoque o material indica?","source":"SUGESTAO_PEDIDO_6000_*.pdf","objective":"Validar sugestao 6000.","required":["6.000","estoque"],"ideal":"Explicar composicao de estoque de R$6.000 baseada no material."},
  {"id":31,"theme":"B2B acesso","question":"Depois que o cadastro estiver liberado, como funcionam login e senha do portal B2B?","source":"CURRENT_STATE.md / UPDATE_AGENT_240326-1100.txt","objective":"Validar login CNPJ e senha 8 digitos.","required":["CNPJ","8 primeiros"],"ideal":"Login e o CNPJ completo; senha sao os 8 primeiros digitos do CNPJ."},
  {"id":32,"theme":"Book envio","question":"Quando faz sentido enviar o book de vendas para o lead?","source":"SCRIPT_APRESENTACAO_BOOK_DE_VENDAS.txt","objective":"Validar book apos triagem/cadastro.","required":["pre-cadastro","book"],"ideal":"Apos pre-cadastro/validacao, enviar o book como proximo passo de analise comercial."},
  {"id":33,"theme":"Vitrine","question":"A vitrine de pedido inicial deve ser enviada automaticamente ou preciso pedir anuencia?","source":"UPDATE_AGENT_240326-1100.txt","objective":"Validar anuencia expressa para vitrine.","required":["anuencia","expressa"],"ideal":"Precisa de anuencia expressa do lead antes de enviar."},
  {"id":34,"theme":"Pessoa fisica","question":"Se uma pessoa quer comprar uma unidade para uso proprio nesse canal, qual direcionamento correto?","source":"DIRECIONAMENTO_CLIENTE_PF_NO_CANAL_DE_REVENDA.txt","objective":"Validar PF para ecommerce.","required":["pessoa fisica","e-commerce"],"ideal":"Direcionar com simpatia para o e-commerce oficial; canal e para revenda."},
  {"id":35,"theme":"Seguranca comercial","question":"Que argumentos objetivos posso usar para ter seguranca em comprar da Classe para revender?","source":"SOBRE A MARCA / rankings / suporte","objective":"Validar argumentos comerciais reais.","required":["30 anos","suporte","giro"],"ideal":"Citar mais de 30 anos, qualidade/design, rankings de giro e suporte comercial."},
  {"id":36,"theme":"Estoque inicial","question":"Quero um estoque inicial com giro. Quais categorias fazem sentido combinar?","source":"RANKING_COMERCIAL_TOP10_INVERNO_26.txt / sugestoes de pedido","objective":"Validar combinacao de categorias.","required":["bolsas","carteiras","cintos"],"ideal":"Combinar bolsas/crossbody com carteiras, cintos e acessorios de giro."},
  {"id":37,"theme":"Objecao preco","question":"Antes de passar dados, consigo entender se os valores do book fazem sentido para revenda?","source":"BOOK_PROSPECCAO_VENDAS_INTERNAS_EXTRAIDO_PYPDF.txt","objective":"Validar resposta com PV/PVL e proximo passo sem exigir CNPJ.","required":["PV","PVL"],"ideal":"Explicar que o book traz PV/PVL e dar exemplo curto, perguntando categoria de interesse."},
  {"id":38,"theme":"Mix e suporte","question":"Se eu nao souber montar o primeiro pedido, a Classe ajuda a escolher produtos de melhor giro?","source":"REGRAS_COMERCIAIS_CRITICAS / rankings","objective":"Validar suporte + ranking.","required":["suporte","giro","mix"],"ideal":"Sim, suporte ajuda a montar mix com base em perfil, investimento e produtos de giro."},
  {"id":39,"theme":"Defeito e reembolso","question":"Se a fabrica confirmar defeito, recebo credito ou PIX?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar PIX 100% item.","required":["PIX","100%"],"ideal":"Confirmado defeito, 100% do valor daquele item retorna via PIX."},
  {"id":40,"theme":"Sem lucro garantido","question":"Posso contar que vou lucrar com certeza usando o markup 2,3?","source":"REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md","objective":"Validar nao prometer lucro garantido.","required":["nao","garantido","2,3"],"ideal":"Nao prometer lucro garantido; usar 2,3 como potencial bruto e considerar custos/giro."},
]
PROHIBITED = [("Classe Couro", "nome antigo da marca"),("premium", "termo premium proibido"),("Eduardo Silva", "consultor incorreto")]
GENDER_RE = re.compile(r"\b(feminina|feminino|femininas|femininos|masculina|masculino|masculinas|masculinos)\b", re.I)
MEIA_OFFER_RE = re.compile(r"\b(podemos|posso|conseguimos|consigo|aceitamos|oferecemos|fazemos|da para fazer|dá para fazer)\b[^.\n]{0,50}\bmeia\s+nota\b", re.I)

def norm(s):
    s = str(s or '').lower(); tr = str.maketrans('áàãâäéèêëíìîïóòõôöúùûüç', 'aaaaaeeeeiiiiooooouuuuc'); return s.translate(tr)

def has_required(reply, req):
    n = norm(reply); flat = n.replace('.', '').replace(',', '.')
    hits=[]
    for r in req:
        rr=norm(r); ok = rr in n or rr.replace('.', '') in n.replace('.', '') or rr.replace(',', '.') in flat
        hits.append(ok)
    return hits

def classify(q, reply, error):
    if error or not str(reply or '').strip(): return 'NAO_RESPONDEU', 'Sem resposta util do endpoint.'
    bad=[]
    for term, why in PROHIBITED:
        if term.lower() in reply.lower(): bad.append(why)
    if GENDER_RE.search(reply): bad.append('produto definido por genero')
    if MEIA_OFFER_RE.search(reply): bad.append('oferta/aceite de meia nota')
    if re.search(r'\blucro\s+garantido\b|\bgarantia\s+de\s+lucro\b', norm(reply)) and q['id'] in {10,11,12,13,40}: bad.append('promessa de lucro garantido')
    if bad: return 'RISCO_COMERCIAL', '; '.join(bad)
    hits=has_required(reply, q.get('required', [])); c=sum(hits); total=len(hits)
    if c == total: return 'SATISFATORIA', 'Atendeu todos os criterios objetivos esperados.'
    if c >= max(1, total-1) and total >= 3: return 'PARCIALMENTE_UTIL', f'Faltou parte do criterio esperado: {c}/{total} termos.'
    if c >= 1: return 'FRACA', f'Resposta tocou parte do tema, mas faltou informacao essencial: {c}/{total} termos.'
    return 'INSATISFATORIA', 'Nao recuperou os elementos obrigatorios do material esperado.'

def send_question(q):
    number = f"5599820{q['id']:04d}"
    payload = {"number": number,"customerNumber": number,"remoteJid": f"{number}@s.whatsapp.net","pushName": f"Stress Rodada2 Q{q['id']:02d}","messageId": f"STRESS-R2-{q['id']:02d}-{int(time.time()*1000)}","inboundText": q['question'],"instance":"ATENDIMENTO_VENDAS_CLEAN"}
    data=json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(ROUTE_URL, data=data, headers={'Content-Type':'application/json; charset=utf-8'}, method='POST')
    started=time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw=resp.read().decode('utf-8', errors='replace'); elapsed=round((time.perf_counter()-started)*1000); obj=json.loads(raw); return payload,obj,raw,elapsed,''
    except Exception as e:
        elapsed=round((time.perf_counter()-started)*1000); return payload,{},'',elapsed,f'{type(e).__name__}: {e}'
REPORT.mkdir(parents=True, exist_ok=True)
with (REPORT/'questions.csv').open('w', newline='', encoding='utf-8-sig') as f:
    w=csv.DictWriter(f, fieldnames=['id','tema','pergunta','fonte_esperada','objetivo']); w.writeheader(); [w.writerow({'id':q['id'],'tema':q['theme'],'pergunta':q['question'],'fonte_esperada':q['source'],'objetivo':q['objective']}) for q in QUESTIONS]
raw_path=REPORT/'responses_raw.jsonl'; eval_rows=[]
with raw_path.open('w', encoding='utf-8') as rawf:
    for q in QUESTIONS:
        payload,obj,raw,elapsed,error=send_question(q); reply=obj.get('llmReplyText') or obj.get('cachedReplyText') or obj.get('replyText') or ''
        classification,justification=classify(q,reply,error)
        evidence={'routeDecision':obj.get('routeDecision',''),'cacheHit':obj.get('cacheHit',False),'ragLinesCount':len(obj.get('ragContextLines') or []),'ragTopScore':obj.get('ragTopScore',0),'llmProvider':obj.get('llmProvider',''),'llmModel':obj.get('llmModel',''),'llmLatencyMs':obj.get('llmLatencyMs',0),'ragContextLines':obj.get('ragContextLines') or []}
        rec={'timestamp':datetime.now().isoformat(timespec='seconds'),'id':q['id'],'tema':q['theme'],'pergunta':q['question'],'payload_enviado':payload,'resposta_bruta':reply,'raw_response':obj,'latencia_ms':elapsed,'erro':error,'rota':evidence.get('routeDecision'),'evidencia_tecnica':evidence}
        rawf.write(json.dumps(rec, ensure_ascii=False)+'\n')
        eval_rows.append({'id':q['id'],'tema':q['theme'],'pergunta':q['question'],'resposta_resumida':reply.replace('\n',' ')[:500],'classificacao':classification,'justificativa':justification,'resposta_ideal_esperada':q['ideal'],'acao_corretiva_necessaria':'' if classification=='SATISFATORIA' else 'Investigar/corrigir e retestar','latencia_ms':elapsed,'rota':evidence.get('routeDecision'),'provider':evidence.get('llmProvider'),'rag_linhas':evidence.get('ragLinesCount'),'rag_top_score':evidence.get('ragTopScore')})
        print(f"Q{q['id']:02d} {classification} route={evidence.get('routeDecision')} provider={evidence.get('llmProvider')} ms={elapsed}", flush=True)
with (REPORT/'evaluation.csv').open('w', newline='', encoding='utf-8-sig') as f:
    fields=list(eval_rows[0].keys()); w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(eval_rows)
summary={}
for r in eval_rows: summary[r['classificacao']]=summary.get(r['classificacao'],0)+1
(REPORT/'initial_summary.json').write_text(json.dumps({'summary':summary,'total':len(eval_rows)}, ensure_ascii=False, indent=2), encoding='utf-8')
print('SUMMARY', json.dumps(summary, ensure_ascii=False), flush=True)
