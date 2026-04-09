const payload = { ...$json };
const ROUTER_BASE_URL = String($env.ROUTER_BASE_URL || 'http://router:8091').replace(/\/$/, '');
const topology = {
  operationalHostRole: 'PC_CLS',
  operationalHostIp: '100.113.13.27',
  operationalDockerHostRole: 'PC_CLS',
  operationalDockerHostIp: '100.113.13.27',
  interactiveHostRole: 'PC_LBN',
  interactiveHostIp: '100.101.106.95',
  interactiveModeOnly: true,
  rejectLbnAsRuntime: true,
  rejectLbnDocker: true
};

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

function stripUnauthorizedLinks(value) {
  return String(value || '')
    .replace(/\bhttps?:\/\/[^\s<>()]+/gi, '')
    .replace(/\bwww\.[^\s<>()]+/gi, '')
    .replace(/\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?:\/[^\s<>()]*)?/gi, '');
}

function sanitizeOutboundText(value) {
  return stripEmojiCharacters(stripUnauthorizedLinks(String(value || '').replace(/\r\n?/g, '\n')))
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

const text = sanitizeOutboundText(payload.replyText || '');
const inbound = String(payload.inboundTextOriginal || '').trim();

if (!text || !inbound) {
  return [{ json: payload }];
}

try {
  await fetch(`${ROUTER_BASE_URL}/learn-response`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      number: String(payload.number || payload.customerNumber || '').trim(),
      contactKey: String(payload.contactKey || payload.number || payload.customerNumber || '').trim(),
      customerName: String(payload.customerName || '').trim(),
      inboundTextOriginal: inbound,
      replyText: text,
      intent: String(payload.intent || payload.detectedIntent || '').trim(),
      confidence: Number(payload.confidence || 0),
      routeDecision: String(payload.routeDecision || '').trim(),
      leadStage: String(payload.leadStage || '').trim(),
      followUpQuestion: String(payload.followUpQuestion || '').trim(),
      productFocusResolved: String(payload.productFocusResolved || '').trim(),
      productCategoryDetected: String(payload.productCategoryDetected || '').trim(),
      customerMemoryUpdate: payload.customerMemoryUpdate && typeof payload.customerMemoryUpdate === 'object'
        ? payload.customerMemoryUpdate
        : {},
      extractedEntities: payload.extractedEntities && typeof payload.extractedEntities === 'object'
        ? payload.extractedEntities
        : (payload.llmStructuredData && typeof payload.llmStructuredData === 'object' ? payload.llmStructuredData : {}),
      llmProvider: String(payload.llmProvider || '').trim(),
      llmModel: String(payload.llmModel || '').trim(),
      needsHuman: Boolean(payload.needsHuman),
      topology
    })
  });
} catch (error) {
  payload.routerLearnError = String(error?.message || error || 'learn_unavailable');
}

return [{ json: { ...payload, topology } }];
