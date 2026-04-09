FROM n8nio/n8n:2.11.3

USER root

ENV N8N_RUNNERS_ENABLED=false \
    N8N_DISABLE_PRODUCTION_MAIN_PROCESS=false

RUN node - <<'NODE'
const fs = require('fs');

const patches = [
  {
    path: '/usr/local/lib/node_modules/n8n/node_modules/@n8n/config/dist/configs/runners.config.js',
    from: 'this.enabled = true;',
    to: 'this.enabled = false;',
  },
  {
    path: '/usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-base/dist/nodes/Code/Code.node.js',
    from: 'const isJsRunner = runnersConfig.enabled;',
    to: 'const isJsRunner = false && runnersConfig.enabled;',
  },
];

for (const patch of patches) {
  const source = fs.readFileSync(patch.path, 'utf8');
  if (!source.includes(patch.from) && !source.includes(patch.to)) {
    throw new Error(`Padrao nao encontrado em ${patch.path}`);
  }
  const updated = source.includes(patch.to) ? source : source.replace(patch.from, patch.to);
  fs.writeFileSync(patch.path, updated);
}
NODE

USER node
