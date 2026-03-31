
SELECT id, key, participant, message, source, status, "messageTimestamp"
FROM "Message"
WHERE CAST(key AS text) LIKE '%114062134407423@lid%'
ORDER BY "messageTimestamp" DESC LIMIT 3;
