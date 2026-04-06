const input = $json;

const cfg = {
  maxInputChars: 600,
  maxOutputChars: 520,
  maxOutputTokens: 260,
  maxMsgsPerMinute: 8,
  maxMsgsPerHour: 25,
  maxMsgsPerDay: 200,
  maxAiCallsPerMinute: 8,
  minGlobalAiIntervalSeconds: 4,
  minConfidenceForAutoSend: 0.4,
  openAiModel: 'gpt-5.4',
  openAiReasoningEffort: 'low',
  openAiReasoningEffortComplex: 'medium',
  openAiConversationStateMaxMinutes: 360,
  workTimezone: 'America/Bahia',
  workDays: [1, 2, 3, 4, 5],
  workWindows: ['08:00-12:00', '13:30-18:00'],
  outOfHoursMessage: 'Aqui é o Eduardo, Consultor de Vendas Internas da Classe Couro. Obrigado pelo seu contato. Atendo de segunda a sexta, das 08:00 às 12:00 e das 13:30 às 18:00. No próximo horário eu sigo com prioridade. Se quiser adiantar, já me diga o produto e a quantidade que você procura.',
  highVolumeMessage: 'Aqui é o Eduardo, Consultor de Vendas Internas da Classe Couro. Seu atendimento já está em prioridade. Para eu acelerar sua proposta, me diga agora o produto e a quantidade desejada.',
  unresolvedRecipientMessage: 'Aqui é o Eduardo, Consultor de Vendas Internas da Classe Couro. Tive uma instabilidade para identificar seu contato neste momento, mas já estou cuidando disso. Pode repetir sua mensagem, por favor?',
  missingKeyMessage: 'Aqui é o Eduardo, Consultor de Vendas Internas da Classe Couro. Nosso atendimento automático está em ajuste neste momento, mas seu contato já foi registrado e vou seguir com você por aqui.',
  blockedNumberMessage: '',
  // Safety denylist for accidental recipients. Extend/adjust as needed.
  blockedNumbers: [
    '557599991111',
    '553498066683', '556282755369', '557182157263', '557581495845',
    '557581534233', '557581542771', '557581960700', '557588270211',
    '557588270407', '557588330352', '557588340002', '557591433132',
    '557591612728', '557591691926', '557591711025', '557591932073',
    '557591958170', '5575920008385', '557592305601', '557592385248',
    '557592490290', '557592637709', '557592832955', '557599001144',
    '557599668464', '557599669915', '557599966316', '558796686768',
    '557382474263'
  ],
  insideSalesOwnNumber: '557583211367',
  salesBook: {
    fileName: 'BOOK_PROSPECCAO_VENDAS_INTERNAS.pdf',
    mimeType: 'application/pdf',
    documentCaption: 'BOOK DE VENDAS | Colecao Classe Couro'
  },
  b2b: {
    url: 'https://mstabletssl.ddns.net/wsB2BProspClasseCouro1ssl/acessocliente.aspx',
    displayLabel: 'Portal B2B Classe Couro'
  },
  knowledge: {
    companyName: 'Classe Couro',
    consultantName: 'Eduardo',
    position: 'Consultor de Vendas Internas',
    businessSummary: [
      'Atendimento consultivo para produtos de couro com foco em solução para necessidade real do cliente.',
      'Orçamento personalizado conforme produto, acabamento, quantidade e prazo desejado.',
      'Atendimento humanizado, com prioridade para leads qualificados e histórico de relacionamento.'
    ],
    salesProcess: [
      'Entender necessidade: tipo de produto, quantidade, uso e prazo.',
      'Qualificar lead com poucos dados: produto principal, volume aproximado e prazo.',
      'Conduzir para próximo passo comercial com pergunta única e objetiva.'
    ]
  },
  activeProspectingPrinciples: {
    core: [
      'Responder primeiro o que o cliente perguntou; avancar a conversa so depois disso.',
      'Gerar continuidade: cada resposta deve aumentar confianca e facilitar o proximo passo.',
      'Tratar a demanda como necessidade real, nao como curiosidade superficial.',
      'Soar humano, simpatico, consultivo e comercial, sem parecer bot engessado.',
      'Nunca subestimar a inteligencia do cliente e nunca inventar dados.'
    ],
    firstContact: [
      'No primeiro contato: acolher com calor humano, mostrar utilidade imediata e fazer no maximo 1 pergunta curta.',
      'Evitar interrogatorio; se o cliente ja trouxe contexto na mesma mensagem, aproveitar isso.',
      'Criar conexao emocional leve e profissional, sem exagero.'
    ],
    qualityGate: [
      'Antes de concluir a resposta, validar silenciosamente: respondi a pergunta principal?',
      'Fortaleci confianca na Classe Couro?',
      'Deixei um proximo passo claro e leve?',
      'Evitei repeticao, generalidade e desconexao com o contexto?'
    ]
  }
};

const now = new Date();
const nowIso = now.toISOString();

const parts = new Intl.DateTimeFormat('en-CA', {
  timeZone: cfg.workTimezone,
  weekday: 'short',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false
}).formatToParts(now);

const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
const weekdayMap = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 7 };
const dow = weekdayMap[p.weekday] || 0;
const hh = Number(p.hour || '0');
const mm = Number(p.minute || '0');
const minutesNow = (hh * 60) + mm;
const dayKey = `${p.year}-${p.month}-${p.day}`;
const hourKey = `${dayKey}-${String(hh).padStart(2, '0')}`;
const minuteKey = `${hourKey}-${String(mm).padStart(2, '0')}`;

function getGreetingLabel(hour) {
  const h = Number(hour || 0);
  if (h >= 5 && h <= 11) return 'bom dia';
  if (h >= 12 && h <= 17) return 'boa tarde';
  return 'boa noite';
}

function resolveReasoningEffort(intent, inboundText, humanPriority) {
  const len = String(inboundText || '').trim().length;
  if (humanPriority) return cfg.openAiReasoningEffortComplex;
  if (['institucional_empresa', 'preco_orcamento', 'atacado_quantidade', 'produto_catalogo'].includes(String(intent || '')) && len >= 80) {
    return cfg.openAiReasoningEffortComplex;
  }
  return cfg.openAiReasoningEffort;
}

function hhmmToMinutes(hhmm) {
  const [h, m] = String(hhmm).split(':').map((v) => Number(v));
  return (h * 60) + m;
}

function inAnyWindow(value, windows) {
  for (const w of windows) {
    const [start, end] = w.split('-').map((v) => v.trim());
    if (!start || !end) continue;
    const s = hhmmToMinutes(start);
    const e = hhmmToMinutes(end);
    if (value >= s && value <= e) return true;
  }
  return false;
}

function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function toTitleName(name) {
  const clean = String(name || '')
    .replace(/[^A-Za-zÀ-ÿ\s'`-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!clean) return '';

  const stop = new Set(['de', 'da', 'do', 'dos', 'das', 'e']);
  return clean
    .split(' ')
    .filter((x) => x && x.length >= 2)
    .slice(0, 3)
    .map((part, idx) => {
      const p = part.toLowerCase();
      if (idx > 0 && stop.has(p)) return p;
      return p.charAt(0).toUpperCase() + p.slice(1);
    })
    .join(' ')
    .trim();
}

function toFirstName(name) {
  const clean = toTitleName(name);
  if (!clean) return '';
  const first = clean.split(' ').filter(Boolean)[0] || '';
  return toTitleName(first);
}

function sanitizeCustomerName(name) {
  const first = toFirstName(name);
  if (!first) return '';
  const invalid = new Set([
    'comigo', 'aqui', 'agora', 'momento', 'mesmo', 'numero', 'telefone', 'whatsapp', 'perfil',
    'nao', 'não', 'sim', 'obrigado', 'obrigada', 'classe', 'couro', 'revenda', 'atacado',
    'possuo', 'tenho', 'positivo', 'ok', 'claro', 'certo', 'correto', 'isso', 'este', 'essa',
    'loja', 'fisica', 'física', 'lojista', 'empresa', 'cliente', 'contato', 'cadastro',
    'comercial', 'vendas', 'inside', 'sales', 'b2b', 'catalogo', 'catálogo', 'book', 'material'
  ]);
  const norm = normalizeText(first);
  if (invalid.has(norm)) return '';
  if (first.length < 2) return '';
  return first;
}

function resolvePreferredCustomerName(profile, inboundPushName) {
  const savedName = sanitizeCustomerName(profile?.customerName || '');
  const pushName = sanitizeCustomerName(inboundPushName || profile?.pushName || '');
  const savedSource = String(profile?.customerNameSource || '').trim();

  if (savedName && pushName) {
    if (normalizeText(savedName) === normalizeText(pushName)) {
      return {
        name: savedName,
        source: savedSource || 'whatsapp_profile'
      };
    }

    if (savedSource && savedSource !== 'whatsapp_profile') {
      return {
        name: savedName,
        source: savedSource
      };
    }

    return {
      name: savedName,
      source: savedSource || 'saved_contact'
    };
  }

  if (savedName) {
    return {
      name: savedName,
      source: savedSource || 'saved_contact'
    };
  }

  if (pushName) {
    return {
      name: pushName,
      source: 'whatsapp_profile'
    };
  }

  return {
    name: '',
    source: ''
  };
}

function extractSelfIdentifiedName(text) {
  const t = String(text || '').trim();
  if (!t) return '';

  // Some inbound payloads may contain replacement chars (�), so normalize aggressively.
  const normalized = normalizeText(t)
    .replace(/[^a-z\s'`-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!normalized) return '';

  const rgx = /(?:meu\s+nome(?:\s+e)?|me\s+chamo|pode\s+me\s+chamar\s+de|eu\s+sou|sou\s+o|sou\s+a)\s+([a-z][a-z'`-]{1,30}(?:\s+[a-z][a-z'`-]{1,30}){0,2})/i;
  const m = normalized.match(rgx);
  if (m && m[1]) {
    const connectors = new Set(['de', 'da', 'do', 'dos', 'das', 'e']);
    const stopAfterName = new Set([
      'quero', 'gostaria', 'preciso', 'precisava', 'tenho', 'tenhoo', 'desejo',
      'sobre', 'produto', 'produtos', 'saber', 'comprar', 'atacado', 'orcamento',
      'orcamento', 'valor', 'preco', 'prazo', 'entrega', 'boa', 'tarde', 'dia', 'noite'
    ]);

    const tokens = String(m[1])
      .split(/\s+/)
      .map((x) => x.trim())
      .filter(Boolean);

    const picked = [];
    for (let i = 0; i < tokens.length; i++) {
      const tk = String(tokens[i] || '').toLowerCase();
      if (!tk) continue;

      if (picked.length > 0 && stopAfterName.has(tk)) break;

      if (connectors.has(tk)) {
        // Keep connector only if it links to a probable surname.
        const next = String(tokens[i + 1] || '').toLowerCase();
        if (picked.length > 0 && next && !stopAfterName.has(next)) {
          picked.push(tk);
        }
        continue;
      }

      if (stopAfterName.has(tk) && picked.length === 0) {
        continue;
      }

      picked.push(tk);
      if (picked.length >= 3) break;
    }

    const candidate = sanitizeCustomerName(picked.join(' '));
    if (candidate && !/\d/.test(candidate)) return candidate;
  }

  return '';
}

function detectIntent(text) {
  const norm = normalizeText(text);

  // Map interactive button responses to intents directly
  const buttonMap = {
    'btn_orcamento': { intent: 'preco_orcamento', score: 0.95, matches: ['btn_orcamento'] },
    'btn_catalogo': { intent: 'produto_catalogo', score: 0.95, matches: ['btn_catalogo'] },
    'btn_humano': { intent: 'human_escalation', score: 0.99, matches: ['btn_humano'] },
    'solicitar orcamento': { intent: 'preco_orcamento', score: 0.92, matches: ['solicitar orcamento'] },
    'ver catalogo / produtos': { intent: 'produto_catalogo', score: 0.92, matches: ['ver catalogo'] },
    'ver catalogo': { intent: 'produto_catalogo', score: 0.92, matches: ['ver catalogo'] },
    'falar com vendedor': { intent: 'human_escalation', score: 0.99, matches: ['falar com vendedor'] },
  };
  var btnMatch = buttonMap[norm] || buttonMap[String(text || '').trim().toLowerCase()];
  if (btnMatch) return btnMatch;

  const rules = [
    { intent: 'saudacao', score: 0.68, keywords: ['bom dia', 'boa tarde', 'boa noite', 'olá', 'ola', 'oi', 'tudo bem', 'tudo bom'] },
    { intent: 'institucional_empresa', score: 0.83, keywords: ['classe couro', 'sobre a classe', 'sobre sua empresa', 'sobre a empresa', 'sobre voces', 'quem sao voces', 'historia da marca', 'fale sobre'] },
    { intent: 'agradecimento', score: 0.7, keywords: ['obrigado', 'obrigada', 'valeu', 'agradeco', 'agradeço'] },
    { intent: 'preco_orcamento', score: 0.78, keywords: ['preco', 'valor', 'orcamento', 'quanto custa', 'cotacao'] },
    { intent: 'produto_catalogo', score: 0.76, keywords: ['catalogo', 'modelo', 'produto', 'acessorio', 'acessorios', 'couro', 'carteira', 'carteiras', 'cinto', 'cintos', 'bolsa', 'bolsas', 'mochila', 'mochilas', 'kit', 'kits', 'shopping bag', 'peca', 'pecas', 'masculino', 'masculina', 'feminino', 'feminina'] },
    { intent: 'prazo_entrega', score: 0.75, keywords: ['prazo', 'entrega', 'quando chega', 'frete', 'envio'] },
    { intent: 'pagamento', score: 0.74, keywords: ['pagamento', 'pix', 'cartao', 'boleto', 'parcelamento'] },
    { intent: 'atacado_quantidade', score: 0.82, keywords: ['atacado', 'quantidade', 'lote', 'revenda'] },
    { intent: 'pos_venda_reclamacao', score: 0.88, keywords: ['reclamacao', 'problema', 'defeito', 'atraso', 'insatisfacao'] },
    { intent: 'troca_devolucao', score: 0.9, keywords: ['troca', 'devolucao', 'devolver'] },
    { intent: 'cancelamento', score: 0.9, keywords: ['cancelar', 'cancelamento'] }
  ];

  let best = { intent: 'geral', score: 0.45, matches: [] };
  for (const rule of rules) {
    const matches = rule.keywords.filter((kw) => norm.includes(kw));
    if (matches.length > 0) {
      const finalScore = Math.min(0.95, rule.score + (matches.length * 0.03));
      if (finalScore > best.score) {
        best = { intent: rule.intent, score: finalScore, matches };
      }
    }
  }
  return best;
}

function getIgnoredNumbersSet(staticData, routerBlockedNumbers) {
  const out = new Set((cfg.blockedNumbers || []).map((x) => String(x || '').replace(/\D/g, '')).filter(Boolean));
  const dynamicIgnored = staticData?.ignoredContacts && typeof staticData.ignoredContacts === 'object'
    ? staticData.ignoredContacts
    : {};
  const numbers = Array.isArray(dynamicIgnored.numbers) ? dynamicIgnored.numbers : [];
  for (const value of numbers) {
    const digits = String(value || '').replace(/\D/g, '');
    if (digits) out.add(digits);
  }
  const fromRouter = Array.isArray(routerBlockedNumbers) ? routerBlockedNumbers : [];
  for (const value of fromRouter) {
    const digits = String(value || '').replace(/\D/g, '');
    if (digits) out.add(digits);
  }
  return out;
}

function getAlwaysAllowedNumbersSet(staticData, routerAlwaysAllowedNumbers) {
  const out = new Set();
  const dynamicAllowed = staticData?.alwaysAllowedContacts && typeof staticData.alwaysAllowedContacts === 'object'
    ? staticData.alwaysAllowedContacts
    : {};
  const numbers = Array.isArray(dynamicAllowed.numbers) ? dynamicAllowed.numbers : [];
  for (const value of numbers) {
    const digits = String(value || '').replace(/\D/g, '');
    if (digits) out.add(digits);
  }
  const fromRouter = Array.isArray(routerAlwaysAllowedNumbers) ? routerAlwaysAllowedNumbers : [];
  for (const value of fromRouter) {
    const digits = String(value || '').replace(/\D/g, '');
    if (digits) out.add(digits);
  }
  return out;
}

function extractEntities(text) {
  const t = String(text || '');
  const entities = {};

  const qtyMatch = t.match(/\b(\d{1,4})\s?(un|und|unid|unidades|peca|pecas|pares?)\b/i);
  if (qtyMatch) entities.quantity = Number(qtyMatch[1]);

  const moneyMatch = t.match(/(?:r\$\s?)(\d+[\d\.,]*)/i);
  if (moneyMatch) entities.budgetHint = moneyMatch[1];

  const cityMatch = t.match(/(?:sou de|entrega em|para)\s+([\p{L}\s]{3,40})/iu);
  if (cityMatch) entities.cityHint = cityMatch[1].trim();

  const urgencyMatch = t.match(/(urgente|hoje|amanha|essa semana|imediato)/i);
  if (urgencyMatch) entities.urgencyHint = urgencyMatch[1];

  const productMatch = t.match(/\b(carteiras?|cintos?|bolsas?|mochilas?|kits?|acessorios?|shopping\s+bags?|pe[cç]as?)\b/i);
  if (productMatch) entities.productHint = String(productMatch[1] || '').toLowerCase();

  const audienceMatch = t.match(/\b(masculin[oa]s?|feminin[oa]s?)\b/i);
  if (audienceMatch) entities.audienceHint = String(audienceMatch[1] || '').toLowerCase();

  const lineMatch = t.match(/\b(basic[ao]s?|intermediari[ao]s?|premium)\b/i);
  if (lineMatch) entities.linePreference = normalizeText(lineMatch[1]);

  return entities;
}

function detectProductFocusSignals(text, entities, profile) {
  const norm = normalizeText(text);
  const productHint = String(entities.productHint || '').toLowerCase();
  const audienceHint = String(entities.audienceHint || '').toLowerCase();
  const explicitLine = String(entities.linePreference || '').toLowerCase();
  const linePreference = explicitLine.includes('basic') ? 'basica'
    : explicitLine.includes('intermedi') ? 'intermediaria'
    : explicitLine.includes('premium') ? 'premium'
    : '';

  const imageRequest = [
    'imagem', 'imagens', 'foto', 'fotos', 'mostra', 'mostrar', 'quero ver', 'me mostra', 'catalogo', 'catálogo'
  ].some((k) => norm.includes(normalizeText(k)));

  let productFocus = '';
  let productCategory = '';

  if (productHint.includes('carteira')) {
    productFocus = 'CARTEIRAS';
    if (audienceHint.includes('mascul')) productCategory = 'CARTEIRAS MASCULINAS';
    if (audienceHint.includes('feminin')) productCategory = 'CARTEIRAS FEMININAS';
  } else if (productHint.includes('cinto')) {
    productFocus = 'CINTOS';
    if (audienceHint.includes('mascul')) productCategory = 'CINTOS MASCULINOS';
    if (audienceHint.includes('feminin')) productCategory = 'CINTOS FEMININOS';
  } else if (productHint.includes('bolsa')) {
    productFocus = 'BOLSAS';
    productCategory = 'BOLSAS FEMININAS';
  } else if (productHint.includes('mochila')) {
    productFocus = 'MOCHILAS';
    if (audienceHint.includes('mascul')) productCategory = 'MOCHILAS MASCULINAS';
    if (audienceHint.includes('feminin')) productCategory = 'MOCHILAS FEMININAS';
  } else if (productHint.includes('kit')) {
    productFocus = 'KITS';
    if (audienceHint.includes('mascul')) productCategory = 'KITS MASCULINOS';
    if (audienceHint.includes('feminin')) productCategory = 'KITS FEMININOS';
  } else if (productHint.includes('shopping bag')) {
    productFocus = 'BOLSAS';
    productCategory = 'BOLSAS FEMININAS';
  } else if (productHint.includes('peca') || productHint.includes('acessorio')) {
    productFocus = 'ACESSORIOS';
    if (audienceHint.includes('mascul')) productCategory = 'ACESSORIOS MASCULINOS';
    if (audienceHint.includes('feminin')) productCategory = 'ACESSORIOS FEMININOS';
  }

  const needsPreviousContext = Boolean(linePreference || imageRequest || audienceHint);
  if (!productFocus && needsPreviousContext) {
    productFocus = String(profile.lastProductFocus || '').trim();
  }
  if (!productCategory && needsPreviousContext) {
    productCategory = String(profile.lastProductCategory || '').trim();
  }

  return {
    productFocus,
    productCategory,
    linePreference,
    imageRequest,
  };
}

function yesNoIntent(text) {
  const norm = normalizeText(text);
  const yesList = ['sim', 'tenho', 'possuo', 'positivo', 'claro', 'ok', 'tenho sim'];
  const noList = ['nao', 'não', 'nao tenho', 'não tenho', 'negativo', 'sem cnpj', 'sem loja'];

  const hasYes = yesList.some((k) => norm.includes(k));
  const hasNo = noList.some((k) => norm.includes(k));
  if (hasYes && !hasNo) return 'yes';
  if (hasNo && !hasYes) return 'no';
  return 'unknown';
}

function isShortAcknowledgement(text) {
  const norm = normalizeText(text).replace(/\s+/g, ' ').trim();
  if (!norm) return false;
  if (yesNoIntent(text) !== 'unknown') return true;

  const tokens = norm.split(' ').filter(Boolean);
  if (tokens.length > 6) return false;

  return [
    'ok', 'okay', 'certo', 'beleza', 'blz', 'entendi', 'obrigado', 'obrigada',
    'valeu', 'show', 'perfeito', 'recebi', 'combinado', 'fechado', 'joia',
    'maravilha', 'tudo certo', 'de acordo'
  ].some((label) => {
    const probe = normalizeText(label);
    return norm === probe || norm.startsWith(`${probe} `) || norm.endsWith(` ${probe}`) || norm.includes(` ${probe} `);
  });
}

function extractPhone(text) {
  const digits = String(text || '').replace(/\D/g, '');
  if (digits.length < 10) return '';
  if (digits.length > 13) return digits.slice(-13);
  return digits;
}

function inferPhoneFromContext(text, profileNumber) {
  const norm = normalizeText(text);
  const mentionsCurrentNumber = [
    'esse numero', 'este numero', 'esse mesmo', 'este mesmo', 'numero que estou falando',
    'esse telefone', 'meu numero', 'meu whatsapp', 'perfil de whatsapp', 'procure meu numero'
  ].some((k) => norm.includes(k));
  if (!mentionsCurrentNumber) return '';

  const p = String(profileNumber || '').replace(/\D/g, '');
  return p.length >= 10 ? p : '';
}

function extractCnpj(text) {
  const digits = String(text || '').replace(/\D/g, '');
  if (digits.length < 14) return '';
  return digits.slice(0, 14);
}

function looksLikeMaskedCnpjInput(text) {
  const raw = String(text || '').trim();
  if (!raw) return false;
  const digits = raw.replace(/\D/g, '');
  if (digits.length !== 14) return false;
  return /[.\-\/\s]/.test(raw) || /^\d{14}$/.test(raw);
}

function isValidCnpj(cnpj) {
  const digits = String(cnpj || '').replace(/\D/g, '');
  if (!digits || digits.length !== 14) return false;
  if (/^(\d)\1{13}$/.test(digits)) return false;

  function calc(base, factors) {
    let total = 0;
    for (let i = 0; i < factors.length; i++) {
      total += Number(base[i] || 0) * factors[i];
    }
    const mod = total % 11;
    return mod < 2 ? 0 : 11 - mod;
  }

  const d1 = calc(digits.slice(0, 12), [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  const d2 = calc(digits.slice(0, 12) + String(d1), [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  return digits.endsWith(`${d1}${d2}`);
}

function extractInstagram(text) {
  const t = String(text || '').trim();
  if (!t) return '';
  const norm = normalizeText(t).trim();
  const blocked = new Set([
    'sim', 'nao', 'não', 'ok', 'claro', 'positivo', 'negativo', 'tenho', 'possuo',
    'esse mesmo', 'este mesmo', 'nao tenho', 'não tenho', 'nao possuo', 'não possuo',
    'nao informado', 'não informado', 'nao tenho comigo no momento', 'não tenho comigo no momento'
  ]);
  if (blocked.has(norm)) return '';
  const handle = t.match(/@([a-zA-Z0-9._]{2,30})/);
  if (handle && handle[1]) return `@${handle[1]}`;
  if (/instagram\.com\//i.test(t)) return t.slice(0, 120);
  return '';
}

function extractCity(text) {
  const t = String(text || '').trim();
  if (!t) return '';
  const m = t.match(/(?:sou de|cidade|moro em|de)\s+([\p{L}\s]{2,40})/iu);
  if (m && m[1]) return m[1].trim();
  if (/^\p{L}[\p{L}\s-]{1,40}$/iu.test(t)) return t;
  return '';
}

function extractLikelyStandaloneName(text) {
  const t = String(text || '').trim();
  if (!t) return '';

  const cleaned = t
    .replace(/^[\s"'`´^~.,!?;:()\-_/\\]+/, '')
    .replace(/[\s"'`´^~.,!?;:()\-_/\\]+$/, '')
    .trim();

  if (!cleaned) return '';
  if (cleaned.length > 40) return '';
  if (/[0-9@]/.test(cleaned)) return '';
  if (/[?!.:,;]/.test(cleaned.replace(/[ .'-]/g, ''))) return '';
  if (cleaned.split(/\s+/).length > 2) return '';

  return sanitizeCustomerName(cleaned);
}

function inferLojaFisicaStatus(text) {
  const norm = normalizeText(text);
  const noPhrases = [
    'nao tenho loja fisica', 'não tenho loja fisica', 'nao tenho loja física', 'não tenho loja física',
    'sem loja fisica', 'sem loja física', 'so online', 'só online'
  ];
  if (noPhrases.some((k) => norm.includes(k))) return 'nao';

  const yesPhrases = [
    'tenho loja fisica', 'tenho loja física', 'ja tenho loja fisica', 'já tenho loja física',
    'possuo loja fisica', 'possuo loja física', 'minha loja fisica', 'minha loja física',
    'loja fisica', 'loja física'
  ];
  if (yesPhrases.some((k) => norm.includes(k))) return 'sim';

  return '';
}

function inferCnpjAtivoStatus(text, cnpjDetected) {
  const norm = normalizeText(text);
  const noPhrases = ['nao tenho cnpj', 'não tenho cnpj', 'cnpj inapto', 'cnpj baixado', 'regularizacao', 'regularização'];
  if (noPhrases.some((k) => norm.includes(k))) return 'nao';

  if (cnpjDetected) return 'sim';
  if (norm.includes('cnpj ativo')) return 'sim';
  return '';
}

function inferPessoaFisicaInterest(text) {
  const norm = normalizeText(text);
  const pfPhrases = [
    'pessoa fisica', 'pessoa física', 'sou pf', 'sou pessoa fisica', 'sou pessoa física',
    'consumidor final', 'uso proprio', 'uso próprio', 'pra mim', 'para mim', 'pra meu uso', 'para meu uso',
    'compra pessoal', 'comprar pra mim', 'comprar para mim', 'quero comprar pra mim', 'quero comprar para mim',
    'presentear', 'presente', 'comprar no varejo', 'comprar pelo site', 'comprar no site',
    'nao revendo', 'não revendo', 'nao sou lojista', 'não sou lojista'
  ];
  return pfPhrases.some((k) => norm.includes(k));
}

function shouldRoutePessoaFisicaEcommerce(text, activeScript) {
  const norm = normalizeText(text);
  const stage = Number(activeScript?.stage || 1);
  const yn = yesNoIntent(text);

  // If the client is simply answering the mandatory revenda triage,
  // preserve the existing scripted response and do not reroute to ecommerce.
  if (stage === 1 && yn === 'no') return false;
  if (stage === 2 && yn === 'no') return false;
  if (inferCnpjAtivoStatus(text, extractCnpj(text)) === 'nao') return false;
  if (inferLojaFisicaStatus(text) === 'nao') return false;

  return inferPessoaFisicaInterest(norm);
}

function buildPessoaFisicaEcommerceReply(profile) {
  const firstName = sanitizeCustomerName(profile?.customerName || '');
  const prefix = firstName ? `Que bom falar com voce, ${firstName}!` : 'Que bom ter voce por aqui!';
  return `${prefix} Como o seu interesse e comprar como pessoa fisica, o melhor caminho e pelo nosso site oficial: www.classecouro.com.br. La voce pode conhecer as linhas com calma, navegar pelo e-commerce e ficar a vontade para escolher seus produtos da Classe Couro.`;
}

function buildSemCnpjSiteReply(profile) {
  const firstName = sanitizeCustomerName(profile?.customerName || '');
  const prefix = firstName ? `Sem problema, ${firstName}!` : 'Sem problema!';
  return `${prefix} No momento, nao vamos conseguir prosseguir com o seu cadastramento no nosso B2B, porque a revenda direta exige CNPJ ativo. Agradeco sinceramente o seu interesse na Classe Couro. Quando esse requisito estiver regularizado, sera um prazer retomar seu atendimento por aqui e seguir com voce da forma correta. Obrigado pelo seu contato e conte com a gente.`;
}

function likelyRevendaScript(normInbound, intent) {
  if (intent === 'atacado_quantidade') return true;
  const keys = ['atacado', 'revenda', 'revender', 'revendedor', 'fabrica', 'fornecedor', 'cnpj', 'loja fisica'];
  return keys.some((k) => normInbound.includes(k));
}

function shouldRestartRevendaScript(script, inboundText) {
  if (!script || typeof script !== 'object') return false;
  const norm = normalizeText(inboundText);
  const explicitRestart = (
    /como\s+faco\s+(pra|para)\s+revender/.test(norm) ||
    /quero\s+revender/.test(norm) ||
    /revender\s+classe/.test(norm) ||
    /comprar\s+em\s+atacado/.test(norm) ||
    /como\s+comprar\s+em\s+atacado/.test(norm)
  );
  if (!explicitRestart) return false;

  if (script.completed) return true;
  if (Number(script.stage || 0) > 1) return true;

  const data = script.data || {};
  const hasAnyProgress = Boolean(
    data.cnpjAtivo || data.lojaFisica || data.nome || data.telefone || data.cidade || data.instagram || data.cnpj
  );
  return hasAnyProgress;
}

function initRevendaScriptState(nowIso) {
  return {
    active: true,
    stage: 1,
    startedAt: nowIso,
    updatedAt: nowIso,
    completed: false,
    disqualified: false,
    disqualifiedReason: '',
    data: {
      cnpjAtivo: '',
      lojaFisica: '',
      nome: '',
      telefone: '',
      cidade: '',
      instagram: '',
      cnpj: ''
    }
  };
}

function wantsRevendaExplanation(text) {
  const norm = normalizeText(text);
  return [
    'quero entender melhor antes de passar os dados',
    'quero entender melhor',
    'antes de passar os dados',
    'antes de informar os dados',
    'antes de enviar os dados'
  ].some((k) => norm.includes(k));
}

function wantsSalesBook(text) {
  const norm = normalizeText(text);
  return [
    'book', 'book de vendas', 'book vendas', 'catalogo', 'catálogo', 'mostruario', 'mostruário'
  ].some((k) => norm.includes(normalizeText(k)));
}

function wantsCommercialMaterial(text) {
  const norm = normalizeText(text);
  return [
    'foto', 'fotos', 'imagem', 'imagens', 'book', 'book de vendas', 'catalogo', 'catálogo',
    'mostruario', 'mostruário', 'material', 'materiais', 'me envie', 'me envia', 'me mostre',
    'me mostra', 'quero ver', 'mostrar modelos'
  ].some((k) => norm.includes(normalizeText(k)));
}

function buildMaterialLabel(productSignals, profile) {
  const category = String(productSignals?.productCategory || profile?.lastProductCategory || '').trim();
  const focus = String(productSignals?.productFocus || profile?.lastProductFocus || '').trim();

  if (category === 'BOLSAS FEMININAS') return 'as bolsas femininas com melhor giro';
  if (category === 'CARTEIRAS FEMININAS') return 'as carteiras femininas com melhor giro';
  if (category === 'CARTEIRAS MASCULINAS') return 'as carteiras masculinas com melhor giro';
  if (category === 'CINTOS FEMININOS') return 'os cintos femininos com melhor giro';
  if (category === 'CINTOS MASCULINOS') return 'os cintos masculinos com melhor giro';
  if (category === 'MOCHILAS FEMININAS') return 'as mochilas femininas com melhor giro';
  if (category === 'MOCHILAS MASCULINAS') return 'as mochilas masculinas com melhor giro';
  if (category === 'KITS FEMININOS') return 'os kits femininos com melhor giro';
  if (category === 'KITS MASCULINOS') return 'os kits masculinos com melhor giro';
  if (category === 'ACESSORIOS FEMININOS') return 'os acessórios femininos com melhor giro';
  if (category === 'ACESSORIOS MASCULINOS') return 'os acessórios masculinos com melhor giro';

  if (focus === 'BOLSAS') return 'as bolsas com melhor giro';
  if (focus === 'CARTEIRAS') return 'as carteiras com melhor giro';
  if (focus === 'CINTOS') return 'os cintos com melhor giro';
  if (focus === 'MOCHILAS') return 'as mochilas com melhor giro';
  if (focus === 'KITS') return 'os kits com melhor giro';
  if (focus === 'ACESSORIOS') return 'os acessórios com melhor giro';

  return 'os materiais comerciais mais alinhados ao seu perfil';
}

function buildCommercialMaterialGateReply(script, productSignals, profile) {
  const stage = Number(script?.stage || 1);
  const materialLabel = buildMaterialLabel(productSignals, profile);

  if (stage <= 1) {
    return `Consigo sim te mostrar ${materialLabel}. Faz sentido voce querer avaliar antes de avancar. Eu libero esse material logo apos um pre-cadastro rapido, para ja te apresentar algo mais alinhado ao perfil da sua loja, alem de book e condicoes comerciais. Para avancarmos, voce possui CNPJ ativo?`;
  }
  if (stage === 2) {
    return `Perfeito, ja deixo ${materialLabel} preparado para a proxima etapa. Antes, preciso confirmar um requisito obrigatorio da revenda para te atender do jeito certo: voce possui loja fisica?`;
  }
  if (stage === 3) {
    return `Otimo, estamos avancando. Para eu direcionar seu atendimento da forma certa e ja preparar ${materialLabel}, me diz primeiro de qual cidade voce e.`;
  }
  if (stage === 4) {
    return `Perfeito, isso ja me ajuda bastante. Para eu seguir com seu pre-cadastro e liberar o material da forma correta, me fala por favor o seu nome.`;
  }
  if (stage === 5) {
    return `Falta pouco. Para eu concluir seu pre-cadastro e seguir com o material, me informa o melhor telefone para contato.`;
  }
  if (stage === 6) {
    return `Estamos quase concluindo. Se tiver Instagram da loja, pode me passar. Se nao tiver, tudo bem; me avisa e seguimos para a proxima etapa.`;
  }
  return `Perfeito. Para eu liberar ${materialLabel} e seguir com seu atendimento comercial da forma correta, preciso validar tambem o CNPJ da loja. Pode me informar o numero completo?`;
}

function buildSalesBookGateReply(script) {
  const stage = Number(script?.stage || 1);
  if (stage <= 1) {
    return 'Eu consigo liberar o BOOK DE VENDAS assim que concluirmos seu pre-cadastro. E rapidinho e isso garante que seu atendimento siga do jeito certo. Para avancarmos, voce possui CNPJ ativo?';
  }
  if (stage === 2) {
    return 'Eu ja separo o BOOK DE VENDAS para a proxima etapa, mas antes preciso confirmar um requisito obrigatorio da revenda. Voce possui loja fisica?';
  }
  if (stage === 3) {
    return 'Estamos quase la. Para eu direcionar seu atendimento da forma certa e seguir com a analise, me diz primeiro de qual cidade voce e.';
  }
  if (stage === 4) {
    return 'Perfeito, estamos avancando. Para seguir com a triagem e liberar o proximo passo, me fala por favor o seu nome.';
  }
  if (stage === 5) {
    return 'Falta pouco. Para eu concluir essa etapa e seguir para a liberacao correta do atendimento, me informa o melhor telefone para contato.';
  }
  if (stage === 6) {
    return 'Estamos na reta final. Se tiver Instagram da loja, pode me passar. Se nao tiver, tudo bem; me avisa e seguimos.';
  }
  return 'Para liberar o proximo passo do atendimento e o acesso ao material comercial, preciso validar tambem o seu CNPJ. Pode me informar o numero completo?';
}

function buildSalesBookPresentation(profile, script, options = {}) {
  const firstName = sanitizeCustomerName(
    script?.data?.nome ||
    profile?.customerName ||
    profile?.pushName ||
    ''
  );
  const razaoSocial = String(script?.data?.razaoSocial || profile?.companyLegalName || '').trim();
  const prefix = firstName ? `Perfeito, ${firstName}!` : 'Perfeito!';
  const mode = String(options.mode || 'release');

  if (mode === 'resend') {
    return `${prefix} Estou te reenviando o nosso Book de Vendas para facilitar sua analise. Nele voce identifica o posicionamento das linhas e as categorias com melhor potencial para o perfil da sua loja. Assim que olhar, me diga o que chamou mais sua atencao e eu sigo com voce de forma consultiva.`;
  }

  if (razaoSocial) {
    return `${prefix} CNPJ validado e ativo. Razao social localizada: ${razaoSocial}. Sera um prazer ter a ${razaoSocial} no time da Classe Couro. Estou te enviando agora o nosso Book de Vendas para voce conhecer as linhas, o posicionamento comercial e o potencial de revenda. Analise com calma. Depois posso tambem te mostrar uma vitrine de referencia com sugestoes de pedido inicial.`;
  }

  return `${prefix} Pre-cadastro recebido e validado. Estou te enviando agora o nosso Book de Vendas para voce conhecer as linhas, o posicionamento comercial e o potencial de revenda da Classe Couro. Analise com calma. Depois posso tambem te mostrar uma vitrine de referencia com sugestoes de pedido inicial.`;
}

function buildSalesBookCaption(profile, script) {
  const firstName = sanitizeCustomerName(
    script?.data?.nome ||
    profile?.customerName ||
    ''
  );
  const leadTag = firstName ? `Para ${firstName}` : 'Apresentacao comercial';
  return `${cfg.salesBook.documentCaption} | ${leadTag}`;
}

function wantsVitrine(text) {
  const norm = normalizeText(text);
  return [
    'vitrine', 'ver a vitrine', 'quero ver a vitrine', 'pode enviar a vitrine',
    'me mostra a vitrine', 'pode mostrar a vitrine'
  ].some((k) => norm.includes(normalizeText(k)));
}

function wantsB2BAccess(text) {
  const norm = normalizeText(text);
  return [
    'site b2b', 'portal b2b', 'acesso b2b', 'link b2b', 'site de pedidos',
    'portal de pedidos', 'acesso ao sistema', 'link do sistema', 'login b2b',
    'entrar no portal', 'acessar o portal'
  ].some((k) => norm.includes(normalizeText(k)));
}

function showsOrderReadiness(text) {
  const norm = normalizeText(text);
  return [
    'como faco o pedido', 'como faço o pedido', 'quero fazer pedido', 'quero fazer o pedido',
    'ja fiz minhas escolhas', 'já fiz minhas escolhas', 'como eu compro',
    'como finalizo', 'quero fechar', 'como faco para comprar', 'como faço para comprar',
    'quero pedir', 'fazer pedido', 'efetuar pedido', 'como pedir', 'como eu faco para pedir',
    'como eu faço para pedir', 'finalizar meu pedido', 'fechar meu pedido'
  ].some((k) => norm.includes(normalizeText(k)));
}

function showsCommercialEngagement(text) {
  const norm = normalizeText(text);
  return [
    'gostei', 'tenho interesse', 'quero seguir', 'quero avancar', 'quero avançar',
    'quero ver mais', 'quero comprar', 'como faco', 'como faço', 'me envia',
    'me mande', 'me mostra', 'pode enviar', 'pode mostrar', 'quero acessar',
    'site', 'portal', 'pedido'
  ].some((k) => norm.includes(normalizeText(k)));
}

function buildVitrineConsentReply(profile) {
  const firstName = sanitizeCustomerName(profile?.customerName || profile?.pushName || '');
  const prefix = firstName ? `${firstName},` : 'Perfeito,';
  return `${prefix} alem do book, tenho uma vitrine de referencia que facilita muito a visualizacao de um pedido inicial. Sao sugestoes montadas em faixas de R$ 2.000, R$ 4.000 e R$ 6.000, com as pecas de melhor giro da colecao atual. Posso te enviar agora?`;
}

function buildVitrinePresentationReply(profile) {
  const firstName = sanitizeCustomerName(profile?.customerName || profile?.pushName || '');
  const prefix = firstName ? `${firstName},` : 'Perfeito,';
  return `${prefix} segue a vitrine de referencia. Ela mostra combinacoes com boa leitura comercial e facilita a visualizacao de um pedido inicial em faixas de R$ 2.000, R$ 4.000 e R$ 6.000. Depois que voce olhar, me diz qual faixa faz mais sentido pro seu momento e eu te ajudo a montar.`;
}

function buildB2BConsentReply(profile) {
  const firstName = sanitizeCustomerName(profile?.customerName || profile?.pushName || '');
  const prefix = firstName ? `${firstName},` : 'Para o proximo passo,';
  return `${prefix} posso te liberar o acesso ao nosso portal exclusivo de pedidos. Por la voce navega pelo catalogo completo, visualiza disponibilidade e ja monta seu pedido com autonomia. Quer que eu te envie o link e as credenciais agora?`;
}

function buildB2BAccessReply(profile, script) {
  const cnpj = String(script?.data?.cnpj || profile?.companyCnpj || '').replace(/\D/g, '');
  const firstName = sanitizeCustomerName(script?.data?.nome || profile?.customerName || profile?.pushName || '');
  const prefix = firstName ? `${firstName},` : 'Perfeito,';
  const password = cnpj.slice(0, 8);
  const cnpjFormatted = cnpj.length === 14
    ? `${cnpj.slice(0,2)}.${cnpj.slice(2,5)}.${cnpj.slice(5,8)}/${cnpj.slice(8,12)}-${cnpj.slice(12)}`
    : cnpj;
  return `${prefix} segue o acesso ao ${cfg.b2b.displayLabel}.\n\nPortal: ${cfg.b2b.url}\nLogin: ${cnpjFormatted}\nSenha: ${password}\n\nEntre com o CNPJ no login e use os 8 primeiros digitos como senha. Dentro do portal voce visualiza o catalogo completo e ja consegue montar seu pedido. Qualquer duvida na navegacao e so me chamar.`;
}

function normalizeCnpjSituation(value) {
  const norm = normalizeText(value).replace(/\s+/g, ' ').trim();
  if (norm === 'ativa') return 'ATIVA';
  if (norm === 'inapta') return 'INAPTA';
  if (norm === 'inativa') return 'INATIVA';
  if (norm === 'baixada') return 'BAIXADA';
  if (norm === 'suspensa') return 'SUSPENSA';
  if (norm) return String(value || '').trim().toUpperCase();
  return '';
}

async function requestJsonWithRetry(url, attempts, delayMs) {
  let lastError = null;
  for (let i = 0; i < Number(attempts || 1); i++) {
    try {
      const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
      const timeout = controller ? setTimeout(() => controller.abort(), 12000) : null;
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: controller ? controller.signal : undefined
      });
      if (timeout) clearTimeout(timeout);
      if (response.ok) {
        return { ok: true, status: response.status, data: await response.json() };
      }
      lastError = `http_${response.status}`;
    } catch (error) {
      lastError = String(error?.name || error?.message || 'fetch_failed');
    }

    if (i < (Number(attempts || 1) - 1)) {
      await new Promise((resolve) => setTimeout(resolve, Number(delayMs || 500)));
    }
  }
  return { ok: false, error: lastError || 'request_failed' };
}

async function lookupCnpjPublicData(cnpj, staticData) {
  const digits = String(cnpj || '').replace(/\D/g, '');
  if (digits.length !== 14) {
    return { ok: false, error: 'invalid_cnpj_length' };
  }

  if (!staticData.cnpjLookupCache || typeof staticData.cnpjLookupCache !== 'object') {
    staticData.cnpjLookupCache = {};
  }

  const cache = staticData.cnpjLookupCache;
  const cached = cache[digits];
  const nowMs = Date.now();
  const ttlMs = 1000 * 60 * 60 * 24 * 7;
  if (cached && Number(cached.cachedAtMs || 0) >= (nowMs - ttlMs)) {
    return { ...cached, fromCache: true };
  }

  try {
    const receitaWs = await requestJsonWithRetry(`https://www.receitaws.com.br/v1/cnpj/${digits}`, 2, 900);
    if (receitaWs.ok) {
      const data = receitaWs.data || {};
      const situation = normalizeCnpjSituation(data?.situacao || '');
      const razaoSocial = String(data?.nome || '').trim();
      const result = {
        ok: true,
        cnpj: digits,
        situation,
        isActive: situation === 'ATIVA',
        razaoSocial,
        fetchedAt: nowIso,
        source: 'ReceitaWS'
      };
      cache[digits] = { ...result, cachedAtMs: nowMs };
      return result;
    }

    const brasilApi = await requestJsonWithRetry(`https://brasilapi.com.br/api/cnpj/v1/${digits}`, 2, 700);
    if (brasilApi.ok) {
      const data = brasilApi.data || {};
      const situation = normalizeCnpjSituation(data?.descricao_situacao_cadastral || data?.situacao_cadastral || '');
      const razaoSocial = String(data?.razao_social || '').trim();
      const result = {
        ok: true,
        cnpj: digits,
        situation,
        isActive: situation === 'ATIVA',
        razaoSocial,
        fetchedAt: nowIso,
        source: 'BrasilAPI'
      };
      cache[digits] = { ...result, cachedAtMs: nowMs };
      return result;
    }

    return {
      ok: false,
      error: `receitaws_${receitaWs.error || 'failed'}__brasilapi_${brasilApi.error || 'failed'}`
    };
  } catch (error) {
    return {
      ok: false,
      error: String(error?.name || error?.message || 'lookup_failed')
    };
  }
}

function buildInactiveCnpjReply(profile, script) {
  const firstName = sanitizeCustomerName(script?.data?.nome || profile?.customerName || '');
  const razaoSocial = String(script?.data?.razaoSocial || '').trim();
  const situation = String(script?.data?.cnpjSituacao || 'INATIVA').trim();
  const prefix = firstName ? `Entendi, ${firstName}.` : 'Entendi.';
  const companySnippet = razaoSocial ? ` Consultei o cadastro e a razao social localizada foi ${razaoSocial}.` : '';
  return `${prefix} No momento, nao consigo prosseguir com o cadastro de revenda porque o CNPJ informado consta como ${situation}.${companySnippet} Se voce tiver outro CNPJ ativo, pode me enviar que eu valido para seguir com voce da forma correta.`;
}

function buildCnpjLookupUnavailableReply() {
  return 'Estou validando seu CNPJ para seguir com o cadastro da forma correta, mas tive uma instabilidade momentanea na consulta publica agora. Pode me reenviar o CNPJ em instantes para eu concluir essa validacao?';
}

function getRecentRevendaSignals(staticData, profile, script, nowIso) {
  const recipientNumber = String(profile?.number || '').trim();
  const history = staticData?.customerHistory?.[recipientNumber];
  if (!Array.isArray(history) || !history.length) {
    return {
      cnpjAtivo: '',
      lojaFisica: '',
      cidade: '',
      nome: '',
      telefone: '',
      instagram: '',
      cnpj: ''
    };
  }

  const nowMs = Date.parse(nowIso || new Date().toISOString());
  const startedAtMs = Date.parse(script?.startedAt || nowIso || new Date().toISOString());
  const minTs = Number.isFinite(startedAtMs) ? startedAtMs : (nowMs - (45 * 60 * 1000));

  const recent = history
    .filter((entry) => String(entry?.role || '') === 'customer')
    .filter((entry) => {
      const ts = Date.parse(String(entry?.timestamp || ''));
      if (!Number.isFinite(ts)) return true;
      return ts >= minTs && ts >= (nowMs - (45 * 60 * 1000));
    })
    .slice(-8);

  const out = {
    cnpjAtivo: '',
    lojaFisica: '',
    cidade: '',
    nome: '',
    telefone: '',
    instagram: '',
    cnpj: ''
  };

  for (const item of recent) {
    const text = String(item?.text || '').trim();
    if (!text) continue;

    const explicitCnpj = extractCnpj(text);
    const explicitName = sanitizeCustomerName(extractSelfIdentifiedName(text) || extractLikelyStandaloneName(text));
    const explicitPhone = extractPhone(text) || inferPhoneFromContext(text, profile?.number);
    const explicitCity = extractCity(text);
    const explicitInstagram = extractInstagram(text);
    const explicitLoja = inferLojaFisicaStatus(text);
    const explicitCnpjAtivo = inferCnpjAtivoStatus(text, explicitCnpj);

    if (!out.cnpj && explicitCnpj) out.cnpj = explicitCnpj;
    if (!out.cnpjAtivo && explicitCnpjAtivo) out.cnpjAtivo = explicitCnpjAtivo;
    if (!out.lojaFisica && explicitLoja) out.lojaFisica = explicitLoja;
    if (!out.cidade && explicitCity) out.cidade = explicitCity;
    if (!out.nome && explicitName) out.nome = explicitName;
    if (!out.telefone && explicitPhone) out.telefone = explicitPhone;
    if (!out.instagram && explicitInstagram) out.instagram = explicitInstagram;
  }

  return out;
}

async function runRevendaScript(profile, inboundText, identifiedName, nowIso, staticData, productSignals = {}) {
  const norm = normalizeText(inboundText);
  if (!profile.revendaScript || typeof profile.revendaScript !== 'object') {
    profile.revendaScript = initRevendaScriptState(nowIso);
  }

  const script = profile.revendaScript;
  script.updatedAt = nowIso;

  if (shouldRestartRevendaScript(script, inboundText)) {
    profile.revendaScript = initRevendaScriptState(nowIso);
  }

  const activeScript = profile.revendaScript;
  activeScript.updatedAt = nowIso;
  if (!profile.bookSalesAccess) profile.bookSalesAccess = 'locked_pending_triage';
  const yn = yesNoIntent(inboundText);
  const standaloneName = extractLikelyStandaloneName(inboundText);
  // In the revenda script, only reuse data captured in the current script flow.
  const nameFromInput = sanitizeCustomerName(identifiedName || standaloneName);
  const phoneFromInput = extractPhone(inboundText) || inferPhoneFromContext(inboundText, profile.number);
  const cityFromInput = extractCity(inboundText);
  const instagramFromInput = extractInstagram(inboundText);
  const cnpjFromInput = extractCnpj(inboundText);
  const lojaFisicaStatus = inferLojaFisicaStatus(inboundText);
  const cnpjAtivoStatus = inferCnpjAtivoStatus(inboundText, cnpjFromInput);
  const pessoaFisicaInterest = shouldRoutePessoaFisicaEcommerce(inboundText, activeScript);
  const recentSignals = getRecentRevendaSignals(staticData, profile, activeScript, nowIso);
  const profileKnownName = sanitizeCustomerName(profile?.customerName || profile?.pushName || '');
  const vitrineAssetsAvailable = Array.isArray(staticData?.vitrineAssets?.items) && staticData.vitrineAssets.items.length > 0;
  const shortAcknowledgement = isShortAcknowledgement(inboundText);

  if (!activeScript.active && !activeScript.completed) {
    activeScript.active = true;
    activeScript.stage = 1;
  }

  if (pessoaFisicaInterest) {
    activeScript.active = false;
    activeScript.disqualified = true;
    activeScript.disqualifiedReason = 'pessoa_fisica_ecommerce';
    profile.bookSalesAccess = 'locked_pf_ecommerce';
    profile.leadStage = 'varejo_site';
    return {
      forced: true,
      reply: buildPessoaFisicaEcommerceReply(profile)
    };
  }

  const inboundStage = Number(activeScript.stage || 1);

  // Prefill only with explicit information from this same inbound message.
  // A generic "sim/nao" must affect only the stage currently being answered.
  // Explicit signals from the recent conversation can be reused safely.
  if (!activeScript.data.cnpj && (cnpjFromInput || recentSignals.cnpj) && (looksLikeMaskedCnpjInput(inboundText) || recentSignals.cnpj)) {
    activeScript.data.cnpj = cnpjFromInput || recentSignals.cnpj;
  }
  if (!activeScript.data.cnpjAtivo && (cnpjAtivoStatus || cnpjFromInput || recentSignals.cnpjAtivo || recentSignals.cnpj) && inboundStage <= 1) {
    activeScript.data.cnpjAtivo = cnpjAtivoStatus || recentSignals.cnpjAtivo || (cnpjFromInput || recentSignals.cnpj ? 'sim' : '');
  }
  if (!activeScript.data.lojaFisica && (lojaFisicaStatus || recentSignals.lojaFisica) && inboundStage <= 2) {
    activeScript.data.lojaFisica = lojaFisicaStatus || recentSignals.lojaFisica;
  }
  // Cidade e um dado critico para marketing/raio de campanha.
  // Portanto, so aceitamos quando vier explicitamente na mensagem atual do lead.
  if (!activeScript.data.cidade && cityFromInput && inboundStage <= 3) {
    activeScript.data.cidade = cityFromInput;
  }
  if (!activeScript.data.nome && (nameFromInput || recentSignals.nome || profileKnownName) && inboundStage <= 4) {
    activeScript.data.nome = nameFromInput || recentSignals.nome || profileKnownName;
  }
  if (!activeScript.data.telefone && (phoneFromInput || recentSignals.telefone) && inboundStage <= 5) {
    activeScript.data.telefone = phoneFromInput || recentSignals.telefone;
  }
  if (!activeScript.data.instagram && (instagramFromInput || recentSignals.instagram) && inboundStage <= 6) {
    activeScript.data.instagram = instagramFromInput || recentSignals.instagram;
  }
  if (!activeScript.data.instagram && inboundStage <= 6 && (norm.includes('nao tenho instagram') || norm.includes('não tenho instagram') || norm.includes('nao tenho comigo no momento') || norm.includes('não tenho comigo no momento'))) {
    activeScript.data.instagram = 'nao informado';
  }

  if (wantsRevendaExplanation(inboundText)) {
    if (activeScript.stage <= 1) {
      return {
        forced: true,
        reply: 'Claro, sem problema. Essas informacoes servem apenas para o pre-cadastro inicial e para encaminhar seu atendimento ao representante responsavel pela sua regiao, que vai te orientar melhor e apresentar nosso catalogo. Me diz: voce possui CNPJ ativo?'
      };
    }

    if (activeScript.stage === 2) {
      return {
        forced: true,
        reply: 'Claro. Essas informacoes ajudam a direcionar seu atendimento da forma certa, sem te tomar muito tempo. Me confirma: voce possui loja fisica?'
      };
    }
  }

  if (wantsCommercialMaterial(inboundText) && !activeScript.completed) {
    profile.bookSalesAccess = 'locked_pending_triage';
    return {
      forced: true,
      reply: buildCommercialMaterialGateReply(activeScript, productSignals, profile)
    };
  }

  if (wantsSalesBook(inboundText) && !activeScript.completed) {
    profile.bookSalesAccess = 'locked_pending_triage';
    return {
      forced: true,
      reply: buildSalesBookGateReply(activeScript)
    };
  }

  if (wantsSalesBook(inboundText) && activeScript.completed && profile.bookSalesAccess === 'eligible') {
    return {
      forced: true,
      reply: buildSalesBookPresentation(profile, activeScript, { mode: 'resend' }),
      sendSalesBookPdf: true,
      salesBookCaption: buildSalesBookCaption(profile, activeScript)
    };
  }

  if (
    activeScript.completed &&
    profile.bookSalesAccess === 'eligible' &&
    showsOrderReadiness(inboundText) &&
    !profile.b2bLinkSentAt
  ) {
    profile.awaitingB2BConsent = false;
    profile.b2bConsentGrantedAt = nowIso;
    profile.b2bLinkSentAt = nowIso;
    return {
      forced: true,
      reply: buildB2BAccessReply(profile, activeScript)
    };
  }

  if (activeScript.completed && profile.bookSalesAccess === 'eligible' && vitrineAssetsAvailable && wantsVitrine(inboundText)) {
    profile.awaitingVitrineConsent = false;
    profile.vitrineConsentAskedAt = profile.vitrineConsentAskedAt || nowIso;
    profile.vitrineShownAt = nowIso;
    return {
      forced: true,
      reply: buildVitrinePresentationReply(profile),
      sendVitrineAssets: true
    };
  }

  if (activeScript.completed && profile.bookSalesAccess === 'eligible' && vitrineAssetsAvailable && profile.awaitingVitrineConsent) {
    if (yn === 'yes') {
      profile.awaitingVitrineConsent = false;
      profile.vitrineConsentGrantedAt = nowIso;
      profile.vitrineShownAt = nowIso;
      return {
        forced: true,
        reply: buildVitrinePresentationReply(profile),
        sendVitrineAssets: true
      };
    }
    if (yn === 'no') {
      profile.awaitingVitrineConsent = false;
      profile.vitrineConsentDeclinedAt = nowIso;
    }
    if (yn === 'unknown' && !shortAcknowledgement) {
      profile.awaitingVitrineConsent = false;
      profile.vitrineConsentDismissedAt = nowIso;
    }
  }

  if (
    activeScript.completed &&
    profile.bookSalesAccess === 'eligible' &&
    profile.salesBookLastSentAt &&
    !profile.awaitingVitrineConsent &&
    !profile.vitrineShownAt &&
    vitrineAssetsAvailable &&
    shortAcknowledgement &&
    !wantsSalesBook(inboundText) &&
    !wantsB2BAccess(inboundText)
  ) {
    profile.awaitingVitrineConsent = true;
    profile.vitrineConsentAskedAt = nowIso;
    return {
      forced: true,
      reply: buildVitrineConsentReply(profile)
    };
  }

  if (activeScript.completed && profile.bookSalesAccess === 'eligible' && wantsB2BAccess(inboundText)) {
    profile.awaitingB2BConsent = false;
    profile.b2bLinkSentAt = nowIso;
    return {
      forced: true,
      reply: buildB2BAccessReply(profile, activeScript)
    };
  }

  if (
    activeScript.completed &&
    profile.bookSalesAccess === 'eligible' &&
    !profile.b2bLinkSentAt &&
    !profile.awaitingB2BConsent &&
    shortAcknowledgement &&
    (profile.vitrineShownAt || (!vitrineAssetsAvailable && profile.salesBookLastSentAt))
  ) {
    profile.awaitingB2BConsent = true;
    profile.b2bConsentAskedAt = nowIso;
    return {
      forced: true,
      reply: buildB2BConsentReply(profile)
    };
  }

  if (activeScript.completed && profile.bookSalesAccess === 'eligible' && profile.awaitingB2BConsent) {
    if (yn === 'yes') {
      profile.awaitingB2BConsent = false;
      profile.b2bConsentGrantedAt = nowIso;
      profile.b2bLinkSentAt = nowIso;
      return {
        forced: true,
        reply: buildB2BAccessReply(profile, activeScript)
      };
    }
    if (yn === 'no') {
      profile.awaitingB2BConsent = false;
      profile.b2bConsentDeclinedAt = nowIso;
    }
    if (yn === 'unknown' && !shortAcknowledgement) {
      profile.awaitingB2BConsent = false;
      profile.b2bConsentDismissedAt = nowIso;
    }
  }

  if (!activeScript.completed) {
  // Hard gate for mandatory sequence:
  // without CNPJ ativo confirmed, do not move beyond stage 1;
  // without loja fisica confirmed, do not move beyond stage 2.
  if (!activeScript.data.cnpjAtivo && Number(activeScript.stage || 1) > 1) {
    activeScript.stage = 1;
  }
  if (!activeScript.data.lojaFisica && Number(activeScript.stage || 1) > 2) {
    activeScript.stage = 2;
  }

  // Fast-forward stages when mandatory fields were already provided.
  for (let i = 0; i < 8; i++) {
    if (activeScript.stage === 1) {
      if (!activeScript.data.cnpjAtivo && inboundStage === 1 && yn === 'yes') activeScript.data.cnpjAtivo = 'sim';
      if (!activeScript.data.cnpjAtivo && inboundStage === 1 && yn === 'no') activeScript.data.cnpjAtivo = 'nao';
      if (activeScript.data.cnpjAtivo === 'sim') {
        activeScript.stage = 2;
        continue;
      }
      if (activeScript.data.cnpjAtivo === 'nao') {
        activeScript.active = false;
        activeScript.disqualified = true;
        activeScript.disqualifiedReason = 'cnpj_inativo_ou_ausente';
        profile.bookSalesAccess = 'locked_ineligible';
        profile.leadStage = 'encerrado_sem_cnpj';
        return {
          forced: true,
          reply: buildSemCnpjSiteReply(profile)
        };
      }
      break;
    }

    if (activeScript.stage === 2) {
      if (!activeScript.data.lojaFisica && inboundStage === 2 && yn === 'yes') activeScript.data.lojaFisica = 'sim';
      if (!activeScript.data.lojaFisica && inboundStage === 2 && yn === 'no') activeScript.data.lojaFisica = 'nao';
      if (activeScript.data.lojaFisica === 'sim') {
        activeScript.stage = 3;
        continue;
      }
      if (activeScript.data.lojaFisica === 'nao') {
        activeScript.active = false;
        activeScript.disqualified = true;
        activeScript.disqualifiedReason = 'sem_loja_fisica';
        profile.bookSalesAccess = 'locked_ineligible';
        profile.leadStage = 'encerrado_sem_loja_fisica';
        return {
          forced: true,
          reply: 'Sem problema, obrigado pela sinceridade. No momento, nao vamos conseguir prosseguir com o seu cadastramento no nosso B2B, porque a revenda direta exige loja fisica. Agradeco sinceramente o seu interesse na Classe Couro. Quando esse requisito estiver atendido, sera um prazer continuar seu atendimento por aqui. Obrigado pelo seu contato e conte com a gente.'
        };
      }
      break;
    }

    if (activeScript.stage === 3) {
      if (activeScript.data.cidade) {
        activeScript.stage = 4;
        continue;
      }
      break;
    }

    if (activeScript.stage === 4) {
      if (activeScript.data.nome) {
        activeScript.stage = 5;
        continue;
      }
      break;
    }

    if (activeScript.stage === 5) {
      if (activeScript.data.telefone) {
        activeScript.stage = 6;
        continue;
      }
      break;
    }

    if (activeScript.stage === 6) {
      if (activeScript.data.instagram) {
        activeScript.stage = 7;
        continue;
      }
      break;
    }

    if (activeScript.stage === 7) {
      if (looksLikeMaskedCnpjInput(inboundText) && cnpjFromInput) {
        activeScript.data.cnpj = cnpjFromInput;
      }
      if (activeScript.data.cnpj) {
        if (!isValidCnpj(activeScript.data.cnpj)) {
          activeScript.data.cnpj = '';
          activeScript.cnpjValidationStatus = 'checksum_invalid';
          profile.bookSalesAccess = 'locked_invalid_cnpj';
          return {
            forced: true,
            reply: 'Quero seguir com voce da forma certa, mas esse CNPJ parece invalido no formato informado. Pode me enviar novamente o numero completo do CNPJ?'
          };
        }
        activeScript.stage = 8;
        activeScript.active = false;
        activeScript.cnpjValidationStatus = 'checksum_valid';
        const cnpjLookup = await lookupCnpjPublicData(activeScript.data.cnpj, staticData);
        if (!cnpjLookup.ok) {
          activeScript.completed = true;
          activeScript.cnpjLookupStatus = 'lookup_unavailable';
          profile.leadStage = 'qualificando';
          profile.bookSalesAccess = 'eligible';
          return {
            forced: true,
            reply: buildSalesBookPresentation(profile, activeScript, { mode: 'release' }),
            sendSalesBookPdf: true,
            salesBookCaption: buildSalesBookCaption(profile, activeScript)
          };
        }

        activeScript.data.razaoSocial = String(cnpjLookup.razaoSocial || '').trim();
        activeScript.data.cnpjSituacao = String(cnpjLookup.situation || '').trim();
        activeScript.cnpjLookupStatus = cnpjLookup.isActive ? 'active' : 'inactive';
        profile.companyLegalName = activeScript.data.razaoSocial || profile.companyLegalName || '';
        profile.companyCnpj = activeScript.data.cnpj;
        profile.companyCnpjSituation = activeScript.data.cnpjSituacao;

        if (!cnpjLookup.isActive) {
          activeScript.stage = 7;
          activeScript.active = true;
          activeScript.completed = false;
          activeScript.data.cnpj = '';
          profile.bookSalesAccess = 'locked_invalid_cnpj_status';
          return {
            forced: true,
            reply: buildInactiveCnpjReply(profile, activeScript)
          };
        }

        activeScript.completed = true;
        profile.leadStage = 'qualificando';
        profile.bookSalesAccess = 'eligible';
        return {
          forced: true,
          reply: buildSalesBookPresentation(profile, activeScript, { mode: 'release' }),
          sendSalesBookPdf: true,
          salesBookCaption: buildSalesBookCaption(profile, activeScript)
        };
      }
      break;
    }

    break;
  }

  if (activeScript.stage === 1) {
    return {
      forced: true,
      reply: 'Ola, seja bem-vindo a Classe. Vou te fazer algumas perguntas rapidas para entender seu perfil e seguir com o pre-cadastro. Voce possui CNPJ ativo?'
    };
  }

  if (activeScript.stage === 2) {
    return { forced: true, reply: 'Perfeito, isso ja nos permite seguir para a proxima etapa. Voce possui loja fisica?' };
  }

  if (activeScript.stage === 3) {
    return {
      forced: true,
      reply: 'Otimo, isso tambem e um dos requisitos para seguirmos com o pre-cadastro. Para eu direcionar seu atendimento da forma certa, de qual cidade voce e?'
    };
  }

  if (activeScript.stage === 4) {
    return {
      forced: true,
      reply: 'Perfeito, isso ja me ajuda bastante. Me fala por favor o seu nome.'
    };
  }

  if (activeScript.stage === 5) {
    return { forced: true, reply: `Perfeito, ${activeScript.data.nome || 'tudo certo'}. Qual e o melhor telefone para contato?` };
  }

  if (activeScript.stage === 6) {
    return { forced: true, reply: 'Perfeito, isso nos ajuda a direcionar seu atendimento para o representante da sua regiao. Voce tem Instagram da loja? Se tiver, pode me passar. Se nao tiver, tudo bem.' };
  }

  if (activeScript.stage === 7) {
    return { forced: true, reply: 'Perfeito, obrigado por compartilhar. Pode me informar o numero do seu CNPJ?' };
  }

  } // end if (!activeScript.completed)

  return { forced: false, reply: '' };
}

function pickRelevantKnowledge(intent) {
  const base = [];
  base.push(...cfg.knowledge.businessSummary);
  base.push(...cfg.knowledge.salesProcess);

  if (intent === 'preco_orcamento' || intent === 'atacado_quantidade') {
    base.push('Preco e condicao comercial dependem de produto, acabamento e quantidade.');
    base.push('Quando possivel, pedir quantidade e prazo desejado para acelerar proposta.');
  }

  if (intent === 'prazo_entrega') {
    base.push('Prazo depende da disponibilidade e da regiao de entrega.');
    base.push('Coletar cidade/UF e urgencia para retorno assertivo.');
  }

  if (intent === 'pos_venda_reclamacao' || intent === 'troca_devolucao' || intent === 'cancelamento') {
    base.push('Priorizar acolhimento e transicao para atendimento humano.');
    base.push('Evitar decisoes finais sem validacao do consultor responsavel.');
  }

  return base.slice(0, 8);
}

function scoreDynamicRule(rule, inboundText, intent) {
  if (!rule || typeof rule !== 'object') return null;

  const ruleIntent = String(rule.intent || 'geral').trim() || 'geral';
  const intentCompatible = ruleIntent === 'geral' || ruleIntent === intent;
  if (!intentCompatible) return null;

  const pattern = String(rule.pattern || '').trim();
  const responseGuidance = String(rule.responseGuidance || '').trim();
  if (!responseGuidance) return null;

  let matched = false;
  if (!pattern) {
    matched = true;
  } else {
    try {
      const regex = new RegExp(pattern, 'i');
      matched = regex.test(String(inboundText || '')) || regex.test(normalizeText(inboundText));
    } catch {
      matched = false;
    }
  }

  if (!matched) return null;

  return {
    intent: ruleIntent,
    pattern,
    responseGuidance,
    priority: Number(rule.priority || 50),
    source: String(rule.source || 'dynamic')
  };
}

function scoreMandatoryDirective(directive, inboundText) {
  if (!directive || typeof directive !== 'object') return null;
  const objective = String(directive.objective || '').trim();
  const questions = Array.isArray(directive.questions) ? directive.questions.map((q) => String(q || '').trim()).filter(Boolean) : [];
  const keywords = Array.isArray(directive.keywords) ? directive.keywords.map((k) => normalizeText(k)).filter(Boolean) : [];

  if (!objective && questions.length === 0) return null;

  const norm = normalizeText(inboundText);
  const keywordHits = keywords.filter((k) => k && norm.includes(k));
  const questionHits = questions
    .map((q) => normalizeText(q))
    .filter((q) => q && (norm.includes(q.slice(0, 16)) || q.includes(norm.slice(0, 16))));

  const matched = keywordHits.length > 0 || questionHits.length > 0;
  if (!matched) return null;

  return {
    fileName: String(directive.fileName || ''),
    filePath: String(directive.filePath || ''),
    objective,
    questions: questions.slice(0, 8),
    keywords: keywords.slice(0, 8),
    enforcement: String(directive.enforcement || 'preserve_objective'),
    score: (keywordHits.length * 2) + questionHits.length
  };
}

function tokenizeForKnowledge(text) {
  return normalizeText(text)
    .replace(/[^a-z0-9à-ÿ\s]/g, ' ')
    .split(/\s+/)
    .filter((x) => x && x.length >= 4);
}

function isReadableKnowledgeLine(value) {
  const line = String(value || '').trim();
  if (!line || line.length < 20) return false;

  const norm = normalizeText(line);
  const blocked = ['endstream', 'endobj', ' xref ', '%pdf', ' obj '];
  if (blocked.some((k) => norm.includes(k))) return false;

  const printable = (line.match(/[A-Za-zÀ-ÿ0-9 ,.!?;:()\/_\-]/g) || []).length;
  const letters = (line.match(/[A-Za-zÀ-ÿ]/g) || []).length;
  const printableRatio = printable / line.length;
  const letterRatio = letters / line.length;
  return printableRatio >= 0.82 && letterRatio >= 0.45;
}

function scoreKnowledgeLine(line, inboundText, intent) {
  const normLine = normalizeText(line);
  const inboundTokens = Array.from(new Set(tokenizeForKnowledge(inboundText))).slice(0, 14);
  let score = 0;

  for (const token of inboundTokens) {
    if (token && normLine.includes(token)) score += 2;
  }

  const intentHints = {
    saudacao: ['atender', 'ajudar', 'bem-vindo', 'contar', 'falar'],
    produto_catalogo: ['produto', 'carteira', 'cinto', 'bolsa', 'acessorio', 'linha'],
    atacado_quantidade: ['atacado', 'revenda', 'quantidade', 'pedido', 'cnpj'],
    preco_orcamento: ['preco', 'orcamento', 'condicao', 'quantidade'],
    institucional_empresa: ['classe', 'marca', 'historia', 'qualidade'],
  };

  for (const k of (intentHints[intent] || [])) {
    if (normLine.includes(k)) score += 1;
  }

  return score;
}

function detectProductCategoryFromText(text) {
  const norm = normalizeText(text);

  if (norm.includes('carteira') && norm.includes('mascul')) return 'CARTEIRAS MASCULINAS';
  if (norm.includes('carteira') && norm.includes('feminin')) return 'CARTEIRAS FEMININAS';
  if (norm.includes('cinto') && norm.includes('mascul')) return 'CINTOS MASCULINOS';
  if (norm.includes('cinto') && norm.includes('feminin')) return 'CINTOS FEMININOS';
  if (norm.includes('bolsa')) return 'BOLSAS FEMININAS';
  if (norm.includes('mochila') && norm.includes('mascul')) return 'MOCHILAS MASCULINAS';
  if (norm.includes('mochila') && norm.includes('feminin')) return 'MOCHILAS FEMININAS';
  if (norm.includes('kit') && norm.includes('mascul')) return 'KITS MASCULINOS';
  if (norm.includes('kit') && norm.includes('feminin')) return 'KITS FEMININOS';
  if ((norm.includes('porta celular') || norm.includes('necessaire') || norm.includes('acessorio')) && norm.includes('mascul')) return 'ACESSORIOS MASCULINOS';
  if ((norm.includes('porta celular') || norm.includes('necessaire') || norm.includes('acessorio')) && norm.includes('feminin')) return 'ACESSORIOS FEMININOS';

  return '';
}

function buildProductCatalogContext(staticData, inboundText) {
  const catalog = staticData.productCatalog && typeof staticData.productCatalog === 'object'
    ? staticData.productCatalog
    : {};
  const categories = catalog.categories && typeof catalog.categories === 'object'
    ? catalog.categories
    : {};

  const categoryNames = Object.keys(categories);
  if (categoryNames.length === 0) {
    return {
      available: false,
      categoryDetected: '',
      summaryLines: []
    };
  }

  const categoryDetected = detectProductCategoryFromText(inboundText);
  const summaryLines = [];

  if (categoryDetected && categories[categoryDetected]) {
    const topRefs = (categories[categoryDetected].top10 || [])
      .slice(0, 5)
      .map((item) => String(item.displayType || item.category || '').trim())
      .filter(Boolean);
    if (topRefs.length > 0) {
      summaryLines.push(`Categoria consultada: ${categoryDetected}. Destaques internos: ${topRefs.join(' | ')}`);
    }
  } else {
    summaryLines.push(`Categorias de produto disponiveis: ${categoryNames.slice(0, 12).join(' | ')}`);
  }

  return {
    available: true,
    categoryDetected,
    summaryLines
  };
}

function buildDynamicKnowledgeBlock(staticData, inboundText, intent) {
  const dk = (staticData && staticData.dynamicKnowledge && typeof staticData.dynamicKnowledge === 'object')
    ? staticData.dynamicKnowledge
    : {};

  const rules = Array.isArray(dk.activeRules) ? dk.activeRules : [];
  const matchedRules = [];

  for (const rule of rules) {
    const scored = scoreDynamicRule(rule, inboundText, intent);
    if (scored) matchedRules.push(scored);
  }

  matchedRules.sort((a, b) => Number(b.priority || 0) - Number(a.priority || 0));
  const selectedRules = matchedRules.slice(0, 5);

  const topBacklogQuestions = Array.isArray(dk.topBacklogQuestions) ? dk.topBacklogQuestions : [];
  const selectedQuestions = topBacklogQuestions
    .filter((q) => {
      const qi = String(q.intent || 'geral');
      return qi === 'geral' || qi === intent;
    })
    .slice(0, 2)
    .map((q) => String(q.question || '').trim())
    .filter(Boolean);

  const ml = dk.machineLearning && typeof dk.machineLearning === 'object' ? dk.machineLearning : {};
  const mlHighlights = Array.isArray(ml.highlights) ? ml.highlights : [];
  const scoredMl = mlHighlights
    .map((h) => String(h || '').trim())
    .filter((h) => isReadableKnowledgeLine(h))
    .map((h) => ({ text: h, score: scoreKnowledgeLine(h, inboundText, intent) }))
    .sort((a, b) => Number(b.score || 0) - Number(a.score || 0));

  let selectedMl = scoredMl
    .filter((x) => Number(x.score || 0) > 0)
    .slice(0, 6)
    .map((x) => x.text);

  if (selectedMl.length === 0) {
    selectedMl = scoredMl.slice(0, 3).map((x) => x.text);
  }

  const lines = selectedRules.map((r) => `Regra dinamica (${r.intent}, p${r.priority}): ${r.responseGuidance}`);
  if (selectedQuestions.length > 0) {
    lines.push(`Duvidas recorrentes recentes: ${selectedQuestions.join(' | ')}`);
  }
  for (const m of selectedMl) {
    lines.push(`Base interna relevante: ${m}`);
  }

  const mlDocuments = Array.isArray(ml.documents) ? ml.documents : [];
  const scoredChunks = [];
  for (const doc of mlDocuments) {
    const fileName = String(doc?.fileName || '').trim();
    const ragChunks = Array.isArray(doc?.ragChunks) ? doc.ragChunks : [];
    for (const chunk of ragChunks) {
      const text = String(chunk || '').trim();
      if (!isReadableKnowledgeLine(text)) continue;
      const score = scoreKnowledgeLine(text, inboundText, intent);
      if (score <= 0) continue;
      scoredChunks.push({
        fileName,
        text,
        score,
      });
    }
  }
  scoredChunks.sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  for (const item of scoredChunks.slice(0, 5)) {
    lines.push(`RAG local relevante [${item.fileName}]: ${item.text.slice(0, 260)}`);
  }

  const mandatoryDirectives = Array.isArray(ml.mandatoryDirectives) ? ml.mandatoryDirectives : [];
  const matchedMandatory = [];
  for (const d of mandatoryDirectives) {
    const hit = scoreMandatoryDirective(d, inboundText);
    if (hit) matchedMandatory.push(hit);
  }
  matchedMandatory.sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  const selectedMandatory = matchedMandatory.slice(0, 2);
  for (const md of selectedMandatory) {
    lines.push(`Script mandatorio (${md.fileName}): objetivo=${md.objective}`);
    if (md.questions[0]) lines.push(`Primeira pergunta-chave: ${md.questions[0]}`);
  }

  const cycleSummary = dk.cycleSummary && typeof dk.cycleSummary === 'object' ? dk.cycleSummary : {};

  return {
    lines,
    matchedRulesCount: selectedRules.length,
    mandatoryMatchedCount: selectedMandatory.length,
    mandatoryDirectives: selectedMandatory,
    generatedAt: String(dk.generatedAt || ''),
    openBacklog: Number(cycleSummary.openBacklog || 0),
    crmLastRunAt: String(staticData.crmSync?.lastRunAt || ''),
    mlDocuments: Number(ml.activeDocuments || 0),
    mlIndexedNow: Number(ml.indexedNow || 0)
  };
}

function buildActiveProspectingBlock(ctx) {
  const lines = [];
  const core = Array.isArray(cfg.activeProspectingPrinciples?.core) ? cfg.activeProspectingPrinciples.core : [];
  const firstContact = Array.isArray(cfg.activeProspectingPrinciples?.firstContact) ? cfg.activeProspectingPrinciples.firstContact : [];
  const qualityGate = Array.isArray(cfg.activeProspectingPrinciples?.qualityGate) ? cfg.activeProspectingPrinciples.qualityGate : [];

  for (const item of core.slice(0, 5)) {
    lines.push(`Principio ativo: ${item}`);
  }

  if (ctx.isFirstInbound) {
    for (const item of firstContact.slice(0, 4)) {
      lines.push(`Primeiro contato: ${item}`);
    }
  }

  const intent = String(ctx.intent || 'geral');
  if (intent === 'institucional_empresa') {
    lines.push('Diretriz ativa: ao apresentar a empresa, use pitch curto com autoridade, diferencial e utilidade pratica para o perfil do cliente.');
  }
  if (intent === 'produto_catalogo') {
    lines.push('Diretriz ativa: em conversa de produto, responder de forma objetiva e consultiva, com opcao clara e uma pergunta curta de qualificacao.');
  }
  if (intent === 'atacado_quantidade') {
    lines.push('Diretriz ativa: em conversa de revenda/atacado, reduzir atrito, qualificar sem friccao e conduzir com seguranca para o proximo passo.');
  }
  if (ctx.mandatoryDirectiveMatched) {
    lines.push('Diretriz ativa: existe script mandatorio no contexto; adaptar a linguagem, mas preservar integralmente a finalidade comercial.');
  }
  if (ctx.productImageRequest) {
    lines.push('Diretriz ativa: se houver pedido de imagem, introduzir as imagens como apoio consultivo e manter o texto principal sem referencias tecnicas.');
  }

  for (const item of qualityGate.slice(0, 4)) {
    lines.push(`Checklist final: ${item}`);
  }

  return {
    lines: lines.slice(0, 18)
  };
}

return (async () => {
const inWorkDay = cfg.workDays.includes(dow);
const inWorkTime = inAnyWindow(minutesNow, cfg.workWindows);
const inBusinessHours = inWorkDay && inWorkTime;
const greetingLabel = getGreetingLabel(hh);

const staticData = $getWorkflowStaticData('global');
if (!staticData.dailyCounts) staticData.dailyCounts = {};
if (!staticData.hourlyCounts) staticData.hourlyCounts = {};
if (!staticData.minuteCounts) staticData.minuteCounts = {};
if (!staticData.aiMinuteCounts) staticData.aiMinuteCounts = {};
if (!staticData.customerProfiles) staticData.customerProfiles = {};
if (!staticData.customerHistory) staticData.customerHistory = {};
if (!staticData.humanQueue) staticData.humanQueue = [];
if (!staticData.learningBacklog) staticData.learningBacklog = [];
if (!staticData.lastAiCallMs) staticData.lastAiCallMs = 0;
if (!staticData.dynamicKnowledge) staticData.dynamicKnowledge = {};
if (!staticData.crmSync) staticData.crmSync = {};

for (const key of Object.keys(staticData.dailyCounts)) {
  if (key !== dayKey) delete staticData.dailyCounts[key];
}
for (const key of Object.keys(staticData.hourlyCounts)) {
  if (!key.startsWith(dayKey)) delete staticData.hourlyCounts[key];
}
for (const key of Object.keys(staticData.minuteCounts)) {
  if (!key.startsWith(hourKey)) delete staticData.minuteCounts[key];
}
for (const key of Object.keys(staticData.aiMinuteCounts)) {
  if (!key.startsWith(hourKey)) delete staticData.aiMinuteCounts[key];
}

const inboundText = String(input.inboundText || '').slice(0, cfg.maxInputChars).trim();
const recipientNumber = String(input.number || '').replace(/\D/g, '');
let outboundNumber = recipientNumber;
const intentDetection = detectIntent(inboundText);
const routeDecision = String(input.routeDecision || '').trim();
const cacheHit = Boolean(input.cacheHit) && String(input.cachedReplyText || '').trim().length > 0;
const cachedReplyText = String(input.cachedReplyText || '').trim();
const messageComplexity = String(input.messageComplexity || '').trim() || 'medium';
const routeIntent = String(input.routeIntent || '').trim();
const ragContextLines = Array.isArray(input.ragContextLines) ? input.ragContextLines : [];
const ragContextSummary = String(input.ragContextSummary || '').trim();
const leadScore = Number(input.leadScore || 0);
const ragTopScore = Number(input.ragTopScore || 0);
const routerOk = Boolean(input.routerOk);
// Dual-LLM fields from router
const llmReplyText = String(input.llmReplyText || '').trim();
const llmProvider = String(input.llmProvider || '').trim();
const llmModel = String(input.llmModel || '').trim();
const llmLatencyMs = Number(input.llmLatencyMs || 0);
const llmStructuredData = input.llmStructuredData || {};
const llmLeadScore = input.llmLeadScore || {};
const leadMemory = input.leadMemory && typeof input.leadMemory === 'object' ? input.leadMemory : {};
const memoryGuidance = Array.isArray(input.memoryGuidance)
  ? input.memoryGuidance.map((line) => String(line || '').trim()).filter(Boolean)
  : [];
const answeredSlots = leadMemory.answeredSlots && typeof leadMemory.answeredSlots === 'object'
  ? leadMemory.answeredSlots
  : {};
const answeredSlotsSummary = Object.entries(answeredSlots)
  .map(([key, value]) => `${key}=${String(value || '').trim()}`)
  .filter((line) => !/=$/i.test(line))
  .slice(0, 6)
  .join(' | ');
const detectedIntent = routeIntent || intentDetection.intent;
const detectedIntentScore = intentDetection.score;
const extractedEntities = extractEntities(inboundText);
const humanPriority = ['pos_venda_reclamacao', 'troca_devolucao', 'cancelamento'].includes(detectedIntent);

let allowAi = true;
let blockReason = '';
const ignoredNumbers = getIgnoredNumbersSet(staticData, input.dynamicBlockedNumbers);
const alwaysAllowedNumbers = getAlwaysAllowedNumbersSet(staticData, input.dynamicAlwaysAllowedNumbers);
const alwaysAllowedNumber = Boolean(recipientNumber && alwaysAllowedNumbers.has(recipientNumber));

if (!recipientNumber) {
  allowAi = false;
  blockReason = 'no_recipient';
} else if (ignoredNumbers.has(recipientNumber)) {
  allowAi = false;
  blockReason = 'blocked_number';
  outboundNumber = '';
} else if (!inBusinessHours) {
  allowAi = false;
  blockReason = 'out_of_hours';
} else {
  const currentMs = Date.now();
  const nextDaily = Number(staticData.dailyCounts[dayKey] || 0) + 1;
  const nextHourly = Number(staticData.hourlyCounts[hourKey] || 0) + 1;
  const nextMinute = Number(staticData.minuteCounts[minuteKey] || 0) + 1;
  const nextAiMinute = Number(staticData.aiMinuteCounts[minuteKey] || 0) + 1;
  const secondsSinceLastAi = (currentMs - Number(staticData.lastAiCallMs || 0)) / 1000;

  if (nextDaily > cfg.maxMsgsPerDay || nextHourly > cfg.maxMsgsPerHour || nextMinute > cfg.maxMsgsPerMinute) {
    allowAi = false;
    blockReason = 'volume';
  } else if (cacheHit) {
    allowAi = false;
    blockReason = 'cache_hit';
    staticData.dailyCounts[dayKey] = nextDaily;
    staticData.hourlyCounts[hourKey] = nextHourly;
    staticData.minuteCounts[minuteKey] = nextMinute;
  } else if (secondsSinceLastAi < cfg.minGlobalAiIntervalSeconds) {
    allowAi = false;
    blockReason = 'ai_cooldown';
    staticData.dailyCounts[dayKey] = nextDaily;
    staticData.hourlyCounts[hourKey] = nextHourly;
    staticData.minuteCounts[minuteKey] = nextMinute;
  } else if (nextAiMinute > cfg.maxAiCallsPerMinute) {
    allowAi = false;
    blockReason = 'ai_minute_limit';
    staticData.dailyCounts[dayKey] = nextDaily;
    staticData.hourlyCounts[hourKey] = nextHourly;
    staticData.minuteCounts[minuteKey] = nextMinute;
  } else {
    staticData.dailyCounts[dayKey] = nextDaily;
    staticData.hourlyCounts[hourKey] = nextHourly;
    staticData.minuteCounts[minuteKey] = nextMinute;
    staticData.aiMinuteCounts[minuteKey] = nextAiMinute;
    staticData.lastAiCallMs = currentMs;
  }
}

const hasValidOpenAiKey = true;
if (allowAi && !hasValidOpenAiKey) {
  allowAi = false;
  blockReason = 'missing_key';
}

let profile = staticData.customerProfiles[recipientNumber] || {
  number: recipientNumber,
  pushName: input.pushName || 'Cliente',
  customerName: '',
  customerNameSource: '',
  firstSeenAt: nowIso,
  lastSeenAt: nowIso,
  messageCount: 0,
  lastIntent: 'geral',
  leadStage: 'novo',
  notes: ''
};

if (profile.customerName) {
  profile.customerName = sanitizeCustomerName(profile.customerName);
}
if (leadMemory.customerName) {
  profile.customerName = sanitizeCustomerName(leadMemory.customerName);
  profile.customerNameSource = profile.customerNameSource || 'router_memory';
}
if (leadMemory.summary) profile.notes = String(leadMemory.summary).trim();
if (leadMemory.nextStep) profile.nextStep = String(leadMemory.nextStep).trim();
if (leadMemory.leadStage) profile.leadStage = String(leadMemory.leadStage).trim();
if (leadMemory.productFocus) profile.lastProductFocus = String(leadMemory.productFocus).trim();
if (leadMemory.productCategory) profile.lastProductCategory = String(leadMemory.productCategory).trim();

const previousMessageCount = Number(profile.messageCount || 0);
const identifiedName = extractSelfIdentifiedName(inboundText);
if (identifiedName) {
  profile.customerName = sanitizeCustomerName(identifiedName);
  profile.customerNameSource = 'self_identified';
  profile.customerNameUpdatedAt = nowIso;
}
const preferredCustomerName = resolvePreferredCustomerName(profile, input.pushName || profile.pushName || '');
if (preferredCustomerName.name) {
  profile.customerName = preferredCustomerName.name;
  profile.customerNameSource = preferredCustomerName.source;
  profile.customerNameUpdatedAt = nowIso;
}

const quotedInboundText = String(input.quotedText || '').trim();
const semanticInboundText = quotedInboundText
  ? `${inboundText}\n${quotedInboundText}`
  : inboundText;
const productSignals = detectProductFocusSignals(semanticInboundText, extractedEntities, profile);
if (!productSignals.productFocus && leadMemory.productFocus) productSignals.productFocus = String(leadMemory.productFocus).trim();
if (!productSignals.productCategory && leadMemory.productCategory) productSignals.productCategory = String(leadMemory.productCategory).trim();
if (productSignals.productFocus) profile.lastProductFocus = productSignals.productFocus;
if (productSignals.productCategory) profile.lastProductCategory = productSignals.productCategory;
if (productSignals.linePreference) profile.lastProductLinePreference = productSignals.linePreference;
if (productSignals.productFocus || productSignals.productCategory || productSignals.linePreference || productSignals.imageRequest) {
  profile.lastProductContextAt = nowIso;
}

const customerName = sanitizeCustomerName(String(profile.customerName || '').trim());
const isFirstInbound = previousMessageCount === 0;
const minutesSinceLastModelResponse = profile.lastOpenAiResponseAt
  ? ((Date.now() - new Date(profile.lastOpenAiResponseAt).getTime()) / 60000)
  : Number.POSITIVE_INFINITY;
const previousOpenAiResponseId = (
  profile.lastOpenAiResponseId &&
  Number.isFinite(minutesSinceLastModelResponse) &&
  minutesSinceLastModelResponse <= Number(cfg.openAiConversationStateMaxMinutes || 360) &&
  !Boolean(profile.revendaScript?.active)
) ? String(profile.lastOpenAiResponseId) : '';

profile.pushName = input.pushName || profile.pushName || 'Cliente';
profile.customerName = customerName;
profile.lastSeenAt = nowIso;
profile.messageCount = previousMessageCount + 1;
let effectiveDetectedIntent = detectedIntent;
if (effectiveDetectedIntent === 'geral' && (productSignals.productFocus || productSignals.imageRequest || productSignals.linePreference)) {
  effectiveDetectedIntent = 'produto_catalogo';
}
const openAiReasoningEffort = resolveReasoningEffort(effectiveDetectedIntent, inboundText, humanPriority);
profile.lastIntent = effectiveDetectedIntent;
staticData.customerProfiles[recipientNumber] = profile;

if (!staticData.customerHistory[recipientNumber]) staticData.customerHistory[recipientNumber] = [];
const history = staticData.customerHistory[recipientNumber];
history.push({
  role: 'customer',
  text: inboundText,
  timestamp: nowIso,
  intent: effectiveDetectedIntent
});
while (history.length > 32) history.shift();

let mandatoryScriptReply = '';
let sendSalesBookPdf = false;
let sendVitrineAssets = false;
let salesBookCaption = '';
const normInbound = normalizeText(inboundText);
const shouldHandleRevendaScript = (
  likelyRevendaScript(normInbound, effectiveDetectedIntent) ||
  inferPessoaFisicaInterest(inboundText) ||
  Boolean(profile.revendaScript?.active) ||
  Boolean(profile.revendaScript?.completed && profile.bookSalesAccess === 'eligible')
);
const scriptCanOverrideNow = !['blocked_number', 'no_recipient', 'out_of_hours', 'missing_key'].includes(blockReason);
if (recipientNumber && shouldHandleRevendaScript && scriptCanOverrideNow) {
  const scriptResult = await runRevendaScript(profile, inboundText, identifiedName, nowIso, staticData, productSignals);
  if (scriptResult?.forced && scriptResult.reply) {
    mandatoryScriptReply = String(scriptResult.reply).trim();
    allowAi = false;
    blockReason = 'mandatory_script';
    sendSalesBookPdf = Boolean(scriptResult.sendSalesBookPdf);
    sendVitrineAssets = Boolean(scriptResult.sendVitrineAssets);
    salesBookCaption = String(scriptResult.salesBookCaption || '').trim();
  }
  staticData.customerProfiles[recipientNumber] = profile;
}

const recentHistory = history.slice(-10).map((h) => {
  const role = h.role === 'customer' ? 'Cliente' : 'Eduardo';
  return `${role}: ${String(h.text || '').slice(0, 240)}`;
}).join('\n');
const quotedText = quotedInboundText;
const effectiveCustomerMessage = quotedText
  ? `${inboundText}\n\nMensagem marcada pelo cliente:\n${quotedText}`
  : inboundText;

const baseKnowledge = pickRelevantKnowledge(effectiveDetectedIntent);
const dynamicBlock = buildDynamicKnowledgeBlock(staticData, semanticInboundText, effectiveDetectedIntent);
const productCatalogBlock = buildProductCatalogContext(staticData, semanticInboundText);
const finalKnowledgeLines = [...baseKnowledge, ...dynamicBlock.lines, ...productCatalogBlock.summaryLines, ...ragContextLines].slice(0, 20);
const relevantKnowledge = finalKnowledgeLines.join('\n- ');
const primaryMandatoryDirective = (dynamicBlock.mandatoryDirectives || [])[0] || null;
const mandatoryDirectiveMatched = Boolean(primaryMandatoryDirective);
const activeProspectingBlock = buildActiveProspectingBlock({
  isFirstInbound,
  intent: effectiveDetectedIntent,
  mandatoryDirectiveMatched,
  productImageRequest: Boolean(productSignals.imageRequest)
});

const customerSnapshot = [
  `Nome de tratamento: ${customerName || 'nao informado'}`,
  `Contato: ${recipientNumber || 'nao resolvido'}`,
  `Mensagens no historico: ${history.length}`,
  `Primeiro contato deste cliente: ${isFirstInbound ? 'sim' : 'nao'}`,
  `Ultima intencao detectada: ${effectiveDetectedIntent}`,
  `Complexidade classificada: ${messageComplexity}`,
  `Rota recomendada: ${routeDecision || 'local_only'}`,
  `Lead score: ${leadScore}`,
  `Estagio atual do lead: ${profile.leadStage || 'novo'}`,
  `Resumo operacional salvo: ${String(profile.notes || '').slice(0, 220) || 'nenhum'}`,
  `Proximo passo salvo: ${String(profile.nextStep || '').slice(0, 180) || 'nenhum'}`,
  `Memoria persistente do router: ${String(leadMemory.summary || '').slice(0, 220) || 'nenhuma'}`,
  `Campos ja respondidos: ${answeredSlotsSummary || 'nenhum'}`,
  `Pergunta comercial em aberto: ${String(leadMemory.openQuestion || input.contextCarryover?.pendingQuestion || '').slice(0, 180) || 'nenhuma'}`,
  `Momento comercial persistido: ${String(leadMemory.commercialMomentum || '').trim() || 'indefinido'}`
].join('\n');

const aiSystemPrompt = [
  `Voce e ${cfg.knowledge.consultantName}, ${cfg.knowledge.position} da ${cfg.knowledge.companyName}.`,
  'Seu objetivo e conduzir o cliente para avanco comercial com clareza, naturalidade, inteligencia contextual e senso real de ajuda.',
  'Tom: masculino, consultivo, acolhedor, descontraido mas corporativo, sem parecer robo ou bot engessado.',
  '',
  'REGRAS ABSOLUTAS:',
  '- NUNCA use emojis ou simbolos especiais nas respostas.',
  '- NUNCA responda algo incoerente com a pergunta do cliente. Leia a pergunta com atencao antes de responder.',
  '- NUNCA invente preco, prazo, disponibilidade ou dado especifico sem ter essa informacao na base.',
  '- NUNCA repita estrutura fixa em mensagens consecutivas.',
  '- NUNCA faca mais de 1 pergunta por mensagem.',
  '- NUNCA inicie com saudacao (o sistema ja adiciona automaticamente).',
  '',
  'DIRETRIZES PRINCIPAIS:',
  '- Antes de redigir a resposta, releia internamente a pergunta do cliente e confirme que sua resposta responde diretamente aquilo.',
  '- Se o cliente marcou (Respondeu a) uma mensagem anterior, interprete a mensagem marcada como contexto de escolha ou selecao de produto e responda de acordo.',
  '- Revise o historico recente para garantir coerencia: nao repita informacoes ja dadas, nao pergunte o que ja foi respondido.',
  '- Se a memoria persistente listar campos ja respondidos, trate esses dados como confirmados e nao pergunte novamente.',
  '- Se houver pergunta comercial em aberto na memoria, interprete a mensagem atual como resposta a essa pergunta antes de abrir nova qualificacao.',
  '- Se o cliente ja informou produto, quantidade ou preferencia no historico, use esse contexto na resposta atual.',
  '- Em perguntas de produto, seja direto, consultivo e contextual. Nao faca perguntas genericas se o produto ja foi indicado.',
  '- Se o cliente pergunta como fazer o pedido ou demonstra que ja fez escolhas, conduza diretamente ao proximo passo (B2B ou contato humano).',
  '- Ao apresentar a empresa, use pitch curto: autoridade, diferencial e utilidade pratica para o perfil do cliente.',
  '- Crie conexao sem soar artificial ou manipulativo. Seja simpatico, direto e util.',
  '- Textos curtos e objetivos: 2 a 4 frases no maximo por resposta. Clientes nao gostam de textos longos.',
  '- Se faltar dado para uma decisao comercial, faca UMA pergunta objetiva e curta.',
  '- Responda em portugues do Brasil com acentuacao correta.',
  '- Se houver script mandatorio aplicavel, preserve objetivo e finalidade comercial; adapte apenas a linguagem.',
  '- Em casos sensiveis (reclamacao, troca, devolucao, cancelamento, bloqueio de API, timeout), sinalize needs_human=true com human_reason descritivo.',
  '',
  'CHECKLIST INTERNO (valide antes de finalizar):',
  '- Minha resposta esta diretamente conectada ao que o cliente perguntou nesta mensagem especifica?',
  '- Se o cliente marcou uma mensagem, minha resposta leva em conta o que foi marcado?',
  '- Minha resposta evita generalizacao, repeticao e desconexao com o contexto?',
  '- Minha resposta e curta, direta e util?',
  '',
  'Retorne SOMENTE JSON valido (sem markdown) com o formato:',
  '{"reply":"string","intent":"string","confidence":0.0,"needs_human":false,"human_reason":"string","lead_stage":"novo|qualificando|proposta|negociacao|fechamento|pos_venda","follow_up_question":"string","extracted_entities":{},"customer_memory_update":{"notes":"string","next_step":"string"}}'
].join('\n');

const aiUserPrompt = [
  `Mensagem recebida: ${effectiveCustomerMessage || '(vazia)'}`,
  quotedText ? `Mensagem marcada pelo cliente: ${quotedText}` : 'Mensagem marcada pelo cliente: nenhuma',
  `Cliente identificado por nome: ${customerName || 'nao'}`,
  `Saudacao atual (horario local): ${greetingLabel}`,
  `Primeiro contato: ${isFirstInbound ? 'sim' : 'nao'}`,
  `Intencao detectada por regra: ${effectiveDetectedIntent} (score ${detectedIntentScore.toFixed(2)})`,
  `Classificacao de complexidade: ${messageComplexity}`,
  `Decisao do roteador: ${routeDecision || 'local_only'}`,
  `Lead score calculado: ${leadScore}`,
  `Roteador local disponivel: ${routerOk ? 'sim' : 'nao'}`,
  `Entidades detectadas: ${JSON.stringify(extractedEntities)}`,
  `Foco de produto resolvido: ${productSignals.productFocus || 'nenhum'}`,
  `Categoria de produto resolvida: ${productSignals.productCategory || 'nenhuma'}`,
  `Preferencia de linha detectada: ${productSignals.linePreference || 'nenhuma'}`,
  `Pedido de imagem detectado: ${productSignals.imageRequest ? 'sim' : 'nao'}`,
  `Conversation state OpenAI disponivel: ${previousOpenAiResponseId ? 'sim' : 'nao'}`,
  `Reasoning effort atual: ${openAiReasoningEffort}`,
  '',
  'Contexto do cliente:',
  customerSnapshot,
  '',
  'Historico recente:',
  recentHistory || 'Sem historico relevante.',
  '',
  'Conhecimento comercial disponivel:',
  `- ${relevantKnowledge}`,
  '',
  'Playbook comercial ativo neste atendimento:',
  `- ${activeProspectingBlock.lines.join('\n- ')}`,
  '',
  `Regras dinamicas aplicadas neste atendimento: ${dynamicBlock.matchedRulesCount}`,
  `Backlog aberto no ciclo CRM: ${dynamicBlock.openBacklog}`,
  `Ultima sincronizacao CRM: ${dynamicBlock.crmLastRunAt || 'nao sincronizado'}`,
  `Documentos ativos no aprendizado: ${dynamicBlock.mlDocuments}`,
  `Documentos reindexados no ultimo ciclo: ${dynamicBlock.mlIndexedNow}`,
  `Catalogo de produto disponivel: ${productCatalogBlock.available ? 'sim' : 'nao'}`,
  `Categoria de produto detectada agora: ${productCatalogBlock.categoryDetected || 'nenhuma'}`,
  `Resumo RAG do roteador: ${ragContextSummary || 'nenhum'}`,
  `Top score RAG: ${ragTopScore ? ragTopScore.toFixed(3) : '0.000'}`,
  `Memoria do router disponivel: ${Object.keys(leadMemory).length > 0 ? 'sim' : 'nao'}`,
  `Pergunta pendente no router: ${String(input.contextCarryover?.pendingQuestion || leadMemory.openQuestion || '').slice(0, 180) || 'nenhuma'}`,
  `Campos respondidos no router: ${answeredSlotsSummary || 'nenhum'}`,
  `Scripts mandatorios aplicaveis agora: ${dynamicBlock.mandatoryMatchedCount || 0}`,
  mandatoryDirectiveMatched
    ? `Objetivo mandatorio: ${String(primaryMandatoryDirective.objective || '').slice(0, 220)}`
    : 'Objetivo mandatorio: nenhum',
  mandatoryDirectiveMatched && Array.isArray(primaryMandatoryDirective.questions) && primaryMandatoryDirective.questions[0]
    ? `Pergunta-chave inicial: ${String(primaryMandatoryDirective.questions[0]).slice(0, 220)}`
    : 'Pergunta-chave inicial: n/a',
  '',
  'Memoria operacional adicional do router:',
  memoryGuidance.length > 0 ? `- ${memoryGuidance.join('\n- ')}` : '- nenhuma',
  '',
  'Responda no formato JSON solicitado no system prompt.'
].join('\n');

const fallbackText = blockReason === 'blocked_number'
  ? cfg.blockedNumberMessage
  : blockReason === 'mandatory_script'
    ? mandatoryScriptReply
  : blockReason === 'cache_hit'
    ? cachedReplyText
  : (blockReason === 'volume' || blockReason === 'ai_minute_limit' || blockReason === 'ai_cooldown')
  ? cfg.highVolumeMessage
  : blockReason === 'no_recipient'
    ? cfg.unresolvedRecipientMessage
    : blockReason === 'missing_key'
      ? cfg.missingKeyMessage
      : cfg.outOfHoursMessage;

const salesBookAsset = staticData.salesBookAsset && typeof staticData.salesBookAsset === 'object'
  ? staticData.salesBookAsset
  : null;
const salesBookAssetAvailable = Boolean(String(salesBookAsset?.mediaBase64 || '').trim());
const vitrineAssets = staticData.vitrineAssets && typeof staticData.vitrineAssets === 'object'
  ? staticData.vitrineAssets
  : null;
const vitrineAssetsAvailable = Array.isArray(vitrineAssets?.items) && vitrineAssets.items.length > 0;

const humanEscalationCall = blockReason === 'missing_key';

return [{
  json: {
    instance: input.instance || '',
    remoteJid: input.remoteJid || '',
    resolutionStatus: input.resolutionStatus || 'unknown',
    messageId: input.messageId || '',
    number: outboundNumber,
    customerNumber: recipientNumber,
    pushName: profile.pushName,
    customerName,
    customerNameKnown: Boolean(customerName),
    isFirstInbound,
    inboundTextOriginal: input.inboundText,
    quotedText,
    quotedMessageId: input.quotedMessageId || '',
    promptInput: inboundText,
    allowAi,
    alwaysAllowedNumber,
    blockReason,
    maxOutputChars: cfg.maxOutputChars,
    maxOutputTokens: cfg.maxOutputTokens,
    maxAiCallsPerMinute: cfg.maxAiCallsPerMinute,
    minConfidenceForAutoSend: cfg.minConfidenceForAutoSend,
    openAiModel: cfg.openAiModel,
    openAiReasoningEffort,
    previousOpenAiResponseId,
    detectedIntent: effectiveDetectedIntent,
    detectedIntentScore,
    extractedEntities,
    productFocusResolved: productSignals.productFocus || '',
    productCategoryDetected: productSignals.productCategory || '',
    productLinePreference: productSignals.linePreference || '',
    productImageRequest: Boolean(productSignals.imageRequest),
    humanPriority,
    mandatoryScriptActive: Boolean(profile.revendaScript?.active),
    mandatoryScriptStage: Number(profile.revendaScript?.stage || 0),
    mandatoryScriptForced: blockReason === 'mandatory_script',
    bookSalesAccess: String(profile.bookSalesAccess || 'locked_pending_triage'),
    sendSalesBookPdf: Boolean(sendSalesBookPdf && salesBookAssetAvailable),
    sendVitrineAssets: Boolean(sendVitrineAssets && vitrineAssetsAvailable),
    salesBookCaption: salesBookCaption || cfg.salesBook.documentCaption,
    salesBookFileName: String(salesBookAsset?.fileName || cfg.salesBook.fileName),
    salesBookMimeType: String(salesBookAsset?.mimeType || cfg.salesBook.mimeType),
    salesBookAssetAvailable,
    vitrineAssetsAvailable,
    mandatoryDirectiveMatched,
    mandatoryDirectiveObjective: primaryMandatoryDirective ? String(primaryMandatoryDirective.objective || '') : '',
    mandatoryDirectiveQuestions: primaryMandatoryDirective ? (primaryMandatoryDirective.questions || []).slice(0, 8) : [],
    customerSnapshot,
    workTimezone: cfg.workTimezone,
    greetingLabel,
    dynamicRulesMatched: dynamicBlock.matchedRulesCount,
    dynamicMandatoryRulesMatched: dynamicBlock.mandatoryMatchedCount,
    dynamicKnowledgeGeneratedAt: dynamicBlock.generatedAt,
    activeProspectingRules: activeProspectingBlock.lines,
    crmLastRunAt: dynamicBlock.crmLastRunAt,
    productCatalogAvailable: productCatalogBlock.available,
    productCategoryDetected: productCatalogBlock.categoryDetected,
    routeDecision,
    cacheHit,
    cachedReplyText,
    messageComplexity,
    leadScore,
    ragContextLines,
    ragContextSummary,
    ragTopScore,
    contextCarryover: input.contextCarryover || {},
    leadMemory,
    memoryGuidance,
    routerOk,
    aiSystemPrompt,
    aiUserPrompt,
    fallbackText,
    humanEscalationCall,
    insideSalesOwnNumber: cfg.insideSalesOwnNumber || '',
    // Dual-LLM passthrough
    llmReplyText,
    llmProvider,
    llmModel,
    llmLatencyMs,
    llmStructuredData,
    llmLeadScore
  }
}];
})();
