# Corrections log - Stress criativo rodada 2

## Resumo da primeira bateria

- Total testado: 40
- SATISFATORIA: 26
- PARCIALMENTE_UTIL: 3
- FRACA: 5
- INSATISFATORIA: 6

## Correcoes permanentes aplicadas

1. \nouter_service.py
- Ampliados gatilhos de RAG para SAC, pagamento, prazo, nota fiscal, B2B, estoque, seguranca, PV/PVL e markup.
- Ajustado uild_rag_snippet para priorizar termos especificos como kits, CTF396, CF165, portal B2B, valores, seguranca, PV/PVL e nota fiscal.
- Adicionado 	argeted_commercial_rules_hits para forcar documentos comerciais criticos no contexto.
- Adicionado recorte de secoes em select_commercial_rules_section para evitar que perguntas de valores/seguranca pegassem trecho errado de documento grande.
- Adicionado saneamento para impedir oferta/aceite de meia nota.

2. sdr_prompt.txt
- Incluidas regras de SAC, pagamento, prazo, suporte, markup, nota cheia, B2B, PV/PVL exato e estoque inicial.

3. Base de conhecimento RAG
- Criado REGRAS_COMERCIAIS_CRITICAS_INSIDE_SALES_CLASSE.md.
- Criado REGRAS_COMERCIAIS_COMPLEMENTARES_RODADA2_CLASSE.md para complementar secoes que estavam fora do primeiro chunk indexado.

## Casos corrigidos e retestados

- Q21 CTF396: causa era leitura incorreta de PV; corrigido com regra de copiar PV/PVL exatamente e referencias complementares. Reteste: SATISFATORIA.
- Q27 Kits: causa era snippet iniciando no topo do ranking e nao na secao de kits; corrigido com priorizacao de termos e referencias complementares. Reteste: SATISFATORIA.
- Q31 B2B: causa era ausencia do conhecimento no RAG ativo; corrigido com regra login=CNPJ e senha=8 primeiros digitos. Reteste: SATISFATORIA.
- Q35 Seguranca comercial: causa era omissao de mais de 30 anos/design/ranking de giro; corrigido com documento complementar e recorte por secao. Reteste final: SATISFATORIA.
- Q36 Estoque inicial: causa era resposta que perguntava antes de sugerir categorias; corrigido com regra de responder primeiro com categorias. Reteste: SATISFATORIA.
- Q37 Valores do book antes de dados: causa era resposta generica de markup sem PV/PVL; corrigido com documento complementar e recorte por secao. Reteste final: SATISFATORIA.
- Q2/Q3/Q4/Q9/Q14/Q15/Q32/Q40: respostas iniciais eram operacionalmente boas, mas foram retestadas apos ajustes de criterio/contexto e ficaram SATISFATORIA.

## Resultado final apos saneamento

- SATISFATORIA: 40
- Total: 40\n\n
