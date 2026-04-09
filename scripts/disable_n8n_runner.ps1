param(
  [string]$ContainerName = "n8n"
)

$patch = @"
const fs = require('fs');
const p = '/usr/local/lib/node_modules/n8n/node_modules/@n8n/config/dist/configs/runners.config.js';
let s = fs.readFileSync(p, 'utf8');
if (!s.includes('this.enabled = false;')) {
  s = s.replace('this.enabled = true;', 'this.enabled = false;');
  fs.writeFileSync(p, s);
}
const out = fs.readFileSync(p, 'utf8').match(/this\.enabled = (true|false);/);
console.log(out ? out[0] : 'flag-not-found');
"@

docker exec $ContainerName node -e $patch
if ($LASTEXITCODE -ne 0) {
  throw "Falha ao aplicar patch do Task Runner no container $ContainerName."
}

docker restart $ContainerName | Out-Null
Start-Sleep -Seconds 3
docker exec $ContainerName node -e "const fs=require('fs');const p='/usr/local/lib/node_modules/n8n/node_modules/@n8n/config/dist/configs/runners.config.js';console.log(fs.readFileSync(p,'utf8').match(/this\.enabled = (true|false);/)[0])"
