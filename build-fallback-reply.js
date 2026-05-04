const payload = $json;
const maxOutputChars = Number(payload.maxOutputChars || 280);
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
    if (prev === '@' || prev === ':' || prev === '/') return match;
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

function escapeRegExp(value) {
  return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function sentenceTrim(text, maxSentences, maxChars) {
  const raw = String(text || '').trim();
  if (!raw) return '';
  const parts = raw
    .replace(/\s+/g, ' ')
    .split(/(?<=[.!?])\s+/)
    .map((x) => x.trim())
    .filter(Boolean);
  const limited = parts.slice(0, Math.max(1, Number(maxSentences || 3))).join(' ').trim();
  if (!maxChars || limited.length <= maxChars) return limited;
  const sliced = limited.slice(0, maxChars);
  const cut = Math.max(sliced.lastIndexOf('.'), sliced.lastIndexOf('?'), sliced.lastIndexOf('!'));
  return (cut >= 80 ? sliced.slice(0, cut + 1) : sliced).trim();
}

function dropLocationSentences(text) {
  const parts = String(text || '')
    .replace(/\s+/g, ' ')
    .split(/(?<=[.!?])\s+/)
    .map((x) => x.trim())
    .filter(Boolean);
  return parts
    .filter((part) => {
      const norm = normalizeForDedupe(part);
      const hasLeadingCityPattern = /^(?:para|em|na|no)\s+[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ][\p{L}.-]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ][\p{L}.-]+){0,2}(?:,|\s)/u.test(part);
      return !/\b(praca|mercado de|mercado local|na sua regiao|para sua regiao|na regiao|na sua cidade|para sua cidade|perfil local|funcione bem em|aderencia em|na cidade de|na cidade)\b/.test(norm)
        && !hasLeadingCityPattern;
    })
    .join(' ')
    .trim();
}

function sanitizeCommercialStyle(value, ctx) {
  let text = String(value || '');
  if (!text) return '';
  text = text.replace(/\r\n?/g, '\n');
  text = text.replace(/---[\s\S]*$/g, ' ');
  text = text.replace(/\*+/g, '');
  const lines = text
    .split('\n')
    .map((x) => x.trim())
    .filter(Boolean)
    .filter((line) => {
      const norm = normalizeForDedupe(line);
      if (norm === 'eduardo silva' || norm === 'eduardo vinhas') return false;
      if (norm.includes('consultor de vendas internas') && norm.length < 90) return false;
      if (/^\|\s*classe\b/i.test(line) && norm.length < 40) return false;
      return true;
    });
  text = lines.join(' ');
  text = text.replace(/\bClasse\s+Couro\b/gi, 'Classe');
  text = text.replace(/\bEduardo\s+Silva\b/gi, 'Eduardo Vinhas');
  text = text.replace(/^aqui e o eduardo(?:\s+vinhas|\s+silva)?(?:,?\s*consultor de vendas internas(?: da classe(?: couro)?)?)?[.!:\-\s]*/i, '');
  text = text.replace(/\b(bolsas?|carteiras?|cintos?|mochilas?|kits?|acessorios?|produtos?|modelos?)\s+(femininas?|masculinas?|feminino|masculino)\b/gi, '$1');
  text = text.replace(/\b(femininas?|masculinas?|feminino|masculino|premium)\b/gi, '');
  const cityCandidates = [];
  for (const candidate of [ctx?.city, ctx?.cidade, ctx?.cityHint]) {
    const city = String(candidate || '').trim();
    if (city && city.length >= 3) cityCandidates.push(city);
  }
  for (const city of [...new Set(cityCandidates)]) {
    const escaped = escapeRegExp(city);
    text = text.replace(new RegExp(`\\b(?:em|para|de|na|no)\\s+${escaped}\\b`, 'gi'), '');
    text = text.replace(new RegExp(`\\b${escaped}\\b`, 'gi'), '');
  }
  text = text.replace(/\b(?:em|para|na|no)\s+[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ][\p{L}.-]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ][\p{L}.-]+){0,2}\b/gu, '');
  text = dropLocationSentences(text);
  const sentences = text
    .replace(/\s+/g, ' ')
    .split(/(?<=[.!?])\s+/)
    .map((x) => x.trim())
    .filter(Boolean);
  const kept = [];
  let cnpjSeen = false;
  for (const sentence of sentences) {
    const norm = normalizeForDedupe(sentence);
    const hasCnpj = norm.includes('cnpj');
    if (hasCnpj && cnpjSeen) continue;
    if (cnpjSeen && /aguardo seu cnpj|aguardo o cnpj|para darmos continuidade|para prosseguirmos|com essa informacao|margens? de lucro|previsao de giro|mix de modelos/.test(norm)) {
      continue;
    }
    kept.push(sentence);
    if (hasCnpj) cnpjSeen = true;
  }
  text = kept.join(' ').replace(/\s{2,}/g, ' ').trim();
  return sentenceTrim(text, 3, Number(ctx?.maxOutputChars || 420));
}

function suppressDuplicateOutbound(instance, number, replyText, messageId) {
  const staticData = $getWorkflowStaticData('global');
  if (!staticData.outboundRecent) staticData.outboundRecent = {};

  const nowMs = Date.now();
  const ttlMs = 1000 * 60 * 10;
  for (const [k, ts] of Object.entries(staticData.outboundRecent)) {
    if (Number(ts || 0) < (nowMs - ttlMs)) delete staticData.outboundRecent[k];
  }

  const key = `${String(instance || '')}:${String(number || '')}:${normalizeForDedupe(replyText)}:${String(messageId || '')}`;
  const lastTs = Number(staticData.outboundRecent[key] || 0);
  if (lastTs && (nowMs - lastTs) < (1000 * 45)) {
    return true;
  }

  staticData.outboundRecent[key] = nowMs;
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
  const cleanText = stripLeadingSalutation(text);
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

  if (shouldSalute) {
    const salutation = composeSalutation(
      number,
      String(customerName || ''),
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

function isValidCnpjDigits(value) {
  const digits = String(value || '').replace(/\D/g, '');
  if (digits.length !== 14) return false;
  if (/^(\d)\1{13}$/.test(digits)) return false;
  const calc = (base, factors) => {
    const sum = factors.reduce((acc, factor, idx) => acc + Number(base[idx] || 0) * factor, 0);
    const rem = sum % 11;
    return rem < 2 ? 0 : 11 - rem;
  };
  const first = calc(digits, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  const second = calc(digits, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  return first === Number(digits[12]) && second === Number(digits[13]);
}

function extractCnpjFromValue(value) {
  const raw = String(value || '');
  const candidates = [];
  const pushDigits = (candidate) => {
    const digits = String(candidate || '').replace(/\D/g, '');
    if (digits.length >= 14) candidates.push(digits.slice(0, 14));
  };
  for (const match of raw.matchAll(/cnpj\D{0,30}([0-9][0-9.\-\/\s]{13,30})/gi)) pushDigits(match[1]);
  for (const match of raw.matchAll(/\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}/g)) pushDigits(match[0]);
  const allDigits = raw.replace(/\D/g, '');
  if (allDigits.length === 14) candidates.push(allDigits);
  if (allDigits.length > 14) {
    for (let i = 0; i <= allDigits.length - 14; i++) candidates.push(allDigits.slice(i, i + 14));
  }
  const unique = [...new Set(candidates.filter((c) => c.length === 14))];
  return unique.find((c) => isValidCnpjDigits(c)) || unique[0] || '';
}

function normalizeB2BCredentials(replyText, data) {
  let out = String(replyText || '').trim();
  if (!/portal b2b|acesso ao/i.test(out)) return out;
  const cnpj = [
    data?.inboundTextOriginal,
    data?.companyCnpj,
    data?.lastCnpj,
    out
  ].map(extractCnpjFromValue).find(Boolean);
  if (!cnpj) return out;
  const credentials = `LOGIN: ${cnpj}\nSENHA: ${cnpj.slice(0, 8)}`;
  if (/login\s*:|senha\s+inicial|senha\s*:/i.test(out)) {
    return out
      .replace(/Login:\s*CNPJ\s*\d{14}\.?\s*Senha inicial:\s*\d{8}\.?/i, credentials)
      .replace(/LOGIN:\s*\d{14}\s*SENHA:\s*\d{8}/i, credentials)
      .trim();
  }
  return `${out}\n${credentials}`;
}

let text = String(payload.fallbackText || 'Recebi sua mensagem e ja vou te atender.');
text = applySalutation(text, payload);
text = sanitizeCommercialStyle(text, payload);
const authorizedOutboundLinks = getAuthorizedOutboundLinks(payload);
text = sanitizeOutboundText(text, {
  authorizedLinks: authorizedOutboundLinks,
  maxChars: maxOutputChars
});
if (!text) {
  text = sanitizeOutboundText('Recebi sua mensagem e ja vou te atender.', {
    authorizedLinks: authorizedOutboundLinks,
    maxChars: maxOutputChars
  });
}
text = normalizeB2BCredentials(text, payload);

const instance = String(payload.instance || '');
const number = String(payload.number || '').replace(/\D/g, '');
const sendEligible = Boolean(payload.sendEligible === true && number);
const sendEligibilityReason = String(payload.sendEligibilityReason || '').trim() || (sendEligible ? 'eligible' : 'blocked');
const duplicateOutbound = sendEligible ? suppressDuplicateOutbound(instance, number, text, payload.messageId) : false;
const sendNumber = (sendEligible && !duplicateOutbound) ? number : '';

// --- Interactive buttons for qualification (Evolution API sendButtons) ---
function shouldSendButtons(data) {
  const outboundText = String(data.fallbackText || data.replyText || '').toLowerCase();
  if (
    outboundText.includes('portal b2b') ||
    outboundText.includes('login:') ||
    String(data.orderChoiceSelection || '').trim().toLowerCase() === 'b2b' ||
    String(data.b2bLinkSentAt || '').trim()
  ) {
    return false;
  }
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
      footer: sanitizeOutboundText('Classe - Atendimento', { authorizedLinks: authorizedOutboundLinks, maxChars: 80 }),
      buttons: [
        { type: 'reply', displayText: sanitizeOutboundText('Solicitar Orcamento', { authorizedLinks: authorizedOutboundLinks, maxChars: 40 }), id: 'btn_orcamento' },
        { type: 'reply', displayText: sanitizeOutboundText('Ver Catalogo / Produtos', { authorizedLinks: authorizedOutboundLinks, maxChars: 40 }), id: 'btn_catalogo' },
        { type: 'reply', displayText: sanitizeOutboundText('Falar com Vendedor', { authorizedLinks: authorizedOutboundLinks, maxChars: 40 }), id: 'btn_humano' }
      ]
    }
  };
}

const outboundItems = [{
  json: {
    instance,
    number: sendNumber,
    sendMode: 'text',
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
    duplicateOutboundSuppressed: duplicateOutbound
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
  for (const mediaItem of buildVitrineMediaItems(instance, sendNumber, payload)) {
    outboundItems.push(mediaItem);
  }
}

return outboundItems;
