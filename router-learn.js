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
      needsHuman: Boolean(payload.needsHuman)
    })
  });
} catch (error) {
  payload.routerLearnError = String(error?.message || error || 'learn_unavailable');
}

return [{ json: payload }];
