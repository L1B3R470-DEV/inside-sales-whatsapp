const payload = { ...$json };

try {
  const response = await fetch('http://host.docker.internal:8091/route', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`router_http_${response.status}`);
  }

  const data = await response.json();
  return [{
    json: {
      ...payload,
      ...data,
      routerOk: true
    }
  }];
} catch (error) {
  return [{
    json: {
      ...payload,
      routerOk: false,
      routerError: String(error?.message || error || 'router_unavailable')
    }
  }];
}
