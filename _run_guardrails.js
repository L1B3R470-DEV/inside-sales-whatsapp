const fs = require('fs');
process.chdir('C:/Users/User/Desktop/PROJETO ATENDIMENTO WHATSAPP INSIDE SALES');
const guardrailsCode = fs.readFileSync('./guardrails.js','utf8');
const staticObj = JSON.parse(fs.readFileSync('./_staticData_dump.json','utf8'));
const globalData = staticObj.global;
const input = {
  instance: 'ATENDIMENTO_VENDAS_CLEAN',
  remoteJid: '557588340000@s.whatsapp.net',
  number: '557588340000',
  pushName: 'Phelper',
  inboundText: 'me envie o book de vendas',
  messageId: 'ACSIMTEST123456789012',
  routeDecision: 'local_only',
  cacheHit: false,
  cachedReplyText: '',
  messageComplexity: 'medium'
};
const getWorkflowStaticData = () => globalData;
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
(async () => {
  try {
    const fn = new AsyncFunction('$json','$getWorkflowStaticData', guardrailsCode);
    const res = await fn(input, getWorkflowStaticData);
    console.log(JSON.stringify(res,null,2));
  } catch (e) {
    console.error('ERR', e && e.stack || e);
  }
})();
