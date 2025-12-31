# Railway - Quick Reference

> **Docs oficiais:** https://docs.railway.com/
> **Dashboard:** https://railway.app/dashboard

## Visao Geral

Railway e uma plataforma de deploy que faz build e deploy automatico a partir do GitHub.

**Projeto:** `remarkable-communication`
**Servico:** `whats-agents`
**Ambiente:** `production`

---

## CLI - Instalacao

```bash
# macOS
brew install railway

# npm
npm i -g @railway/cli

# Shell script
bash <(curl -fsSL cli.new)
```

---

## CLI - Comandos Principais

### Autenticacao

```bash
railway login              # Abre browser para auth
railway login --browserless # Sem browser (mostra codigo)
railway logout             # Encerrar sessao
```

### Projeto

```bash
railway link               # Linkar diretorio ao projeto
railway service            # Selecionar servico
railway environment        # Trocar ambiente
railway status             # Ver projeto/ambiente atual
```

### Logs

```bash
# Logs do servico atual
railway logs

# Ultimas N linhas
railway logs --lines 50

# Logs em tempo real (streaming)
railway logs

# Logs de um servico especifico
railway logs --service whats-agents

# Logs de build
railway logs --build

# Formato JSON
railway logs --json
```

### Deploy

```bash
# Deploy manual (sem push)
railway up

# Deploy sem esperar
railway up --detach
```

### Variaveis

```bash
# Ver variaveis
railway variables

# Rodar comando local com variaveis do Railway
railway run python app.py
railway run npm run dev

# Shell com variaveis
railway shell
```

### Acesso SSH

```bash
# Acessar shell do servico deployado
railway ssh
```

---

## GitHub Auto-Deploy

### Como Funciona

1. Push para branch conectada (ex: `main`)
2. Railway detecta commit
3. Build automatico (Railpack/Dockerfile)
4. Deploy se build OK

### Configurar Branch

1. Dashboard → Service Settings
2. Selecionar branch de deploy
3. Salvar

### Wait for CI

Se tiver GitHub Actions, Railway pode esperar CI passar:

```yaml
# .github/workflows/test.yml
on:
  push:
    branches:
      - main
```

- **WAITING** - CI rodando
- **SKIPPED** - CI falhou (deploy cancelado)
- **OK** - CI passou (deploy continua)

---

## Variaveis de Ambiente

### No Dashboard

1. Service → Variables
2. New Variable ou RAW Editor (colar .env)

### Variaveis Compartilhadas

1. Project Settings → Shared Variables
2. Disponivel para todos os servicos

### Referenciar Outras Variaveis

```bash
# Variavel compartilhada
DATABASE_URL=${{ shared.DATABASE_URL }}

# Variavel de outro servico
API_URL=https://${{ backend.RAILWAY_PUBLIC_DOMAIN }}

# Mesma variavel
FULL_URL=https://${{ RAILWAY_PUBLIC_DOMAIN }}/api
```

### Variaveis do Railway

| Variavel | Descricao |
|----------|-----------|
| `PORT` | Porta para o app escutar |
| `RAILWAY_PUBLIC_DOMAIN` | Dominio publico do servico |
| `RAILWAY_PRIVATE_DOMAIN` | Dominio interno (entre servicos) |
| `RAILWAY_ENVIRONMENT` | Nome do ambiente |
| `RAILWAY_SERVICE_NAME` | Nome do servico |

---

## Healthcheck

### Configurar

1. Criar endpoint `/health` que retorna HTTP 200
2. App deve escutar na porta `$PORT`

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Timeout

- **Padrao:** 300 segundos (5 min)
- **Customizar:** `RAILWAY_HEALTHCHECK_TIMEOUT_SEC=600`

### Importante

- Healthcheck so roda no **deploy** (nao e monitoramento continuo)
- Requisicoes vem de `healthcheck.railway.app`
- Servico so recebe trafego apos healthcheck passar

---

## Restart Policy

| Politica | Comportamento |
|----------|---------------|
| `Always` | Reinicia sempre que parar |
| `On Failure` | Reinicia so se crashar (padrao) |
| `Never` | Nunca reinicia |

**Padrao:** On Failure com max 10 restarts

**Plano pago:** Restarts ilimitados

---

## Build

### Deteccao Automatica

Railway detecta automaticamente:
- `Dockerfile` → Usa Docker
- `requirements.txt` / `pyproject.toml` → Python
- `package.json` → Node.js

### Railpack vs Nixpacks

- **Railpack** - Builder atual (recomendado)
- **Nixpacks** - Legacy (deprecated)

### Forcar Rebuild

```bash
# Via CLI
railway up

# Via Dashboard
CMD + K → "Redeploy"
```

---

## Troubleshooting

### Build Falhou

```bash
# Ver logs de build
railway logs --build

# Verificar Dockerfile local
docker build -t test .
```

### App Nao Inicia

1. Verificar se escuta em `$PORT`
2. Verificar healthcheck endpoint
3. Ver logs: `railway logs --lines 100`

### Timeout no Healthcheck

```bash
# Aumentar timeout
RAILWAY_HEALTHCHECK_TIMEOUT_SEC=600
```

### Ver Logs de Erro

```bash
# Filtrar por erro
railway logs | grep -i error

# No dashboard: Log Explorer com filtro
@service:whats-agents AND "error"
```

---

## Comandos Rapidos

```bash
# Ver status
railway status

# Logs rapidos
railway logs -n 50

# Rodar local com env do Railway
railway run uv run pytest

# SSH no container
railway ssh

# Redeploy
railway up
```
