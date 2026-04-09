const payload = $json;
const maxOutputChars = Number(payload.maxOutputChars || 1800);
const customerName = (String(payload.customerName || '').trim().split(/\s+/).filter(Boolean)[0] || '');

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

function buildSalesBookMediaItem(instance, number, payload) {
  const staticData = $getWorkflowStaticData('global');
  const salesBookAsset = staticData.salesBookAsset && typeof staticData.salesBookAsset === 'object'
    ? staticData.salesBookAsset
    : null;

  if (!salesBookAsset || !String(salesBookAsset.mediaBase64 || '').trim()) return null;

  const mediaLabel = `[sales-book-pdf] ${String(salesBookAsset.fileName || payload.salesBookFileName || 'BOOK_PROSPECCAO_VENDAS_INTERNAS.pdf')}`;
  const duplicateMedia = suppressDuplicateOutbound(instance, number, mediaLabel, payload.messageId);
  const sendNumber = duplicateMedia ? '' : number;
  if (!sendNumber) return null;

  return {
    json: {
      instance,
      number: sendNumber,
      sendEligible: true,
      sendEligibilityReason: 'eligible',
      sendMode: 'media',
      delayMs: Number(payload.salesBookDelayMs || 2600),
      mediaType: 'document',
      media: String(salesBookAsset.mediaBase64 || ''),
      mimeType: String(salesBookAsset.mimeType || payload.salesBookMimeType || 'application/pdf'),
      fileName: String(salesBookAsset.fileName || payload.salesBookFileName || 'BOOK_PROSPECCAO_VENDAS_INTERNAS.pdf'),
      caption: sanitizeOutboundText(String(payload.salesBookCaption || salesBookAsset.caption || '').trim(), {
        authorizedLinks: authorizedOutboundLinks,
        maxChars: 240
      }),
      duplicateOutboundSuppressed: duplicateMedia
    }
  };
}

function buildVitrineMediaItems(instance, number, payload) {
  const staticData = $getWorkflowStaticData('global');
  const vitrineAssets = staticData.vitrineAssets && typeof staticData.vitrineAssets === 'object'
    ? staticData.vitrineAssets
    : {};
  const items = Array.isArray(vitrineAssets.items) ? vitrineAssets.items : [];
  if (items.length === 0) return [];

  return items.slice(0, 5).map((asset) => {
    const label = `[vitrine] ${String(asset.fileName || asset.label || '')}`;
    const duplicate = suppressDuplicateOutbound(instance, number, label, `${payload.messageId || ''}:${asset.fileName || asset.label || ''}`);
    return {
      json: {
        instance,
        number: duplicate ? '' : number,
        sendEligible: !duplicate,
        sendEligibilityReason: duplicate ? 'duplicate_suppressed' : 'eligible',
        sendMode: 'media',
        delayMs: Number(asset.delayMs || payload.vitrineDelayMs || 7200),
        mediaType: String(asset.mediaType || 'image'),
        media: String(asset.mediaBase64 || ''),
        mimeType: String(asset.mimeType || 'image/jpeg'),
        caption: sanitizeOutboundText(String(asset.caption || asset.label || '').trim(), {
          authorizedLinks: authorizedOutboundLinks,
          maxChars: 240
        }),
        fileName: String(asset.fileName || '').trim(),
        duplicateOutboundSuppressed: duplicate
      }
    };
  }).filter((item) => String(item.json.media || '').trim());
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

  out = out.replace(/^(?:oi|ola|ol?)\s+[^\n,!.:?]{1,40}\s*[,!:\-]\s*/i, '');
  out = out.replace(/^(?:oi|ola|ol?)\s*[,!:\-]\s*/i, '');
  out = out.replace(/^(?:bom dia|boa tarde|boa noite)\s+[^\n,!.:?]{1,40}\s*[,!:\-]\s*/i, '');
  out = out.replace(/^(?:bom dia|boa tarde|boa noite)\s*[,!:\-]\s*/i, '');

  return out.trim();
}

function hasGreetingCue(text) {
  const norm = normalizeForDedupe(text);
  return ['bom dia', 'boa tarde', 'boa noite', 'ola', 'ol?', 'oi'].some((k) => norm.includes(k));
}

function composeSalutation(number, name, workTimezone, isFirstInbound, cadence) {
  const greeting = capitalize(getGreetingByHour(getHourInTimezone(workTimezone)));
  if (!number || !name) return `${greeting}!`;
  const nowMs = Date.now();
  const minutesSinceNamed = (nowMs - Number(cadence.lastNamedAt || 0)) / 60000;
  const useName = Boolean(isFirstInbound) || Number(cadence.count || 0) <= 1 || (Number(cadence.count || 0) % 4 === 0) || minutesSinceNamed >= 90;
  return useName ? `${greeting}, ${name}!` : `${greeting}!`;
}

function applySalutation(text, data) {
  if (Boolean(data.skipAutomaticSalutation)) {
    return String(text || '').replace(/\s+/g, ' ').trim();
  }
  const cleanText = stripLeadingSalutation(text);
  const earlyBody = normalizeForDedupe(String(cleanText || '').slice(0, 120));
  const hasEarlyNameMention = Boolean(customerName) && earlyBody.includes(normalizeForDedupe(customerName));
  const startsWithCommercialLead = /^(perfeito|certo|entendi|otimo|ótimo|seu pre-cadastro|estou te enviando|para te ajudar)/i.test(String(cleanText || ''));
  const number = String(data.number || '').replace(/\D/g, '');
  if (!number) return cleanText;

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
  const greetedByCustomer = hasGreetingCue(String(data.inboundTextOriginal || data.inboundText || ''));
  const shouldSalute = Boolean(data.isFirstInbound) ||
    Number(cadence.lastSalutedAt || 0) === 0 ||
    minutesSinceSalutation >= 60 ||
    (greetedByCustomer && minutesSinceSalutation >= 25);

  let finalText = cleanText;
  cadence.count = Number(cadence.count || 0) + 1;

  if (shouldSalute && !(hasEarlyNameMention && startsWithCommercialLead)) {
    const salutation = composeSalutation(
      number,
      hasEarlyNameMention ? '' : String(customerName || ''),
      String(data.workTimezone || 'America/Bahia'),
      Boolean(data.isFirstInbound),
      cadence
    );
    finalText = cleanText ? `${salutation} ${cleanText}` : salutation;
    cadence.lastSalutedAt = nowMs;
    if (String(salutation).includes(',')) cadence.lastNamedAt = nowMs;
  }

  cadence.updatedAt = nowMs;
  staticData.salutationCadence[number] = cadence;
  return String(finalText || '').replace(/\s+/g, ' ').trim();
}

let text = String(payload.fallbackText || 'Aqui e o Eduardo, Consultor de Vendas Internas da Classe Couro. Recebi sua mensagem e ja vou te atender.');
text = applySalutation(text, payload);
const authorizedOutboundLinks = getAuthorizedOutboundLinks(payload);
text = sanitizeOutboundText(text, {
  authorizedLinks: authorizedOutboundLinks,
  maxChars: maxOutputChars
});
if (!text) {
  text = sanitizeOutboundText('Aqui e o Eduardo, Consultor de Vendas Internas da Classe Couro. Recebi sua mensagem e ja vou te atender.', {
    authorizedLinks: authorizedOutboundLinks,
    maxChars: maxOutputChars
  });
}

const instance = String(payload.instance || '');
const number = String(payload.number || '').replace(/\D/g, '');
const sendEligible = Boolean(payload.sendEligible === true && number);
const sendEligibilityReason = String(payload.sendEligibilityReason || '').trim() || (sendEligible ? 'eligible' : 'blocked');
const duplicateOutbound = sendEligible ? suppressDuplicateOutbound(instance, number, text, payload.messageId) : false;
const sendNumber = (sendEligible && !duplicateOutbound) ? number : '';

// --- Interactive buttons for qualification (Evolution API sendButtons) ---
function shouldSendButtons(data) {
  var intent = String(data.detectedIntent || '').toLowerCase();
  var isFirst = Boolean(data.isFirstInbound);
  var complexity = String(data.messageComplexity || '').toLowerCase();
  return isFirst || intent === 'saudacao' || (intent === 'geral' && complexity === 'simple');
}

function buildButtonsItem(inst, num, data) {
  if (!num || !shouldSendButtons(data)) return null;
  var btnKey = 'buttons:' + inst + ':' + num;
  var isDup = suppressDuplicateOutbound(inst, num, btnKey, data.messageId);
  if (isDup) return null;
  return {
    json: {
      instance: inst,
      number: num,
      sendEligible: true,
      sendEligibilityReason: 'eligible',
      sendMode: 'buttons',
      title: sanitizeOutboundText('Como posso ajudar?', { authorizedLinks: authorizedOutboundLinks, maxChars: 80 }),
      description: sanitizeOutboundText('Selecione uma opcao para agilizar seu atendimento:', { authorizedLinks: authorizedOutboundLinks, maxChars: 120 }),
      footer: sanitizeOutboundText('Classe Couro - Atendimento', { authorizedLinks: authorizedOutboundLinks, maxChars: 80 }),
      buttons: [
        { type: 'reply', displayText: sanitizeOutboundText('Solicitar Orcamento', { authorizedLinks: authorizedOutboundLinks, maxChars: 40 }), id: 'btn_orcamento' },
        { type: 'reply', displayText: sanitizeOutboundText('Ver Catalogo / Produtos', { authorizedLinks: authorizedOutboundLinks, maxChars: 40 }), id: 'btn_catalogo' },
        { type: 'reply', displayText: sanitizeOutboundText('Falar com Vendedor', { authorizedLinks: authorizedOutboundLinks, maxChars: 40 }), id: 'btn_humano' }
      ]
    }
  };
}

function buildOrderChoiceButtonsItem(inst, num, data, delayMs) {
  if (!num || !Boolean(data.sendOrderChoiceButtons)) return null;
  var isDup = suppressDuplicateOutbound(inst, num, '[order-choice-buttons]', `${data.messageId || ''}:order-choice-buttons`);
  if (isDup) return null;
  return {
    json: {
      instance: inst,
      number: num,
      sendEligible: true,
      sendEligibilityReason: 'eligible',
      sendMode: 'buttons',
      delayMs: Number(delayMs || data.orderChoiceButtonsDelayMs || 12200),
      title: sanitizeOutboundText('Como voce prefere seguir com o pedido?', { authorizedLinks: authorizedOutboundLinks, maxChars: 80 }),
      description: sanitizeOutboundText('Escolha se quer montar seu pedido direto no portal B2B ou seguir com o apoio do Eduardo neste canal.', { authorizedLinks: authorizedOutboundLinks, maxChars: 160 }),
      footer: sanitizeOutboundText('Classe Couro - Pedido inicial', { authorizedLinks: authorizedOutboundLinks, maxChars: 80 }),
      buttons: [
        { type: 'reply', displayText: sanitizeOutboundText('Pedir pelo site B2B', { authorizedLinks: authorizedOutboundLinks, maxChars: 40 }), id: 'btn_pedido_b2b' },
        { type: 'reply', displayText: sanitizeOutboundText('Montar com Eduardo', { authorizedLinks: authorizedOutboundLinks, maxChars: 40 }), id: 'btn_pedido_eduardo' }
      ]
    }
  };
}

const outboundItems = [{
  json: {
    instance,
    number: sendNumber,
    sendMode: 'text',
    delayMs: Number(payload.replyDelayMs || 1200),
    replyText: text,
    inboundTextOriginal: String(payload.inboundTextOriginal || ''),
    intent: String(payload.detectedIntent || 'fallback'),
    confidence: Number(payload.cacheHit ? 0.99 : 0.7),
    routeDecision: String(payload.routeDecision || ''),
    messageComplexity: String(payload.messageComplexity || ''),
    sendEligible,
    sendEligibilityReason,
    customerName: String(payload.customerName || '').trim(),
    leadStage: String(payload.leadStage || '').trim(),
    followUpQuestion: String(payload.followUpQuestion || '').trim(),
    productFocusResolved: String(payload.productFocusResolved || '').trim(),
    productCategoryDetected: String(payload.productCategoryDetected || '').trim(),
    customerMemoryUpdate: payload.customerMemoryUpdate && typeof payload.customerMemoryUpdate === 'object'
      ? payload.customerMemoryUpdate
      : {},
    extractedEntities: payload.extractedEntities && typeof payload.extractedEntities === 'object'
      ? payload.extractedEntities
      : {},
    llmProvider: String(payload.llmProvider || '').trim(),
    llmModel: String(payload.llmModel || '').trim(),
    duplicateOutboundSuppressed: duplicateOutbound,
    skipAutomaticSalutation: Boolean(payload.skipAutomaticSalutation)
  }
}];

// Append interactive buttons after text reply on first contact / greetings
var buttonsItem = buildButtonsItem(instance, sendNumber, payload);
if (buttonsItem) {
  outboundItems.push(buttonsItem);
}

if (Boolean(payload.sendSalesBookPdf) && sendNumber) {
  const mediaItem = buildSalesBookMediaItem(instance, sendNumber, payload);
  if (mediaItem) {
    outboundItems.push(mediaItem);

    const staticData = $getWorkflowStaticData('global');
    if (!staticData.customerProfiles) staticData.customerProfiles = {};
    const profile = staticData.customerProfiles[sendNumber] || {};
    profile.salesBookLastSentAt = new Date().toISOString();
    profile.salesBookLastFileName = String(mediaItem.json.fileName || '');
    staticData.customerProfiles[sendNumber] = profile;
  }
}

if (Boolean(payload.sendVitrineAssets) && sendNumber) {
  const vitrinePrelude = 'Para te ajudar a visualizar melhor o potencial da marca no ponto de venda, eu tambem posso te mostrar uma vitrine de referencia. Isso costuma facilitar bastante, porque voce consegue imaginar com mais clareza como os produtos da Classe Couro podem valorizar a apresentacao da sua loja, chamar mais atencao do cliente final e construir uma percepcao mais forte de desejo e qualidade. Quando o mix esta bem montado, a vitrine praticamente comeca a vender antes mesmo da abordagem.';
  const duplicatePrelude = suppressDuplicateOutbound(instance, sendNumber, vitrinePrelude, `${payload.messageId || ''}:vitrine-prelude`);
  if (!duplicatePrelude) {
    outboundItems.push({
      json: {
        instance,
        number: sendNumber,
        sendEligible: true,
        sendEligibilityReason: 'eligible',
        sendMode: 'text',
        delayMs: Number(payload.vitrinePreludeDelayMs || 5200),
        replyText: vitrinePrelude,
        duplicateOutboundSuppressed: false,
        skipAutomaticSalutation: true
      }
    });
  }
  let vitrineDelayCursor = Number(payload.vitrineFirstAssetDelayMs || 7200);
  for (const mediaItem of buildVitrineMediaItems(instance, sendNumber, payload)) {
    mediaItem.json.delayMs = Number(mediaItem.json.delayMs || vitrineDelayCursor);
    vitrineDelayCursor += Number(payload.vitrineDelayStepMs || 1800);
    outboundItems.push(mediaItem);
  }

  var orderChoiceButtonsItem = buildOrderChoiceButtonsItem(instance, sendNumber, payload, vitrineDelayCursor + 800);
  if (orderChoiceButtonsItem) {
    outboundItems.push(orderChoiceButtonsItem);
  }
}

return outboundItems;
