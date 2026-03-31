const fs = require('fs');

const files = [
  '/work/guardrails.js',
  '/work/extract-reply.js',
  '/work/build-fallback-reply.js',
  '/work/normalize-payload.js',
];

for (const p of files) {
  const content = fs.readFileSync(p, 'utf8');
  // Compile-only check for syntax errors.
  // eslint-disable-next-line no-new-func
  new Function(content);
  console.log(`${p} syntax_ok`);
}
