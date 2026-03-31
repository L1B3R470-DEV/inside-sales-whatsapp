const base = $node['Normalize Payload'].json;
const inputItems = (typeof $input !== 'undefined' && $input && typeof $input.all === 'function')
  ? $input.all()
  : [];
const contacts = inputItems.length > 0
  ? inputItems.map((item) => item.json || {}).filter(Boolean)
  : (Array.isArray($json?.value) ? $json.value : []);

const remoteJid = String(base.remoteJid || '').toLowerCase();
const isLid = remoteJid.endsWith('@lid');

function norm(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}

let resolvedJid = '';
let number = String(base.number || '').replace(/\D/g, '');
let resolutionStatus = 'passthrough';

if (/@s\.whatsapp\.net$/.test(remoteJid)) {
  resolvedJid = remoteJid;
  number = remoteJid.replace('@s.whatsapp.net', '').replace(/\D/g, '');
  resolutionStatus = 'resolved_direct';
}

if (isLid) {
  resolutionStatus = 'unresolved_lid';
  const staticData = $getWorkflowStaticData('global');
  if (!staticData.lidToSJid) staticData.lidToSJid = {};

  const cached = staticData.lidToSJid[remoteJid];
  if (cached && /@s\.whatsapp\.net$/i.test(String(cached))) {
    resolvedJid = String(cached).toLowerCase();
  }

  const sContacts = contacts.filter((c) => /@s\.whatsapp\.net$/i.test(String(c.remoteJid || '')));
  const lidContact = contacts.find((c) => String(c.remoteJid || '').toLowerCase() === remoteJid);
  const targetName = norm(base.pushName);

  const pickUnique = (arr) => (arr.length === 1 ? arr[0] : null);

  // 1) Match by exact normalized name
  if (!resolvedJid && targetName) {
    const byExactName = sContacts.filter((c) => norm(c.pushName) === targetName);
    const pickedExact = pickUnique(byExactName);
    if (pickedExact) resolvedJid = String(pickedExact.remoteJid || '').toLowerCase();
  }

  // 2) Match by partial name, but only when unique
  if (!resolvedJid && targetName && targetName.length >= 5) {
    const byContains = sContacts.filter((c) => {
      const candidate = norm(c.pushName);
      return candidate && (candidate.includes(targetName) || targetName.includes(candidate));
    });
    const pickedContains = pickUnique(byContains);
    if (pickedContains) resolvedJid = String(pickedContains.remoteJid || '').toLowerCase();
  }

  // 3) Fallback for modern WA LID: match by identical profile picture URL
  if (!resolvedJid && lidContact?.profilePicUrl) {
    const byProfilePic = sContacts.filter((c) => String(c.profilePicUrl || '') === String(lidContact.profilePicUrl || ''));
    const pickedByPic = pickUnique(byProfilePic);
    if (pickedByPic) {
      resolvedJid = String(pickedByPic.remoteJid || '').toLowerCase();
      resolutionStatus = 'resolved_from_lid_profilepic';
    }
  }

  if (resolvedJid && /@s\.whatsapp\.net$/.test(resolvedJid)) {
    staticData.lidToSJid[remoteJid] = resolvedJid;
    number = resolvedJid.replace('@s.whatsapp.net', '').replace(/\D/g, '');
    if (resolutionStatus === 'unresolved_lid') resolutionStatus = 'resolved_from_lid';
  } else {
    number = '';
  }
}

return [{
  json: {
    ...base,
    number,
    resolvedJid,
    resolutionStatus
  }
}];
