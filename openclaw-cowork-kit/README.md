# OpenClaw Cowork Kit

Kit inicial para trabalho conjunto entre:

- este PC local;
- o PC do escritorio com Claude + agents;
- OpenClaw como gateway comum;
- SSH tunnel + loopback para acesso remoto seguro.

## Arquivos

- `office-host-setup.ps1`: prepara o PC do escritorio para hospedar o gateway e os agents.
- `local-client-ssh-loopback.ps1`: sobe o tunnel SSH local e configura este PC para usar o gateway remoto.
- `git-cowork-bootstrap.ps1`: cria uma estrutura minima de pastas para Git/cowork dentro do projeto.
- `CONVENCAO_AGENTES_SESSOES.txt`: padrao recomendado para nomes de agents e sessoes.
- `ESTRUTURA_GIT_COWORK.txt`: fluxo Git recomendado para trabalho concorrente.

## Fluxo recomendado

1. No PC do escritorio, rode:

```powershell
powershell -ExecutionPolicy Bypass -File .\office-host-setup.ps1 `
  -WorkspaceDir "C:\PROJETOS\ATENDENTE" `
  -GatewayToken "TROQUE_POR_UM_TOKEN_FORTE"
```

2. Nesta maquina, rode:

```powershell
powershell -ExecutionPolicy Bypass -File .\local-client-ssh-loopback.ps1 `
  -SshTarget "usuario@host-escritorio" `
  -GatewayToken "TROQUE_POR_O_MESMO_TOKEN_FORTE"
```

3. Teste a conexao:

```powershell
openclaw gateway probe --url ws://127.0.0.1:18789 --token TROQUE_POR_O_MESMO_TOKEN_FORTE
openclaw status
```

4. Abrir uma sessao ACP apontando para o agent principal do escritorio:

```powershell
openclaw acp --session agent:claude-office:main
```

## Observacoes

- O gateway do escritorio permanece em `loopback`, entao nao fica exposto na rede.
- O unico acesso remoto acontece pelo tunnel SSH local.
- Use o mesmo token do gateway nos dois lados.
- Se preferir, rode primeiro com `-DryRun` para inspecionar os comandos sem aplicar mudancas.
