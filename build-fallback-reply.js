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
    .replace(/[\u{1F300}-\u{1FAFF}]/gu, '')
    .replace(/[\u{2600}-\u{27BF}]/gu, '')
    .replace(/\s+/g, ' ')
    .trim();
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
      sendMode: 'media',
      mediaType: 'document',
      media: String(salesBookAsset.mediaBase64 || ''),
      mimeType: String(salesBookAsset.mimeType || payload.salesBookMimeType || 'application/pdf'),
      fileName: String(salesBookAsset.fileName || payload.salesBookFileName || 'BOOK_PROSPECCAO_VENDAS_INTERNAS.pdf'),
      caption: stripEmojiCharacters(String(payload.salesBookCaption || salesBookAsset.caption || '').trim()),
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
        sendMode: 'media',
        mediaType: String(asset.mediaType || 'image'),
        media: String(asset.mediaBase64 || ''),
        mimeType: String(asset.mimeType || 'image/jpeg'),
        caption: stripEmojiCharacters(String(asset.caption || asset.label || '').trim()),
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

let text = String(payload.fallbackText || 'Aqui e o Eduardo, Consultor de Vendas Internas da Classe Couro. Recebi sua mensagem e ja vou te atender.');
text = applySalutation(text, payload);
text = stripEmojiCharacters(text).slice(0, maxOutputChars);

const instance = String(payload.instance || '');
const number = String(payload.number || '').replace(/\D/g, '');
const duplicateOutbound = suppressDuplicateOutbound(instance, number, text, payload.messageId);
const sendNumber = duplicateOutbound ? '' : number;

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
      sendMode: 'buttons',
      title: 'Como posso ajudar?',
      description: 'Selecione uma opcao para agilizar seu atendimento:',
      footer: 'Classe Couro - Atendimento',
      buttons: [
        { type: 'reply', displayText: 'Solicitar Orcamento', id: 'btn_orcamento' },
        { type: 'reply', displayText: 'Ver Catalogo / Produtos', id: 'btn_catalogo' },
        { type: 'reply', displayText: 'Falar com Vendedor', id: 'btn_humano' }
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
    duplicateOutboundSuppressed: duplicateOutbound
  }
}];

// Append interactive buttons after text reply on first contact / greetings
var buttonsItem = buildButtonsItem(instance, number, payload);
if (buttonsItem) {
  outboundItems.push(buttonsItem);
}

if (Boolean(payload.sendSalesBookPdf) && number) {
  const mediaItem = buildSalesBookMediaItem(instance, number, payload);
  if (mediaItem) {
    outboundItems.push(mediaItem);

    const staticData = $getWorkflowStaticData('global');
    if (!staticData.customerProfiles) staticData.customerProfiles = {};
    const profile = staticData.customerProfiles[number] || {};
    profile.salesBookLastSentAt = new Date().toISOString();
    profile.salesBookLastFileName = String(mediaItem.json.fileName || '');
    staticData.customerProfiles[number] = profile;
  }
}

if (Boolean(payload.sendVitrineAssets) && number) {
  for (const mediaItem of buildVitrineMediaItems(instance, number, payload)) {
    outboundItems.push(mediaItem);
  }
}

return outboundItems;
