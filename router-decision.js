const payload = { ...$json };
const topology = {
  operationalHostRole: 'PC_CLS',
  operationalHostIp: '100.113.13.27',
  operationalDockerHostRole: 'PC_CLS',
  operationalDockerHostIp: '100.113.13.27',
  interactiveHostRole: 'PC_LBN',
  interactiveHostIp: '100.101.106.95',
  interactiveModeOnly: true,
  rejectLbnAsRuntime: true,
  rejectLbnDocker: true
};

const ROUTER_BASE_URL = String($env.ROUTER_BASE_URL || 'http://router:8091').replace(/\/$/, '');

try {
  const response = await fetch(`${ROUTER_BASE_URL}/route`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ...payload,
      topology
    })
  });

  if (!response.ok) {
    throw new Error(`router_http_${response.status}`);
  }

  const data = await response.json();
  return [{
    json: {
      ...payload,
      ...data,
      topology,
      routerOk: true
    }
  }];
} catch (error) {
  return [{
    json: {
      ...payload,
      topology,
      routerOk: false,
      routerError: String(error?.message || error || 'router_unavailable')
    }
  }];
}
