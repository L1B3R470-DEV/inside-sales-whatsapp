const body = $json.body ?? $json;

function cleanNumber(value) {
  return String(value || '').replace(/\D/g, '');
}

const number = cleanNumber(body.number);
if (!number) {
  return [];
}

const sendMode = String(body.sendMode || (body.media ? 'media' : 'text')).toLowerCase() === 'media'
  ? 'media'
  : 'text';

return [{
  json: {
    instance: String(body.instance || 'ATENDIMENTO_VENDAS_CLEAN').trim(),
    number,
    sendMode,
    replyText: String(body.replyText || body.text || '').trim(),
    mediaType: String(body.mediaType || body.mediatype || 'image').trim(),
    mimeType: String(body.mimeType || body.mimetype || 'image/jpeg').trim(),
    media: String(body.media || '').trim(),
    caption: String(body.caption || '').trim(),
    fileName: String(body.fileName || body.filename || '').trim(),
  }
}];
