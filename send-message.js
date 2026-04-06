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

function getAuthorizedOutboundLinks(data) {
  var values = [];
  if (Array.isArray(data.authorizedLinks)) values = values.concat(data.authorizedLinks);
  if (Array.isArray(data.operatorAuthorizedLinks)) values = values.concat(data.operatorAuthorizedLinks);
  if (Array.isArray(data.allowedLinks)) values = values.concat(data.allowedLinks);
  var allow = {};
  for (var i = 0; i < values.length; i++) {
    var key = normalizeAuthorizedLink(values[i]);
    if (key) allow[key] = true;
  }
  return allow;
}

function stripUnauthorizedLinks(value, authorizedLinks) {
  var allow = authorizedLinks || {};
  var keepOrDrop = function(match, offset, source) {
    var prev = offset > 0 ? String(source || '').charAt(offset - 1) : '';
    if (prev === '@') return match;
    return allow[normalizeAuthorizedLink(match)] ? match : '';
  };

  return String(value || '')
    .replace(/\bhttps?:\/\/[^\s<>()]+/gi, keepOrDrop)
    .replace(/\bwww\.[^\s<>()]+/gi, keepOrDrop)
    .replace(/\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?:\/[^\s<>()]*)?/gi, keepOrDrop);
}

function sanitizeOutboundText(value, authorizedLinks) {
  return stripEmojiCharacters(stripUnauthorizedLinks(String(value || '').replace(/\r\n?/g, '\n'), authorizedLinks))
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

for (var item of items) {
  var d = item.json;
  var number = String(d.number || '').replace(/\D/g, '');
  var instance = String(d.instance || EVOLUTION_INSTANCE);
  var sendMode = String(d.sendMode || 'text').toLowerCase();
  var authorizedLinks = getAuthorizedOutboundLinks(d);

  if (!number) continue;  // Skip suppressed duplicates

  if (sendMode === 'buttons') {
    results.push({
      json: {
        _sendUrl: EVOLUTION_BASE_URL + '/message/sendButtons/' + instance,
        _sendPayload: {
          number: number,
          title: sanitizeOutboundText(String(d.title || ''), authorizedLinks),
          description: sanitizeOutboundText(String(d.description || ''), authorizedLinks),
          footer: sanitizeOutboundText(String(d.footer || ''), authorizedLinks),
          buttons: Array.isArray(d.buttons)
            ? d.buttons.map(function(btn) {
                return {
                  type: String(btn.type || 'reply'),
                  displayText: sanitizeOutboundText(String(btn.displayText || ''), authorizedLinks),
                  id: String(btn.id || '')
                };
              })
            : []
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
          caption: sanitizeOutboundText(String(d.caption || ''), authorizedLinks),
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
          text: sanitizeOutboundText(String(d.replyText || d.text || ''), authorizedLinks)
        }
      }
    });
  }
}

return results;
