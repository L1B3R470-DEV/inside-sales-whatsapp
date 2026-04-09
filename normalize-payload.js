const body = $json.body ?? $json;
const event = String(body.event || '').toUpperCase().replace(/\./g, '_');

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
  return [{
    json: {
      _eventType: 'label',
      instance: body.instance || body.instanceName || '',
      remoteJid: String(lData.chatId || lData.remoteJid || ''),
      labelId: String(lData.labelId || ''),
      action: String(lData.type || lData.action || ''),
      timestamp: Date.now()
    }
  }];
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

const staticData = $getWorkflowStaticData('global');
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
if (!text && !hasInboundAudio) {
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
    messageId,
    quotedText: String(quotedText || '').trim(),
    quotedMessageId
  }
}];
