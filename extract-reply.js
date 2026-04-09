const response = $json;
const guardrails = $node['Guardrails'].json;

const fallbackBusy = 'Aqui e o Eduardo, Consultor de Vendas Internas da Classe Couro. Seu atendimento ja esta em prioridade. Me diga qual produto voce precisa para eu adiantar seu atendimento.';
const fallbackWaiting = 'Aqui e o Eduardo, Consultor de Vendas Internas da Classe Couro. Recebi sua mensagem e vou te atender pessoalmente em instantes. Para agilizar, me diga qual produto voce precisa e a quantidade desejada.';

function extractRawText(apiResponse) {
  let text = apiResponse?.output_text ?? '';
  if (!text && Array.isArray(apiResponse?.output)) {
    text = apiResponse.output
      .flatMap((item) => item?.content ?? [])
      .map((part) => part?.text ?? '')
      .filter(Boolean)
      .join('\n')
      .trim();
  }
  return String(text || '').trim();
}

function extractResponseId(apiResponse) {
  const id = String(apiResponse?.id || '').trim();
  return id || '';
}

function parseModelJson(raw) {
  if (!raw) return null;
  const tryParse = (value) => {
    try { return JSON.parse(value); } catch { return null; }
  };

  let parsed = tryParse(raw);
  if (parsed) return parsed;

  const start = raw.indexOf('{');
  const end = raw.lastIndexOf('}');
  if (start >= 0 && end > start) {
    parsed = tryParse(raw.slice(start, end + 1));
    if (parsed) return parsed;
  }

  return null;
}

function clampConfidence(value, fallback) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

function toFirstName(value) {
  return String(value || '').trim().split(/\s+/).filter(Boolean)[0] || '';
}

function getHourInTimezone(timeZone) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: String(timeZone || 'America/Bahia'),
    hour: '2-digit',
    hour12: false
  }).formatToParts(new Date());
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  return Number(p.hour || '0');
}

function getGreetingByHour(hour) {
  const h = Number(hour || 0);
  if (h >= 5 && h <= 11) return 'bom dia';
  if (h >= 12 && h <= 17) return 'boa tarde';
  return 'boa noite';
}

function capitalize(text) {
  const t = String(text || '').trim();
  if (!t) return '';
  return t.charAt(0).toUpperCase() + t.slice(1);
}

function stripLeadingSalutation(text) {
  let out = String(text || '').trim();
  if (!out) return '';

  out = out.replace(/^(?:oi|ola|olá)\s+[^\n,!.:?]{1,40}\s*[,!:\-]\s*/i, '');
  out = out.replace(/^(?:oi|ola|olá)\s*[,!:\-]\s*/i, '');
  out = out.replace(/^(?:bom dia|boa tarde|boa noite|meia noite)\s+[^\n,!.:?]{1,40}\s*[,!:\-]\s*/i, '');
  out = out.replace(/^(?:bom dia|boa tarde|boa noite|meia noite)\s*[,!:\-]\s*/i, '');

  return out.trim();
}

function hasGreetingCue(text) {
  const norm = normalizeForDedupe(text);
  return ['bom dia', 'boa tarde', 'boa noite', 'ola', 'olá', 'oi'].some((k) => norm.includes(k));
}

function composeSalutation(number, customerName, workTimezone, isFirstInbound, cadence) {
  const greeting = capitalize(getGreetingByHour(getHourInTimezone(workTimezone)));
  const firstName = toFirstName(customerName);
  if (!number || !firstName) return `${greeting}!`;

  const nowMs = Date.now();
  const minutesSinceNamed = (nowMs - Number(cadence.lastNamedAt || 0)) / 60000;
  const useName = Boolean(isFirstInbound) || Number(cadence.count || 0) <= 1 || (Number(cadence.count || 0) % 4 === 0) || minutesSinceNamed >= 90;
  return useName ? `${greeting}, ${firstName}!` : `${greeting}!`;
}

function applySalutation(replyText, ctx) {
  if (Boolean(ctx?.skipAutomaticSalutation)) {
    return String(replyText || '').replace(/\s+/g, ' ').trim();
  }
  const body = stripLeadingSalutation(replyText);
  const firstName = toFirstName(String(ctx?.customerName || ''));
  const earlyBody = normalizeForDedupe(String(body || '').slice(0, 120));
  const hasEarlyNameMention = Boolean(firstName) && earlyBody.includes(normalizeForDedupe(firstName));
  const startsWithCommercialLead = /^(perfeito|certo|entendi|otimo|ótimo|seu pre-cadastro|estou te enviando|para te ajudar)/i.test(String(body || ''));
  const number = String(ctx?.number || '').replace(/\D/g, '');
  if (!number) return body;

  const staticData = $getWorkflowStaticData('global');
  if (!staticData.salutationCadence) staticData.salutationCadence = {};

  const nowMs = Date.now();
  const cadence = staticData.salutationCadence[number] || {
    count: 0,
    lastNamedAt: 0,
    lastSalutedAt: 0,
    updatedAt: 0
  };

  const minutesSinceSalutation = (nowMs - Number(cadence.lastSalutedAt || 0)) / 60000;
  const greetedByCustomer = hasGreetingCue(String(ctx?.inboundText || ''));
  const shouldSalute = Boolean(ctx?.isFirstInbound) ||
    Number(cadence.lastSalutedAt || 0) === 0 ||
    minutesSinceSalutation >= 60 ||
    (greetedByCustomer && minutesSinceSalutation >= 25);

  let finalText = body;
  cadence.count = Number(cadence.count || 0) + 1;

  if (shouldSalute && !(hasEarlyNameMention && startsWithCommercialLead)) {
    const prefix = composeSalutation(
      number,
      hasEarlyNameMention ? '' : String(ctx?.customerName || ''),
      String(ctx?.workTimezone || 'America/Bahia'),
      Boolean(ctx?.isFirstInbound),
      cadence
    );
    finalText = body ? `${prefix} ${body}` : prefix;
    cadence.lastSalutedAt = nowMs;
    if (String(prefix).includes(',')) cadence.lastNamedAt = nowMs;
  }

  cadence.updatedAt = nowMs;
  staticData.salutationCadence[number] = cadence;
  return String(finalText || '').replace(/\s+/g, ' ').trim();
}

function normalizeForDedupe(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

function stripEmojiCharacters(value) {
  return String(value || '')
    .replace(/\u200D/g, '')
    .replace(/\uFE0F/g, '')
    .replace(/\p{Extended_Pictographic}/gu, '')
    .replace(/[\u{1F300}-\u{1FAFF}]/gu, '')
    .replace(/[\u{2600}-\u{27BF}]/gu, '')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

function normalizeAuthorizedLink(value) {
  return String(value || '')
    .trim()
    .replace(/^<+|>+$/g, '')
    .replace(/[),.;!?]+$/g, '')
    .replace(/\/+$/g, '')
    .toLowerCase();
}

function getAuthorizedOutboundLinks(ctx) {
  const staticData = $getWorkflowStaticData('global');
  const values = [];
  for (const candidate of [ctx?.authorizedLinks, ctx?.operatorAuthorizedLinks, ctx?.allowedLinks]) {
    if (Array.isArray(candidate)) values.push(...candidate);
  }
  const staticAuthorized = staticData?.operatorAuthorizedLinks && typeof staticData.operatorAuthorizedLinks === 'object'
    ? staticData.operatorAuthorizedLinks
    : {};
  if (Array.isArray(staticAuthorized.links)) values.push(...staticAuthorized.links);
  return new Set(values.map(normalizeAuthorizedLink).filter(Boolean));
}

function stripUnauthorizedLinks(value, authorizedLinks) {
  const allowed = authorizedLinks instanceof Set ? authorizedLinks : new Set();
  const keepOrDrop = (match, offset, source) => {
    const prev = offset > 0 ? String(source || '').charAt(offset - 1) : '';
    if (prev === '@') return match;
    return allowed.has(normalizeAuthorizedLink(match)) ? match : '';
  };

  return String(value || '')
    .replace(/\bhttps?:\/\/[^\s<>()]+/gi, keepOrDrop)
    .replace(/\bwww\.[^\s<>()]+/gi, keepOrDrop)
    .replace(/\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?:\/[^\s<>()]*)?/gi, keepOrDrop);
}

function sanitizeOutboundText(value, options) {
  const cfg = options && typeof options === 'object' ? options : {};
  const maxChars = Number(cfg.maxChars || 0);
  const authorizedLinks = cfg.authorizedLinks instanceof Set ? cfg.authorizedLinks : new Set();
  let text = String(value || '').replace(/\r\n?/g, '\n');
  text = stripUnauthorizedLinks(text, authorizedLinks);
  text = stripEmojiCharacters(text)
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
  if (maxChars > 0) {
    text = text.slice(0, maxChars).trim();
  }
  return text;
}

function suppressDuplicateOutbound(instance, number, replyText, messageId) {
  const staticData = $getWorkflowStaticData('global');
  if (!staticData.outboundRecent) staticData.outboundRecent = {};

  const nowMs = Date.now();
  const ttlMs = 1000 * 60 * 10;
  for (const [k, ts] of Object.entries(staticData.outboundRecent)) {
    if (Number(ts || 0) < (nowMs - ttlMs)) delete staticData.outboundRecent[k];
  }

  const normalizedReply = normalizeForDedupe(replyText);
  const exactKey = `${String(instance || '')}:${String(number || '')}:${normalizedReply}:${String(messageId || '')}`;
  const semanticKey = `${String(instance || '')}:${String(number || '')}:${normalizedReply}`;
  const lastExactTs = Number(staticData.outboundRecent[exactKey] || 0);
  const lastSemanticTs = Number(staticData.outboundRecent[semanticKey] || 0);
  if ((lastExactTs && (nowMs - lastExactTs) < (1000 * 45)) || (lastSemanticTs && (nowMs - lastSemanticTs) < (1000 * 120))) {
    return true;
  }

  staticData.outboundRecent[exactKey] = nowMs;
  staticData.outboundRecent[semanticKey] = nowMs;
  return false;
}

function detectRequestedProductCategory(ctx) {
  const explicit = String(ctx?.productCategoryDetected || '').trim();
  if (explicit) return explicit;

  const focus = String(ctx?.productFocusResolved || '').trim();
  if (focus === 'BOLSAS') return 'BOLSAS FEMININAS';

  const entities = (ctx?.extractedEntities && typeof ctx.extractedEntities === 'object') ? ctx.extractedEntities : {};
  const productHint = String(entities.productHint || '').toLowerCase();
  const audienceHint = String(entities.audienceHint || '').toLowerCase();

  if (productHint.includes('carteira') && audienceHint.includes('mascul')) return 'CARTEIRAS MASCULINAS';
  if (productHint.includes('carteira') && audienceHint.includes('feminin')) return 'CARTEIRAS FEMININAS';
  if (productHint.includes('cinto') && audienceHint.includes('mascul')) return 'CINTOS MASCULINOS';
  if (productHint.includes('cinto') && audienceHint.includes('feminin')) return 'CINTOS FEMININOS';
  if (productHint.includes('bolsa')) return 'BOLSAS FEMININAS';
  if (productHint.includes('mochila') && audienceHint.includes('mascul')) return 'MOCHILAS MASCULINAS';
  if (productHint.includes('mochila') && audienceHint.includes('feminin')) return 'MOCHILAS FEMININAS';
  if (productHint.includes('peca') && audienceHint.includes('mascul')) return 'ACESSORIOS MASCULINOS';
  if (productHint.includes('peca') && audienceHint.includes('feminin')) return 'ACESSORIOS FEMININOS';
  if (productHint.includes('acessorio') && audienceHint.includes('mascul')) return 'ACESSORIOS MASCULINOS';
  if (productHint.includes('acessorio') && audienceHint.includes('feminin')) return 'ACESSORIOS FEMININOS';
  return '';
}

function getRequestedCatalogCategories(ctx) {
  const explicit = detectRequestedProductCategory(ctx);
  if (explicit) return [explicit];

  const focus = String(ctx?.productFocusResolved || '').trim();
  if (focus === 'CARTEIRAS') return ['CARTEIRAS MASCULINAS', 'CARTEIRAS FEMININAS'];
  if (focus === 'CINTOS') return ['CINTOS MASCULINOS', 'CINTOS FEMININOS'];
  if (focus === 'BOLSAS') return ['BOLSAS FEMININAS'];
  if (focus === 'MOCHILAS') return ['MOCHILAS MASCULINAS', 'MOCHILAS FEMININAS'];
  if (focus === 'ACESSORIOS') return ['ACESSORIOS MASCULINOS', 'ACESSORIOS FEMININOS'];
  if (focus === 'KITS') return ['KITS MASCULINOS', 'KITS FEMININOS'];
  return [];
}

function resolveRequestedMediaCount(ctx) {
  const inbound = String(ctx?.inboundTextOriginal || '').trim();
  const m = inbound.match(/\b([1-9]|10)\b/);
  const requested = m ? Number(m[1]) : 0;
  if (requested >= 1 && requested <= 10) return requested;
  return 5;
}

function buildProductMediaItems(instance, number, ctx, maxItems) {
  const staticData = $getWorkflowStaticData('global');
  const catalog = staticData.productCatalog && typeof staticData.productCatalog === 'object'
    ? staticData.productCatalog
    : {};
  const categories = catalog.categories && typeof catalog.categories === 'object'
    ? catalog.categories
    : {};

  const requestedCategories = getRequestedCatalogCategories(ctx);
  if (requestedCategories.length === 0) return [];

  const entries = [];
  for (const category of requestedCategories) {
    if (!categories[category]) continue;
    const categoryEntries = Array.isArray(categories[category].topWithImage)
      ? categories[category].topWithImage
      : [];
    for (const entry of categoryEntries) {
      entries.push(entry);
    }
  }
  if (entries.length === 0) return [];

  if (!staticData.productMediaCursor) staticData.productMediaCursor = {};
  if (!staticData.productMediaRecentRefs) staticData.productMediaRecentRefs = {};

  const categoryKey = requestedCategories.join('|') || 'GERAL';
  const cursorKey = `${String(number || '')}:${categoryKey}`;
  const recentKey = `${String(number || '')}:${categoryKey}:recent`;
  const recentRefs = Array.isArray(staticData.productMediaRecentRefs[recentKey])
    ? staticData.productMediaRecentRefs[recentKey]
    : [];

  const filtered = entries.filter((entry) => !recentRefs.includes(String(entry.ref || '')));
  const pool = filtered.length > 0 ? filtered : entries;
  const requestedCount = Number(maxItems || resolveRequestedMediaCount(ctx) || 5);
  const limit = Math.max(1, Math.min(requestedCount, 5, pool.length));
  const startAt = Number(staticData.productMediaCursor[cursorKey] || 0) % Math.max(pool.length, 1);
  const rotated = pool.slice(startAt).concat(pool.slice(0, startAt));
  const selected = rotated.slice(0, limit);
  staticData.productMediaCursor[cursorKey] = (startAt + limit) % Math.max(pool.length, 1);
  staticData.productMediaRecentRefs[recentKey] = selected
    .map((entry) => String(entry.ref || ''))
    .filter(Boolean)
    .slice(-12);

  return selected.map((entry) => {
    const caption = String(entry.caption || '').trim();
    const duplicate = suppressDuplicateOutbound(instance, number, `[media] ${caption}`, ctx?.messageId);
    return {
      json: {
        instance,
        number: duplicate ? '' : number,
        sendEligible: !duplicate,
        sendEligibilityReason: duplicate ? 'duplicate_suppressed' : 'eligible',
        sendMode: 'media',
        delayMs: Number(entry.delayMs || ctx?.productMediaDelayMs || 1800),
        mediaType: 'image',
        media: String(entry.mediaBase64 || ''),
        mimeType: String(entry.mimeType || 'image/jpeg'),
        caption,
        duplicateOutboundSuppressed: duplicate
      }
    };
  }).filter((item) => String(item.json.media || '').trim());
}

function buildVitrineMediaItems(instance, number, ctx) {
  const staticData = $getWorkflowStaticData('global');
  const vitrineAssets = staticData.vitrineAssets && typeof staticData.vitrineAssets === 'object'
    ? staticData.vitrineAssets
    : {};
  const items = Array.isArray(vitrineAssets.items) ? vitrineAssets.items : [];
  if (items.length === 0) return [];

  return items.slice(0, 5).map((asset) => {
    const label = `[vitrine] ${String(asset.fileName || asset.label || '')}`;
    const duplicate = suppressDuplicateOutbound(instance, number, label, `${ctx?.messageId || ''}:${asset.label || ''}`);
    return {
      json: {
        instance,
        number: duplicate ? '' : number,
        sendEligible: !duplicate,
        sendEligibilityReason: duplicate ? 'duplicate_suppressed' : 'eligible',
        sendMode: 'media',
        delayMs: Number(asset.delayMs || ctx?.vitrineDelayMs || 7200),
        mediaType: String(asset.mediaType || 'image'),
        media: String(asset.mediaBase64 || ''),
        mimeType: String(asset.mimeType || 'image/jpeg'),
        caption: String(asset.caption || asset.label || '').trim(),
        fileName: String(asset.fileName || '').trim(),
        duplicateOutboundSuppressed: duplicate
      }
    };
  }).filter((item) => String(item.json.media || '').trim());
}

function buildOrderChoiceButtonsItem(instance, number, ctx, delayMs) {
  if (!number || !ctx || !ctx.sendOrderChoiceButtons) return null;
  const duplicate = suppressDuplicateOutbound(instance, number, '[order-choice-buttons]', `${ctx?.messageId || ''}:order-choice-buttons`);
  if (duplicate) return null;

  return {
    json: {
      instance,
      number,
      sendEligible: true,
      sendEligibilityReason: 'eligible',
      sendMode: 'buttons',
      delayMs: Number(delayMs || ctx?.orderChoiceButtonsDelayMs || 12200),
      title: 'Como voce prefere seguir com o pedido?',
      description: 'Escolha se quer montar seu pedido direto no portal B2B ou seguir com o apoio do Eduardo neste canal.',
      footer: 'Classe Couro - Pedido inicial',
      buttons: [
        { type: 'reply', displayText: 'Pedir pelo site B2B', id: 'btn_pedido_b2b' },
        { type: 'reply', displayText: 'Montar com Eduardo', id: 'btn_pedido_eduardo' }
      ],
      duplicateOutboundSuppressed: false
    }
  };
}

function buildRuleBasedReply(ctx) {
  if (ctx.mandatoryDirectiveMatched) {
    const objective = String(ctx.mandatoryDirectiveObjective || '').trim();
    const questions = Array.isArray(ctx.mandatoryDirectiveQuestions) ? ctx.mandatoryDirectiveQuestions : [];
    const firstQuestion = String(questions[0] || '').trim();
    if (objective && firstQuestion) {
      return `Perfeito! Vou seguir nosso roteiro com foco em ${objective}. ${firstQuestion}`;
    }
    if (firstQuestion) return firstQuestion;
  }

  const intent = String(ctx.detectedIntent || 'geral');
  const entities = (ctx.extractedEntities && typeof ctx.extractedEntities === 'object') ? ctx.extractedEntities : {};
  const qty = Number(entities.quantity || 0);
  const city = String(entities.cityHint || '').trim();
  const productHint = String(entities.productHint || '').toLowerCase();
  const audienceHint = String(entities.audienceHint || '').toLowerCase();
  const focus = String(ctx.productFocusResolved || '').trim();
  const linePreference = String(ctx.productLinePreference || '').trim();
  const imageRequest = Boolean(ctx.productImageRequest);
  const category = String(ctx.productCategoryDetected || '').trim();
  const inboundText = String(ctx.inboundTextOriginal || '').trim();
  const normalizedInbound = normalizeForDedupe(inboundText);
  const greetingOnly = (
    ['bom dia', 'boa tarde', 'boa noite', 'ola', 'olá', 'oi', 'tudo bem', 'tudo bom'].includes(normalizedInbound) ||
    /^(bom dia|boa tarde|boa noite|ola|olá|oi)[!. ]*$/.test(normalizedInbound)
  );

  if (greetingOnly && !ctx.mandatoryScriptActive) {
    return 'Que bom falar com voce. Fique a vontade para me dizer o que voce procura, que eu vou te ajudar da melhor forma possivel.';
  }

  if (intent === 'saudacao') {
    return 'Que bom falar com voce. Fique a vontade para me dizer o que voce procura, que eu vou te ajudar da melhor forma possivel.';
  }

  if (intent === 'agradecimento') {
    return 'Eu que agradeco. Sempre que precisar, estou por aqui para te ajudar no que for necessario.';
  }

  if (intent === 'institucional_empresa') {
    return 'Claro. A Classe Couro e referencia em bolsas e acessorios de couro, com mais de 30 anos de mercado, unindo design e alta qualidade. Se quiser, te mostro as linhas com melhor saida para revenda no seu perfil.';
  }

  if (intent === 'atacado_quantidade' || intent === 'preco_orcamento') {
    const qtyText = qty > 0 ? `${qty} unidades` : 'essa quantidade';
    return `Entendi sua necessidade. Para ${qtyText}, consigo montar a melhor condicao comercial para voce. Voce precisa mais de cintos, carteiras ou ambos?`;
  }

  if (intent === 'prazo_entrega') {
    const cityText = city ? ` para ${city}` : '';
    return `Consigo te orientar o prazo com precisao${cityText}. Para eu te indicar a melhor opcao agora, qual volume aproximado voce precisa?`;
  }

  if (intent === 'produto_catalogo') {
    if (imageRequest && focus) {
      return `Separei algumas imagens de ${focus.toLowerCase()} para voce visualizar melhor. Se quiser, depois eu tambem organizo as opcoes por estilo ou perfil de venda.`;
    }

    if (linePreference && focus) {
      return `Para comecar, vou te mostrar algumas opcoes de ${focus.toLowerCase()} com bom giro para voce visualizar melhor. Se quiser, depois eu tambem separo por estilo ou perfil de venda.`;
    }

    if (productHint.includes('bolsa') || focus === 'BOLSAS' || category === 'BOLSAS FEMININAS') {
      return 'Temos otimas opcoes de bolsas com excelente aceitacao na revenda. Voce procura mais shopping bags, bolsas estruturadas ou uma selecao mista?';
    }

    if (productHint.includes('mochila') || focus === 'MOCHILAS' || category.includes('MOCHILAS')) {
      if (!audienceHint && !category) {
        return 'Temos mochilas com otima percepcao de valor e excelente saida na revenda. Voce procura mais modelos masculinos, femininos ou uma selecao mista?';
      }
      const categoryText = category ? ` ${category.toLowerCase()}` : (audienceHint ? ` ${audienceHint}` : '');
      return `Temos otimas opcoes de mochilas${categoryText} com boa procura e otimo potencial de giro. Voce prefere uma linha mais casual, executiva ou uma selecao mista?`;
    }

    if (productHint.includes('kit') || focus === 'KITS' || category.includes('KITS')) {
      if (!audienceHint && !category) {
        return 'Temos kits com otima percepcao de presente e excelente potencial de revenda. Voce procura mais kits masculinos, femininos ou uma selecao mista?';
      }
      const categoryText = category ? ` ${category.toLowerCase()}` : (audienceHint ? ` ${audienceHint}` : '');
      return `Temos kits${categoryText} com boa percepcao de valor e otima aceitacao na revenda. Voce quer uma linha mais classica, presenteavel ou uma selecao mista?`;
    }

    if (productHint.includes('carteira')) {
      if (!audienceHint) {
        return 'Temos otimas opcoes de carteiras com excelente giro para revenda. Voce procura mais modelos masculinos, femininos ou uma selecao mista?';
      }
      const audienceText = audienceHint ? ` ${audienceHint}` : '';
      return `Temos otimas opcoes de carteiras${audienceText} em couro, com excelente giro para revenda. Voce prefere linha basica, intermediaria ou premium?`;
    }

    if (productHint.includes('cinto')) {
      if (!audienceHint) {
        return 'Temos linhas de cintos com otima saida e excelente percepcao de valor. Voce procura mais modelos masculinos, femininos ou uma selecao mista?';
      }
      const audienceText = audienceHint ? ` ${audienceHint}` : '';
      return `Temos linhas de cintos${audienceText} com otima saida e excelente percepcao de valor. Voce prefere modelos casuais, sociais ou misto?`;
    }

    if (productHint.includes('peca') || productHint.includes('acessorio') || focus === 'ACESSORIOS' || category.includes('ACESSORIOS') || audienceHint) {
      const audienceText = audienceHint ? ` ${audienceHint}` : '';
      return `Temos uma linha forte de acessorios${audienceText} com otimo giro e boa percepcao de valor na revenda. Para eu te indicar a melhor selecao agora, voce quer comecar por carteiras, cintos, porta-cartoes ou uma selecao mista?`;
    }

    return 'Temos opcoes que podem te atender muito bem. Para eu te recomendar a linha mais assertiva agora, qual categoria voce quer priorizar primeiro?';
  }

  if (intent === 'pagamento') {
    return 'Temos condicoes de pagamento conforme o pedido. Para eu te passar a opcao certa agora, qual produto e quantidade voce precisa?';
  }

  return 'Quero te ajudar da forma mais assertiva possivel. Me conta: qual e sua necessidade principal agora?';
}

function enforceProspectingQuality(replyText, ctx) {
  let text = String(replyText || '').replace(/\s+/g, ' ').trim();
  if (!text) return text;

  const intent = String(ctx.detectedIntent || 'geral');
  const isFirstInbound = Boolean(ctx.isFirstInbound);
  const customerName = String(ctx.customerName || '').trim();
  const norm = normalizeForDedupe(text);
  const focus = String(ctx.productFocusResolved || '').trim();
  const category = String(ctx.productCategoryDetected || '').trim();

  const genericSnippets = [
    'qual produto voce quer priorizar agora',
    'voce quer comecar por carteiras cintos ou ambos',
    'voce precisa mais de cintos carteiras ou ambos',
    'quero te ajudar da forma mais assertiva possivel me conta em uma linha',
    'qual e sua necessidade principal agora'
  ];
  const looksTooGeneric = genericSnippets.some((snippet) => norm.includes(snippet));

  if (intent === 'institucional_empresa' && !/classe couro|classe/i.test(text)) {
    text = 'Claro! A Classe Couro atua com acessórios de couro, unindo qualidade, design e atendimento consultivo para ajudar cada cliente a encontrar a melhor solução. Se fizer sentido para você, eu também posso te mostrar as linhas com melhor saída no seu perfil.';
  }

  if (intent === 'produto_catalogo' && (focus || category) && looksTooGeneric) {
    const targetLabel = String(category || focus || 'produtos').toLowerCase();
    if (targetLabel.includes('bolsa')) {
      text = 'Temos ótimas opções de bolsas com excelente aceitação na revenda. Você procura mais shopping bags, bolsas estruturadas ou uma seleção mista?';
    } else if (targetLabel.includes('mochila')) {
      text = 'Temos mochilas com ótima percepção de valor e excelente saída na revenda. Você procura mais modelos masculinos, femininos ou uma seleção mista?';
    } else if (targetLabel.includes('kit')) {
      text = 'Temos kits com ótima percepção de presente e excelente potencial de revenda. Você procura mais kits masculinos, femininos ou uma seleção mista?';
    } else if (targetLabel.includes('acessorio')) {
      text = 'Temos uma linha forte de acessórios com ótimo giro e boa percepção de valor na revenda. Você quer começar por carteiras, cintos, porta-cartões ou uma seleção mista?';
    } else {
      text = `Perfeito! Separei uma direção mais assertiva para ${targetLabel}. Se você quiser, eu sigo te mostrando as opções com melhor giro e te ajudo a escolher a linha mais adequada para o seu perfil.`;
    }
  }

  if (isFirstInbound && !text.includes('?') && !ctx.mandatoryDirectiveMatched && !['agradecimento', 'institucional_empresa'].includes(intent)) {
    if (intent === 'produto_catalogo') {
      text = `${text} O que você quer priorizar primeiro?`;
    } else if (intent === 'atacado_quantidade' || intent === 'preco_orcamento') {
      text = `${text} Qual produto faz mais sentido para você começar agora?`;
    } else {
      text = `${text} Como posso te ajudar melhor neste primeiro momento?`;
    }
  }

  const repeatedName = customerName
    ? new RegExp(`\\b${customerName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi')
    : null;
  if (repeatedName) {
    const matches = text.match(repeatedName) || [];
    if (matches.length > 1) {
      let firstSeen = false;
      text = text.replace(repeatedName, (m) => {
        if (!firstSeen) {
          firstSeen = true;
          return m;
        }
        return '';
      }).replace(/\s{2,}/g, ' ').replace(/\s+([,!.?])/g, '$1').trim();
    }
  }

  return text.trim();
}

function enforceMandatoryDirective(replyText, ctx) {
  if (!ctx.mandatoryDirectiveMatched) return String(replyText || '').trim();

  const objective = String(ctx.mandatoryDirectiveObjective || '').trim();
  const questions = Array.isArray(ctx.mandatoryDirectiveQuestions) ? ctx.mandatoryDirectiveQuestions : [];
  const firstQuestion = String(questions[0] || '').trim();
  let text = String(replyText || '').trim();

  const norm = normalizeForDedupe(text);
  const objectiveNorm = normalizeForDedupe(objective);
  const keepsObjective = !objectiveNorm || norm.includes(objectiveNorm.slice(0, 20));

  if (!text || !keepsObjective) {
    if (objective && firstQuestion) {
      text = `Perfeito! Vou seguir nosso roteiro com foco em ${objective}. ${firstQuestion}`;
    } else if (firstQuestion) {
      text = firstQuestion;
    }
  } else if (firstQuestion && !text.includes('?')) {
    text = `${text} ${firstQuestion}`;
  }

  return text.trim();
}

function looksMechanicalReply(text) {
  const norm = normalizeForDedupe(text);
  if (!norm) return true;
  const genericSnippets = [
    'qual produto voce quer priorizar agora',
    'qual e sua necessidade principal agora',
    'quero te ajudar da forma mais assertiva possivel',
    'como posso te ajudar melhor neste primeiro momento',
    'voce quer comecar por carteiras cintos ou ambos',
    'voce precisa mais de cintos carteiras ou ambos'
  ];
  return genericSnippets.some((snippet) => norm.includes(snippet));
}

const sensitiveIntents = new Set(['pos_venda_reclamacao', 'troca_devolucao', 'cancelamento']);
const customerName = String(guardrails.customerName || '').trim();

let reply = '';
let intent = String(guardrails.detectedIntent || 'geral');
let confidence = 0.62;
let needsHuman = Boolean(guardrails.humanPriority);
let leadStage = 'qualificando';
let humanReason = '';
let followUpQuestion = '';
let extractedEntities = {};
let memoryUpdate = {};
let modelRaw = '';
let modelResponseId = '';
let modelRequestedHuman = false;
let modelJsonParsed = false;

// --- Dual-LLM: use pre-generated reply from router if available ---
const llmReplyText = String(guardrails.llmReplyText || '').trim();
const llmProvider = String(guardrails.llmProvider || '').trim();
const llmStructuredData = guardrails.llmStructuredData || {};
const llmLeadScore = guardrails.llmLeadScore || {};
const routeDecision = String(guardrails.routeDecision || '').trim();

// Merge structured extraction data from dual-LLM
if (llmStructuredData && typeof llmStructuredData === 'object' && Object.keys(llmStructuredData).length > 0) {
  extractedEntities = { ...extractedEntities, ...llmStructuredData };
}

if (response?.error || response?.statusCode >= 400) {
  const errMsg = String(
    response?.error?.message ??
    response?.message ??
    response?.body?.error?.message ??
    ''
  );

  if (llmReplyText) {
    // Dual-LLM fallback: router already generated a reply via Claude/GPT
    reply = llmReplyText;
    confidence = 0.7;
    needsHuman = false;
    modelRaw = `[dual-llm:${llmProvider}] ${llmReplyText}`;
  } else if (/too many|rate.?limit|429/i.test(errMsg)) {
    reply = fallbackBusy;
    confidence = 0.35;
    needsHuman = true;
    humanReason = guardrails.humanPriority || sensitiveIntents.has(intent)
      ? 'openai_rate_limit_sensitive'
      : 'openai_rate_limit_general';
  } else {
    reply = fallbackWaiting;
    confidence = 0.4;
    needsHuman = true;
    humanReason = guardrails.humanPriority || sensitiveIntents.has(intent)
      ? 'openai_error_sensitive'
      : 'openai_error_general';
  }
} else {
  modelResponseId = extractResponseId(response);
  modelRaw = extractRawText(response);
  const parsed = parseModelJson(modelRaw);

  if (parsed && typeof parsed === 'object') {
    modelJsonParsed = true;
    if (parsed.reply) reply = String(parsed.reply).trim();
    if (parsed.intent) intent = String(parsed.intent);
    if (parsed.follow_up_question) followUpQuestion = String(parsed.follow_up_question);
    if (parsed.human_reason) humanReason = String(parsed.human_reason);
    if (parsed.lead_stage) leadStage = String(parsed.lead_stage);
    if (parsed.extracted_entities && typeof parsed.extracted_entities === 'object') extractedEntities = parsed.extracted_entities;
    if (parsed.customer_memory_update && typeof parsed.customer_memory_update === 'object') memoryUpdate = parsed.customer_memory_update;

    confidence = clampConfidence(parsed.confidence, confidence);
    modelRequestedHuman = Boolean(parsed.needs_human);
  } else {
    reply = modelRaw;
    confidence = clampConfidence(guardrails.detectedIntentScore, 0.58);
  }

  if (!reply) {
    reply = buildRuleBasedReply(guardrails);
    humanReason = humanReason || 'empty_model_reply';
  }
}

const routerOwnsReplyText = Boolean(llmReplyText) && /^rag_claude$|^claude_direct$/i.test(routeDecision);
if (routerOwnsReplyText && !modelRequestedHuman) {
  reply = llmReplyText;
  confidence = Math.max(confidence, 0.74);
  modelRaw = `[router-${llmProvider || 'anthropic'}] ${llmReplyText}`;
} else if (llmReplyText && looksMechanicalReply(reply)) {
  reply = llmReplyText;
  confidence = Math.max(confidence, 0.68);
  modelRaw = `[dual-llm-refine:${llmProvider || 'router'}] ${llmReplyText}`;
}

const minConfidence = Number(guardrails.minConfidenceForAutoSend || 0.4);
const lowConfidence = confidence < minConfidence;
const intentSensitive = sensitiveIntents.has(intent);

if (guardrails.humanPriority || intentSensitive) {
  needsHuman = needsHuman || modelRequestedHuman || lowConfidence;
  if (!humanReason && (modelRequestedHuman || lowConfidence)) humanReason = 'sensitive_intent_review';
} else {
  const veryLowConfidence = confidence < 0.25;
  const weakReply = String(reply || '').trim().length < 24;
  needsHuman = needsHuman || (modelRequestedHuman && (lowConfidence || weakReply)) || veryLowConfidence;
  if (!humanReason && needsHuman && veryLowConfidence) humanReason = 'very_low_confidence';
}

reply = String(reply || fallbackWaiting).replace(/\s+/g, ' ').trim();
if (followUpQuestion && !reply.includes('?') && !needsHuman) {
  reply = `${reply} ${String(followUpQuestion).trim()}`;
}

reply = enforceMandatoryDirective(reply, guardrails);
if (!needsHuman) {
  reply = enforceProspectingQuality(reply, guardrails);
}

let requiresHumanCall = false;
if (needsHuman) {
  reply = 'Aqui e o Eduardo, Consultor de Vendas Internas da Classe Couro. Peco um instante enquanto assumo seu atendimento pessoalmente.';
  requiresHumanCall = /openai_rate_limit|openai_error|api_timeout/.test(String(humanReason || ''));
}

const requestedProductCategory = detectRequestedProductCategory(guardrails);
const requestedProductFocus = String(guardrails.productFocusResolved || '').trim();
if (!needsHuman && (requestedProductCategory || requestedProductFocus)) {
  const genericReply = normalizeForDedupe(reply);
  const tooGeneric = [
    'qual produto voce quer priorizar agora',
    'voce quer comecar por carteiras cintos ou ambos',
    'voce precisa mais de cintos carteiras ou ambos',
    'voce prefere linha basica intermediaria ou premium'
  ].some((snippet) => genericReply.includes(snippet));

  if (tooGeneric) {
    const targetLabel = String(requestedProductCategory || requestedProductFocus || 'produtos').toLowerCase();
    reply = `Separei algumas opções de ${targetLabel} com bom giro para você visualizar melhor. Se alguma linha fizer sentido para o seu perfil, eu sigo com você a partir dela.`;
  }
}

reply = applySalutation(reply, {
  number: guardrails.number,
  customerName,
  workTimezone: guardrails.workTimezone,
  isFirstInbound: guardrails.isFirstInbound,
  inboundText: guardrails.inboundTextOriginal,
  skipAutomaticSalutation: Boolean(guardrails.skipAutomaticSalutation)
});
const authorizedOutboundLinks = getAuthorizedOutboundLinks(guardrails);
reply = sanitizeOutboundText(reply, {
  authorizedLinks: authorizedOutboundLinks,
      maxChars: Number(guardrails.maxOutputChars || 1800)
});
if (!reply) {
  reply = sanitizeOutboundText(fallbackWaiting, {
    authorizedLinks: authorizedOutboundLinks,
      maxChars: Number(guardrails.maxOutputChars || 1800)
  });
}

const staticData = $getWorkflowStaticData('global');
if (!staticData.customerProfiles) staticData.customerProfiles = {};
if (!staticData.customerHistory) staticData.customerHistory = {};
if (!staticData.humanQueue) staticData.humanQueue = [];
if (!staticData.learningBacklog) staticData.learningBacklog = [];

const number = String(guardrails.number || '').replace(/\D/g, '');
const instance = String(guardrails.instance || '');
const pushName = String(guardrails.pushName || 'Cliente');
const nowIso = new Date().toISOString();
const sendEligible = Boolean(guardrails.sendEligible === true && number);
const sendEligibilityReason = String(guardrails.sendEligibilityReason || '').trim() || (sendEligible ? 'eligible' : 'blocked');
const duplicateOutbound = sendEligible ? suppressDuplicateOutbound(instance, number, reply, guardrails.messageId) : false;
const sendNumber = (sendEligible && !duplicateOutbound) ? number : '';
const productMediaItems = (!needsHuman && sendNumber)
  ? buildProductMediaItems(instance, number, guardrails, resolveRequestedMediaCount(guardrails))
  : [];
const vitrineMediaItems = (!needsHuman && sendNumber && Boolean(guardrails.sendVitrineAssets))
  ? buildVitrineMediaItems(instance, number, guardrails)
  : [];

if (number) {
  const profile = staticData.customerProfiles[number] || {
    number,
    pushName,
    firstSeenAt: nowIso,
    messageCount: 0,
    leadStage: 'novo',
    notes: ''
  };

  profile.pushName = pushName;
  if (customerName) {
    profile.customerName = customerName;
    profile.customerNameSource = profile.customerNameSource || 'self_identified';
  }
  profile.lastSeenAt = nowIso;
  profile.lastIntent = intent;
  profile.lastConfidence = confidence;
  profile.leadStage = leadStage || profile.leadStage || 'qualificando';
  profile.lastInboundText = String(guardrails.inboundTextOriginal || '').slice(0, 300);
  profile.lastReplyText = String(reply).slice(0, 300);
  profile.awaitingHuman = Boolean(needsHuman);
  if (modelResponseId) {
    profile.lastOpenAiResponseId = modelResponseId;
    profile.lastOpenAiResponseAt = nowIso;
  }

  if (memoryUpdate && typeof memoryUpdate === 'object') {
    if (memoryUpdate.notes) profile.notes = String(memoryUpdate.notes).slice(0, 600);
    if (memoryUpdate.next_step) profile.nextStep = String(memoryUpdate.next_step).slice(0, 300);
  }

  if (extractedEntities && typeof extractedEntities === 'object') {
    profile.lastEntities = extractedEntities;
  }

  staticData.customerProfiles[number] = profile;

  if (!staticData.customerHistory[number]) staticData.customerHistory[number] = [];
  const history = staticData.customerHistory[number];
  history.push({ role: 'assistant', text: reply, timestamp: nowIso, intent, confidence, needsHuman });
  while (history.length > 20) history.shift();

  if (needsHuman) {
    const queue = staticData.humanQueue;
    const recentIdx = queue.findIndex((q) => q.number === number && q.status !== 'closed');

    const leadScore = Number(guardrails.leadScore || 0);
    const conversationTurns = Number(guardrails.contextCarryover?.conversationTurns || 0);
    const isHighIntent = Boolean(guardrails.humanPriority) || intentSensitive;
    const hasEntities = Boolean(guardrails.extractedEntities && Object.keys(guardrails.extractedEntities).length > 0);
    const hasUrgency = Boolean(guardrails.extractedEntities?.urgencyHint);

    let priorityScore = 0;
    if (isHighIntent) priorityScore += 40;
    if (hasUrgency) priorityScore += 25;
    if (leadScore >= 3) priorityScore += 20;
    else if (leadScore >= 1) priorityScore += 10;
    if (conversationTurns >= 3) priorityScore += 10;
    if (hasEntities) priorityScore += 5;

    const urgencyLevel = priorityScore >= 60 ? 'critical'
      : priorityScore >= 35 ? 'high'
      : priorityScore >= 15 ? 'medium'
      : 'low';

    const ticket = {
      number,
      pushName,
      createdAt: nowIso,
      status: 'open',
      priority: urgencyLevel,
      priorityScore,
      reason: humanReason || 'manual_review',
      intent,
      leadScore,
      conversationTurns,
      inboundText: String(guardrails.inboundTextOriginal || '').slice(0, 500)
    };

    if (recentIdx >= 0) {
      queue[recentIdx] = { ...queue[recentIdx], ...ticket, updatedAt: nowIso };
    } else {
      queue.push(ticket);
    }

    queue.sort((a, b) => (b.priorityScore || 0) - (a.priorityScore || 0));
    while (queue.length > 200) queue.pop();
  }

  if (!needsHuman) {
    const queue = staticData.humanQueue;
    const openIdx = queue.findIndex((q) => q.number === number && q.status !== 'closed');
    if (openIdx >= 0) {
      queue[openIdx] = {
        ...queue[openIdx],
        status: 'closed',
        closedAt: nowIso,
        closeReason: 'auto_resolved_by_ai'
      };
    }
  }

  if (lowConfidence || !modelJsonParsed) {
    staticData.learningBacklog.push({
      createdAt: nowIso,
      number,
      pushName,
      intent,
      confidence,
      modelJsonParsed,
      customerQuestion: String(guardrails.inboundTextOriginal || '').slice(0, 500),
      modelRaw: String(modelRaw || '').slice(0, 1200)
    });
    while (staticData.learningBacklog.length > 500) staticData.learningBacklog.shift();
  }
}

const outboundItems = [{
  json: {
    instance,
    number: sendNumber,
    sendMode: 'text',
    delayMs: Number(guardrails.replyDelayMs || 1200),
    replyText: reply,
    inboundTextOriginal: String(guardrails.inboundTextOriginal || ''),
    intent,
    confidence,
    needsHuman,
    requiresHumanCall,
    sendEligible,
    sendEligibilityReason,
    insideSalesOwnNumber: String(guardrails.insideSalesOwnNumber || ''),
    leadStage,
    humanReason,
    routeDecision: String(guardrails.routeDecision || ''),
    messageComplexity: String(guardrails.messageComplexity || ''),
    customerName,
    productFocusResolved: String(guardrails.productFocusResolved || ''),
    productCategoryDetected: String(guardrails.productCategoryDetected || ''),
    followUpQuestion: String(followUpQuestion || '').trim(),
    customerMemoryUpdate: memoryUpdate,
    extractedEntities,
    llmProvider: llmProvider || 'openai',
    llmModel: String(guardrails.llmModel || ''),
    llmStructuredData: extractedEntities,
    duplicateOutboundSuppressed: duplicateOutbound,
    skipAutomaticSalutation: Boolean(guardrails.skipAutomaticSalutation)
  }
}];

for (const mediaItem of productMediaItems) {
  if (mediaItem?.json?.caption) {
    mediaItem.json.caption = sanitizeOutboundText(mediaItem.json.caption, {
      authorizedLinks: authorizedOutboundLinks,
      maxChars: 240
    });
  }
  outboundItems.push(mediaItem);
}

if (Boolean(guardrails.sendVitrineAssets) && sendNumber) {
  const vitrinePrelude = 'Para te ajudar a visualizar melhor o potencial da marca no ponto de venda, eu tambem posso te mostrar uma vitrine de referencia. Isso costuma facilitar bastante, porque voce consegue imaginar com mais clareza como os produtos da Classe Couro podem valorizar a apresentacao da sua loja, chamar mais atencao do cliente final e construir uma percepcao mais forte de desejo e qualidade. Quando o mix esta bem montado, a vitrine praticamente comeca a vender antes mesmo da abordagem.';
  const duplicatePrelude = suppressDuplicateOutbound(instance, sendNumber, vitrinePrelude, `${guardrails.messageId || ''}:vitrine-prelude`);
  if (!duplicatePrelude) {
    outboundItems.push({
      json: {
        instance,
        number: sendNumber,
        sendMode: 'text',
        delayMs: Number(guardrails.vitrinePreludeDelayMs || 5200),
        replyText: vitrinePrelude,
        sendEligible: true,
        sendEligibilityReason: 'eligible',
        duplicateOutboundSuppressed: false,
        skipAutomaticSalutation: true
      }
    });
  }
}

let vitrineDelayCursor = Number(guardrails.vitrineFirstAssetDelayMs || 7200);
for (const mediaItem of vitrineMediaItems) {
  if (mediaItem?.json?.caption) {
    mediaItem.json.caption = sanitizeOutboundText(mediaItem.json.caption, {
      authorizedLinks: authorizedOutboundLinks,
      maxChars: 240
    });
  }
  mediaItem.json.delayMs = Number(mediaItem?.json?.delayMs || vitrineDelayCursor);
  vitrineDelayCursor += Number(guardrails.vitrineDelayStepMs || 1800);
  outboundItems.push(mediaItem);
}

const orderChoiceButtonsItem = (!needsHuman && sendNumber)
  ? buildOrderChoiceButtonsItem(instance, sendNumber, guardrails, vitrineDelayCursor + 800)
  : null;
if (orderChoiceButtonsItem) {
  outboundItems.push(orderChoiceButtonsItem);
}

return outboundItems;
