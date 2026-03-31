// send-message.js — n8n Code node
// Monta o payload correto para a Evolution API baseado no sendMode
// Colocar ANTES do HTTP Request node de envio
//
// sendMode: 'text'    -> /message/sendText/{instance}
// sendMode: 'media'   -> /message/sendMedia/{instance}
// sendMode: 'buttons' -> /message/sendButtons/{instance}

var EVOLUTION_BASE_URL = $env.EVOLUTION_BASE_URL || 'http://localhost:8080';
var EVOLUTION_INSTANCE = $env.EVOLUTION_INSTANCE || 'ATENDIMENTO_VENDAS_CLEAN';

var items = $input.all();
var results = [];

for (var item of items) {
  var d = item.json;
  var number = String(d.number || '').replace(/\D/g, '');
  var instance = String(d.instance || EVOLUTION_INSTANCE);
  var sendMode = String(d.sendMode || 'text').toLowerCase();

  if (!number) continue;  // Skip suppressed duplicates

  if (sendMode === 'buttons') {
    results.push({
      json: {
        _sendUrl: EVOLUTION_BASE_URL + '/message/sendButtons/' + instance,
        _sendPayload: {
          number: number,
          title: String(d.title || ''),
          description: String(d.description || ''),
          footer: String(d.footer || ''),
          buttons: d.buttons || []
        }
      }
    });
  } else if (sendMode === 'media') {
    results.push({
      json: {
        _sendUrl: EVOLUTION_BASE_URL + '/message/sendMedia/' + instance,
        _sendPayload: {
          number: number,
          mediatype: String(d.mediaType || 'image'),
          media: String(d.media || ''),
          mimetype: String(d.mimeType || 'image/jpeg'),
          caption: String(d.caption || ''),
          fileName: String(d.fileName || '')
        }
      }
    });
  } else {
    // Default: sendText
    results.push({
      json: {
        _sendUrl: EVOLUTION_BASE_URL + '/message/sendText/' + instance,
        _sendPayload: {
          number: number,
          text: String(d.replyText || d.text || '')
        }
      }
    });
  }
}

return results;
