
SELECT id, "remoteJid", "pushName", "profilePicUrl", "updatedAt"
FROM "Contact"
WHERE "remoteJid" = '114062134407423@lid'
   OR "pushName" = 'Classe Comercial Pedidos';

SELECT id, "remoteJid", "jidOptions", "updatedAt"
FROM "IsOnWhatsapp"
WHERE "remoteJid" = '114062134407423@lid';

SELECT id, key, "pushName", participant, message, "createdAt"
FROM "Message"
WHERE CAST(key AS text) LIKE '%114062134407423@lid%'
ORDER BY "createdAt" DESC LIMIT 5;
