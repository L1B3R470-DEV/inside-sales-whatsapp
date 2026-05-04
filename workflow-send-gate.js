const items = $input.all();
const staticData = $getWorkflowStaticData('global');

if (!staticData.outboundDispatchState || typeof staticData.outboundDispatchState !== 'object') {
  staticData.outboundDispatchState = {};
}

const state = staticData.outboundDispatchState;
if (!state.strong || typeof state.strong !== 'object') state.strong = {};
if (!state.weak || typeof state.weak !== 'object') state.weak = {};

const STRONG_TTL_MS = 24 * 60 * 60 * 1000;
const WEAK_TTL_MS = 2 * 60 * 1000;
const nowMs = Date.now();

for (const [key, ts] of Object.entries(state.strong)) {
  if (Number(ts || 0) < (nowMs - STRONG_TTL_MS)) delete state.strong[key];
}

for (const [key, ts] of Object.entries(state.weak)) {
  if (Number(ts || 0) < (nowMs - WEAK_TTL_MS)) delete state.weak[key];
}

function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

function stableHash(value) {
  const text = String(value || '');
  let hash = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}

function normalizeNumber(value) {
  return String(value || '').replace(/\D/g, '');
}

function isClosedLabelBlocked(data) {
  return data.closedWhatsappLabelActive === true ||
    data.closedLabelActive === true ||
    String(data.blockReason || '') === 'closed_label_encerrado' ||
    String(data.sendEligibilityReason || '') === 'closed_label_encerrado';
}

function resolveSemanticPayload(data) {
  const mode = String(data.sendMode || 'text').toLowerCase();
  if (mode === 'media') {
    return [
      mode,
      normalizeText(data.caption || ''),
      normalizeText(data.fileName || ''),
      normalizeText(data.mimeType || ''),
      stableHash(String(data.media || '').trim()),
    ].join('|');
  }

  if (mode === 'buttons') {
    const buttons = Array.isArray(data.buttons)
      ? data.buttons.map((btn) => `${normalizeText(btn?.displayText || '')}:${normalizeText(btn?.id || '')}`).join('|')
      : '';
    return [
      mode,
      normalizeText(data.title || ''),
      normalizeText(data.description || ''),
      normalizeText(data.footer || ''),
      buttons,
    ].join('|');
  }

  return [
    mode,
    normalizeText(data.replyText || data.text || ''),
  ].join('|');
}

function buildStrongKey(data) {
  const mode = String(data.sendMode || 'text').toLowerCase();
  const number = normalizeNumber(data.number);
  const explicit = String(
    data.replyHash ||
    data.outboundDedupeKey ||
    data.messageId ||
    data.sourceMessageId ||
    data.quotedMessageId ||
    ''
  ).trim();
  if (!number || !explicit) return '';
  return `${number}|${mode}|${explicit}`;
}

function buildWeakKey(data) {
  const mode = String(data.sendMode || 'text').toLowerCase();
  const number = normalizeNumber(data.number);
  if (!number) return '';
  return `${number}|${resolveSemanticPayload(data)}`;
}

function shouldBypassWeakDuplicate(data) {
  const inbound = normalizeText(data.inboundTextOriginal || data.inboundText || '');
  return /\b(reenvie|reenviar|envie novamente|manda novamente|mandar novamente|preciso novamente)\b/.test(inbound);
}

function buildStructuredLog(data, extra) {
  return {
    event: 'workflow_send_gate',
    executionId: String($execution.id || ''),
    number: normalizeNumber(data.number),
    intent: String(data.intent || data.detectedIntent || ''),
    routeDecision: String(data.routeDecision || ''),
    sendEligible: Boolean(data.sendEligible),
    sendMode: String(data.sendMode || 'text').toLowerCase(),
    replyHash: String(data.replyHash || ''),
    messageId: String(data.messageId || ''),
    ...extra,
  };
}

function validatePayload(data) {
  const number = normalizeNumber(data.number);
  const mode = String(data.sendMode || '').trim().toLowerCase();

  if (!number) throw new Error('Missing number');
  if (!mode) throw new Error('Missing sendMode');

  if (mode === 'media') {
    if (!String(data.media || '').trim()) throw new Error('Invalid asset media');
    if (!String(data.mimeType || '').trim()) throw new Error('Invalid asset mimeType');
  } else if (mode === 'buttons') {
    if (!Array.isArray(data.buttons) || data.buttons.length === 0) throw new Error('Missing buttons');
    const invalid = data.buttons.some((btn) => !String(btn?.displayText || '').trim() || !String(btn?.id || '').trim());
    if (invalid) throw new Error('Invalid buttons payload');
  } else {
    const text = String(data.replyText || data.text || '').trim();
    if (!text) throw new Error('Missing reply text');
  }
}

const output = [];

for (const item of items) {
  const data = { ...item.json };
  const logBase = buildStructuredLog(data, {});

  if (isClosedLabelBlocked(data)) {
    console.log(JSON.stringify(buildStructuredLog(data, {
      status: 'skip_closed_label_encerrado',
      sendEligibilityReason: 'closed_label_encerrado',
    })));
    output.push({
      json: {
        ...data,
        sendEligible: false,
        sendEligibilityReason: 'closed_label_encerrado',
        outboundGuardStatus: 'skip_closed_label_encerrado',
      },
    });
    continue;
  }

  if (data.sendEligible !== true) {
    console.log(JSON.stringify(buildStructuredLog(data, {
      status: 'skip_not_eligible',
      sendEligibilityReason: String(data.sendEligibilityReason || ''),
    })));
    output.push({
      json: {
        ...data,
        outboundGuardStatus: 'skip_not_eligible',
      },
    });
    continue;
  }

  validatePayload(data);

  const strongKey = buildStrongKey(data);
  const weakKey = buildWeakKey(data);
  const strongSeenAt = strongKey ? Number(state.strong[strongKey] || 0) : 0;
  const weakSeenAt = weakKey ? Number(state.weak[weakKey] || 0) : 0;

  if (strongSeenAt && (nowMs - strongSeenAt) < STRONG_TTL_MS) {
    console.log(JSON.stringify(buildStructuredLog(data, {
      status: 'suppressed_duplicate_strong',
      dedupeKey: strongKey,
      dedupeLevel: 'strong',
    })));
    output.push({
      json: {
        ...data,
        sendEligible: false,
        sendEligibilityReason: 'duplicate_outbound_strong',
        duplicateOutboundSuppressed: true,
        outboundGuardStatus: 'suppressed_duplicate_strong',
      },
    });
    continue;
  }

  if (weakSeenAt && (nowMs - weakSeenAt) < WEAK_TTL_MS && !shouldBypassWeakDuplicate(data)) {
    console.log(JSON.stringify(buildStructuredLog(data, {
      status: 'suppressed_duplicate_weak',
      dedupeKey: weakKey,
      dedupeLevel: 'weak',
    })));
    output.push({
      json: {
        ...data,
        sendEligible: false,
        sendEligibilityReason: 'duplicate_outbound_weak',
        duplicateOutboundSuppressed: true,
        outboundGuardStatus: 'suppressed_duplicate_weak',
      },
    });
    continue;
  }

  if (strongKey) state.strong[strongKey] = nowMs;
  if (weakKey) state.weak[weakKey] = nowMs;

  output.push({
    json: {
      ...data,
      outboundDedupeStrongKey: strongKey,
      outboundDedupeWeakKey: weakKey,
      outboundGuardStatus: 'ready',
    },
  });

  console.log(JSON.stringify(buildStructuredLog(data, {
    status: 'ready',
    dedupeKey: strongKey || weakKey,
    dedupeLevel: strongKey ? 'strong' : 'weak',
  })));
}

return output;
