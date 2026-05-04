const body = $json.body ?? $json;
const event = String(body.event || '').toUpperCase().replace(/\./g, '_');
const staticData = $getWorkflowStaticData('global');

const CLOSED_WHATSAPP_LABEL_NAMES = new Set(['encerrado']);
// Current Evolution label id for "ENCERRADO" in ATENDIMENTO_VENDAS_CLEAN.
const CLOSED_WHATSAPP_LABEL_IDS = new Set(['21']);

function normalizeLabelText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

function digitsOnly(value) {
  return String(value || '').replace(/\D/g, '');
}

function cleanJid(value) {
  return String(value || '')
    .replace(/:\d+(?=@)/g, '')
    .toLowerCase()
    .trim();
}

function closedContactKeysFromJid(value) {
  const jid = cleanJid(value);
  const keys = new Set();
  if (jid) keys.add(jid);
  const digits = digitsOnly(jid.replace(/@s\.whatsapp\.net|@g\.us|@lid/g, ''));
  if (digits) keys.add(digits);
  return [...keys];
}

function ensureClosedLabelRegistry() {
  if (!staticData.closedByWhatsappLabel || typeof staticData.closedByWhatsappLabel !== 'object') {
    staticData.closedByWhatsappLabel = {};
  }
  return staticData.closedByWhatsappLabel;
}

function isClosedWhatsappLabel(labelId, labelName) {
  const id = String(labelId || '').trim();
  const name = normalizeLabelText(labelName);
  return (id && CLOSED_WHATSAPP_LABEL_IDS.has(id)) || (name && CLOSED_WHATSAPP_LABEL_NAMES.has(name));
}

function labelAssociationIsRemove(action) {
  const norm = normalizeLabelText(action);
  return ['remove', 'removed', 'delete', 'deleted', 'desassociar', 'desassociado', 'unlabel'].includes(norm);
}

function collectLabelEntries(value, out = []) {
  if (!value) return out;
  if (Array.isArray(value)) {
    for (const item of value) collectLabelEntries(item, out);
    return out;
  }
  if (typeof value === 'object') {
    const id = value.labelId ?? value.id ?? value.predefinedId ?? '';
    const name = value.labelName ?? value.name ?? value.text ?? value.title ?? '';
    if (id || name) out.push({ id: String(id || '').trim(), name: String(name || '').trim() });
    for (const [key, child] of Object.entries(value)) {
      if (/label|tag|etiqueta/i.test(key)) collectLabelEntries(child, out);
    }
    return out;
  }
  if (typeof value === 'string') out.push({ id: '', name: value });
  return out;
}

function payloadHasClosedWhatsappLabel(...sources) {
  for (const source of sources) {
    const entries = collectLabelEntries(source);
    if (entries.some((entry) => isClosedWhatsappLabel(entry.id, entry.name))) return true;
  }
  return false;
}

function readClosedLabelState(keys) {
  const registry = ensureClosedLabelRegistry();
  for (const key of keys) {
    const clean = cleanJid(key) || digitsOnly(key);
    if (clean && registry[clean]) return registry[clean];
  }
  return null;
}

// --- Handle non-message events: ignore for auto-reply flow ---
if (event === 'MESSAGES_UPDATE') {
  return [];
}

if (event === 'PRESENCE_UPDATE') {
  var pData = body.data ?? body;
  return [{
    json: {
      _eventType: 'presence',
      instance: body.instance || body.instanceName || '',
      remoteJid: String(pData.id || pData.remoteJid || ''),
      presence: String(pData.presences ? Object.values(pData.presences)[0]?.lastKnownPresence || '' : pData.presence || ''),
      timestamp: Date.now()
    }
  }];
}

if (event === 'CALL') {
  var cData = body.data ?? body;
  return [{
    json: {
      _eventType: 'call',
      instance: body.instance || body.instanceName || '',
      remoteJid: String(cData.from || cData.remoteJid || ''),
      callId: String(cData.id || ''),
      status: String(cData.status || ''),
      timestamp: Date.now()
    }
  }];
}

if (event === 'CONNECTION_UPDATE') {
  var connData = body.data ?? body;
  return [{
    json: {
      _eventType: 'connection',
      instance: body.instance || body.instanceName || '',
      state: String(connData.state || connData.status || ''),
      timestamp: Date.now()
    }
  }];
}

if (event === 'LABELS_ASSOCIATION') {
  var lData = body.data ?? body;
  const labelId = String(lData.labelId ?? lData.id ?? lData.label?.id ?? '').trim();
  const labelName = String(lData.labelName ?? lData.name ?? lData.label?.name ?? '').trim();
  const remoteJid = cleanJid(lData.chatId || lData.remoteJid || lData.jid || '');
  const action = String(lData.type || lData.action || '').trim();
  const registry = ensureClosedLabelRegistry();

  if (remoteJid && isClosedWhatsappLabel(labelId, labelName)) {
    const keys = closedContactKeysFromJid(remoteJid);
    if (labelAssociationIsRemove(action)) {
      for (const key of keys) delete registry[key];
    } else {
      const state = {
        active: true,
        labelId,
        labelName: labelName || 'ENCERRADO',
        remoteJid,
        updatedAt: new Date().toISOString(),
        source: 'LABELS_ASSOCIATION'
      };
      for (const key of keys) registry[key] = state;
    }
    console.log(JSON.stringify({
      event: 'closed_label_registry_update',
      remoteJid,
      labelId,
      labelName: labelName || 'ENCERRADO',
      action: labelAssociationIsRemove(action) ? 'remove' : 'add'
    }));
  }

  // Label-only events must never enter the auto-reply flow.
  return [];
}

// Only process MESSAGES_UPSERT from here on
if (event && !['MESSAGES_UPSERT'].includes(event)) {
  return [];
}

const payload = body.data ?? body;
const key = payload.key ?? {};
const messageStatus = String(payload.status ?? body.status ?? '').toUpperCase().trim();
const contextInfo =
  payload.message?.extendedTextMessage?.contextInfo ??
  payload.message?.imageMessage?.contextInfo ??
  payload.message?.videoMessage?.contextInfo ??
  payload.message?.documentMessage?.contextInfo ??
  payload.message?.audioMessage?.contextInfo ??
  payload.contextInfo ??
  {};
const quotedMessage = contextInfo?.quotedMessage ?? {};

const fromMeRaw = key.fromMe ?? payload.fromMe ?? body.fromMe;
const fromMe = fromMeRaw === true || String(fromMeRaw).toLowerCase() === 'true' || Number(fromMeRaw) === 1;
if (fromMe) {
  return [];
}

const remoteJid = String(key.remoteJid ?? body.sender ?? '')
  .replace(/:\d+(?=@)/g, '')
  .toLowerCase();
if (!remoteJid || remoteJid.endsWith('@g.us') || remoteJid === 'status@broadcast') {
  return [];
}

const messageId = String(
  key.id ??
  payload.messageId ??
  payload.id ??
  body.messageId ??
  ''
).trim();

// Safety: ignore synthetic test payload IDs to avoid accidental real sends.
if (/^(MSG-|TEST-|DEBUG-)/i.test(messageId)) {
  const remoteNumberForTest = remoteJid
    .replace(/@s\.whatsapp\.net|@g\.us|@lid/g, '')
    .replace(/\D/g, '');
  const allowedTestNumber = '557588340000';
  if (remoteNumberForTest !== allowedTestNumber) {
    return [];
  }
}

if (!staticData.processedMessageIds) staticData.processedMessageIds = {};
if (!staticData.recentMessageFingerprints) staticData.recentMessageFingerprints = {};

const nowMs = Date.now();
const ttlMs = 1000 * 60 * 60 * 36;
for (const [id, ts] of Object.entries(staticData.processedMessageIds)) {
  if (Number(ts || 0) < (nowMs - ttlMs)) delete staticData.processedMessageIds[id];
}
for (const [id, info] of Object.entries(staticData.recentMessageFingerprints)) {
  const seenAt = typeof info === 'object' ? Number(info.seenAt || 0) : Number(info || 0);
  if (seenAt < (nowMs - (1000 * 60 * 10))) delete staticData.recentMessageFingerprints[id];
}

if (messageId) {
  const dedupeKey = `${String(body.instance ?? body.instanceName ?? '')}:${messageId}`;
  if (staticData.processedMessageIds[dedupeKey]) {
    return [];
  }
  staticData.processedMessageIds[dedupeKey] = nowMs;
}

let text =
  payload.message?.conversation ??
  payload.message?.extendedTextMessage?.text ??
  payload.message?.imageMessage?.caption ??
  payload.message?.videoMessage?.caption ??
  payload.message?.documentMessage?.caption ??
  payload.message?.speechToText ??
  payload.message?.buttonsResponseMessage?.selectedDisplayText ??
  payload.message?.listResponseMessage?.title ??
  payload.message?.listResponseMessage?.singleSelectReply?.selectedRowId ??
  '';

text = String(text || '').trim();
const audioMessage =
  payload.message?.audioMessage ??
  payload.message?.viewOnceMessageV2?.message?.audioMessage ??
  {};
const imageMessage =
  payload.message?.imageMessage ??
  payload.message?.viewOnceMessage?.message?.imageMessage ??
  payload.message?.viewOnceMessageV2?.message?.imageMessage ??
  {};
const audioUrl = String(
  audioMessage?.url ??
  audioMessage?.mediaUrl ??
  payload.mediaUrl ??
  payload.message?.mediaUrl ??
  ''
).trim();
const audioMimeType = String(
  audioMessage?.mimetype ??
  audioMessage?.mimeType ??
  payload.mimetype ??
  ''
).trim();
const audioBase64 = String(
  payload.base64 ??
  payload.message?.base64 ??
  audioMessage?.base64 ??
  ''
).trim();
const hasInboundAudio = Boolean(audioUrl || audioBase64 || Object.keys(audioMessage || {}).length > 0);
const imageUrl = String(
  imageMessage?.url ??
  imageMessage?.mediaUrl ??
  payload.mediaUrl ??
  payload.message?.mediaUrl ??
  ''
).trim();
const imageMimeType = String(
  imageMessage?.mimetype ??
  imageMessage?.mimeType ??
  payload.mimetype ??
  ''
).trim();
const imageBase64 = String(
  payload.base64 ??
  payload.message?.base64 ??
  imageMessage?.base64 ??
  ''
).trim();
const hasInboundImage = Boolean(imageUrl || imageBase64 || Object.keys(imageMessage || {}).length > 0);
const quotedText =
  quotedMessage?.conversation ??
  quotedMessage?.extendedTextMessage?.text ??
  quotedMessage?.imageMessage?.caption ??
  quotedMessage?.videoMessage?.caption ??
  quotedMessage?.documentMessage?.caption ??
  '';
const quotedMessageId = String(
  contextInfo?.stanzaId ??
  contextInfo?.quotedMessageId ??
  ''
).trim();
if (!text && hasInboundImage) {
  text = '[imagem recebida]';
}
if (!text && !hasInboundAudio && !hasInboundImage) {
  return [];
}

// Some inbound messages from Android arrive with status ERROR in the webhook
// even though they contain valid customer text. Ignore only empty/system echoes.
if (messageStatus === 'ERROR' && !text) {
  return [];
}
const normalizedText = text
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .replace(/\s+/g, ' ')
  .trim();
const fingerprint = `${String(body.instance ?? body.instanceName ?? '')}:${remoteJid}:${normalizedText}`;
const messageTimestamp = Number(payload.messageTimestamp || body.messageTimestamp || 0);
const previousFingerprint = staticData.recentMessageFingerprints[fingerprint];
if (previousFingerprint) {
  const previousSeenAt = typeof previousFingerprint === 'object'
    ? Number(previousFingerprint.seenAt || 0)
    : Number(previousFingerprint || 0);
  const previousMsgTs = typeof previousFingerprint === 'object'
    ? Number(previousFingerprint.msgTs || 0)
    : 0;
  const withinShortWindow = (nowMs - previousSeenAt) < (1000 * 15);
  const sameMessageTimestamp = Boolean(messageTimestamp && previousMsgTs && (messageTimestamp === previousMsgTs));

  // Only suppress by text fingerprint when there is strong evidence of duplicate delivery.
  if (!messageId && withinShortWindow) {
    return [];
  }
  if (messageId && sameMessageTimestamp && withinShortWindow) {
    return [];
  }

  const substantiveRepeatWindow = (nowMs - previousSeenAt) < (1000 * 120);
  const looksSubstantive = normalizedText.length >= 24;
  const looksCommercialRequest = /book|vitrine|pedido|catalogo|cat[aá]logo|orcamento|or[cç]amento|site b2b|portal b2b|pedido inicial/.test(normalizedText);
  if (substantiveRepeatWindow && (looksSubstantive || looksCommercialRequest)) {
    return [];
  }
}
staticData.recentMessageFingerprints[fingerprint] = { seenAt: nowMs, msgTs: messageTimestamp || 0 };

const isLid = remoteJid.endsWith('@lid');
const number = isLid
  ? ''
  : remoteJid
      .replace(/@s\.whatsapp\.net|@g\.us/g, '')
      .replace(/\D/g, '');
const senderPhoneCandidate = String(
  payload.senderPn ??
  payload.sender_pn ??
  payload.senderPhone ??
  payload.sender_phone ??
  body.senderPn ??
  body.sender_pn ??
  body.senderPhone ??
  body.sender_phone ??
  ''
).trim();
const participantJidCandidate = String(
  key.participant ??
  payload.participant ??
  payload.participantJid ??
  body.participant ??
  contextInfo?.participant ??
  ''
).replace(/:\d+(?=@)/g, '').toLowerCase().trim();
const senderJidCandidate = String(
  payload.senderJid ??
  payload.senderLid ??
  payload.fromJid ??
  body.senderJid ??
  body.senderLid ??
  ''
).replace(/:\d+(?=@)/g, '').toLowerCase().trim();

const closedLabelKeys = [
  remoteJid,
  number,
  senderPhoneCandidate,
  participantJidCandidate,
  senderJidCandidate
].flatMap((value) => {
  const keys = closedContactKeysFromJid(value);
  const digits = digitsOnly(value);
  if (digits) keys.push(digits);
  return keys;
});
const closedLabelState = readClosedLabelState(closedLabelKeys);
const payloadClosedLabel = payloadHasClosedWhatsappLabel(
  body.labels,
  body.label,
  body.chatLabels,
  body.contactLabels,
  payload.labels,
  payload.label,
  payload.chatLabels,
  payload.contactLabels
);

if (closedLabelState || payloadClosedLabel) {
  console.log(JSON.stringify({
    event: 'closed_label_message_suppressed',
    instance: body.instance ?? body.instanceName ?? '',
    remoteJid,
    number,
    messageId,
    label: 'ENCERRADO'
  }));
  return [];
}

return [{
  json: {
    instance: body.instance ?? body.instanceName ?? '',
    remoteJid,
    isLid,
    number,
    pushName: payload.pushName ?? body.pushName ?? 'Cliente',
    inboundText: text,
    inboundAudio: hasInboundAudio ? {
      url: audioUrl,
      mimeType: audioMimeType,
      base64: audioBase64,
      fileName: String(audioMessage?.fileName || '').trim(),
      ptt: Boolean(audioMessage?.ptt),
      seconds: Number(audioMessage?.seconds || 0),
      hasAudio: true
    } : null,
    inboundImage: hasInboundImage ? {
      url: imageUrl,
      mimeType: imageMimeType,
      base64: imageBase64,
      fileName: String(imageMessage?.fileName || '').trim(),
      caption: String(imageMessage?.caption || '').trim(),
      hasImage: true
    } : null,
    inboundMedia: hasInboundImage ? { type: 'image', hasMedia: true } : null,
    messageId,
    quotedText: String(quotedText || '').trim(),
    quotedMessageId,
    senderPhoneCandidate,
    participantJidCandidate,
    senderJidCandidate
  }
}];
