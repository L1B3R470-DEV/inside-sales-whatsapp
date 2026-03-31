const payload = { ...$json };

const text = String(payload.replyText || '').trim();
const inbound = String(payload.inboundTextOriginal || '').trim();

if (!text || !inbound) {
  return [{ json: payload }];
}

try {
  await fetch('http://host.docker.internal:8091/learn-response', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      inboundTextOriginal: inbound,
      replyText: text,
      intent: String(payload.intent || payload.detectedIntent || '').trim(),
      confidence: Number(payload.confidence || 0),
      routeDecision: String(payload.routeDecision || '').trim()
    })
  });
} catch (error) {
  payload.routerLearnError = String(error?.message || error || 'learn_unavailable');
}

return [{ json: payload }];
