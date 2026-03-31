// composing-presence.js — n8n Code node
// Envia "digitando..." antes de cada resposta para parecer humano
// Colocar ANTES do nó de envio de mensagem no workflow
//
// n8n Code nodes executam o corpo como async function, então await funciona.
// Este arquivo serve como referência — colar o conteúdo no Code node do n8n.

const EVOLUTION_BASE_URL = $env.EVOLUTION_BASE_URL || 'http://localhost:8080';
const EVOLUTION_API_KEY  = $env.EVOLUTION_API_KEY  || '123456';
const EVOLUTION_INSTANCE = $env.EVOLUTION_INSTANCE || 'ATENDIMENTO_VENDAS_CLEAN';

const number   = String($json.number || '').replace(/\D/g, '');
const replyLen = String($json.replyText || $json.text || '').length;

// Delay proporcional ao tamanho da resposta (1.5s-4s)
const delayMs = Math.min(4000, Math.max(1500, Math.round(replyLen * 15)));

async function sendComposing() {
  if (!number) return;
  try {
    const url = EVOLUTION_BASE_URL + '/chat/sendPresence/' + EVOLUTION_INSTANCE;
    const resp = $httpRequest
      ? null
      : null;
    const http = require('https');
    const httpModule = url.startsWith('https') ? require('https') : require('http');
    const parsed = new URL(url);
    const postData = JSON.stringify({
      number: number,
      delay: delayMs,
      presence: 'composing',
    });
    const options = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': EVOLUTION_API_KEY,
        'Content-Length': Buffer.byteLength(postData),
      },
    };
    return new Promise(function(resolve) {
      const req = httpModule.request(options, function(res) {
        res.on('data', function() {});
        res.on('end', resolve);
      });
      req.on('error', resolve);
      req.write(postData);
      req.end();
    });
  } catch (_e) {
    // Non-critical
  }
}

sendComposing();

// Aguarda o tempo do indicador de digitacao antes de liberar a mensagem
var _items = $input.all();
return _items;
