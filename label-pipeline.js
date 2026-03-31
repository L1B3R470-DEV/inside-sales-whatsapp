// label-pipeline.js — n8n Code node
// Atribui labels do WhatsApp como pipeline CRM baseado no lead_score e intent
// Executar DEPOIS do route_message retornar, usando o lead_score e intent do payload
//
// Labels existentes no WhatsApp (predefinidas):
//   1 = Novo cliente      | 2 = Novo pedido       | 3 = Pagamento pendente
//   4 = Pago              | 5 = Pedido finalizado  | 6 = Importante
//   7 = Acompanhar        | 8 = Lead

var EVOLUTION_BASE_URL = $env.EVOLUTION_BASE_URL || 'http://localhost:8080';
var EVOLUTION_API_KEY  = $env.EVOLUTION_API_KEY  || '123456';
var EVOLUTION_INSTANCE = $env.EVOLUTION_INSTANCE || 'ATENDIMENTO_VENDAS_CLEAN';

var number    = String($json.number || '').replace(/\D/g, '');
var leadScore = Number($json.leadScore || $json.lead_score || 0);
var intent    = String($json.intent || $json.detectedIntent || '').toLowerCase();
var routeDecision = String($json.routeDecision || '');

// Pipeline mapping based on lead score thresholds
function getLabelId(score, intent, route) {
  if (route === 'human_escalation') return '6';  // Importante
  if (score >= 80) return '1';   // Novo cliente (hot lead)
  if (score >= 50) return '7';   // Acompanhar (qualified, nurture)
  if (score >= 25) return '8';   // Lead (initial interest)
  if (intent === 'saudacao' || intent === 'geral') return '8'; // Lead
  return '';  // No label for very low engagement
}

var labelId = getLabelId(leadScore, intent, routeDecision);

if (number && labelId) {
  try {
    var httpModule = require('http');
    var url = EVOLUTION_BASE_URL + '/label/handleLabel/' + EVOLUTION_INSTANCE;
    var parsed = new URL(url);
    var postData = JSON.stringify({
      number: number,
      labelId: labelId,
      action: 'add'
    });
    var options = {
      hostname: parsed.hostname,
      port: parsed.port || 80,
      path: parsed.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': EVOLUTION_API_KEY,
        'Content-Length': Buffer.byteLength(postData),
      },
    };
    var req = httpModule.request(options, function(res) {
      res.on('data', function() {});
      res.on('end', function() {});
    });
    req.on('error', function() {});
    req.write(postData);
    req.end();
  } catch (_e) {
    // Non-critical
  }
}

var _items = $input.all();
return _items;
