# Railway - Deploy e Troubleshooting

> **Projeto:** `remarkable-communication`
> **Servico:** `whats-agents`

## Fluxo de Deploy

```
1. git push origin main
2. Railway detecta push
3. (Opcional) Espera CI passar
4. Build com Railpack/Dockerfile
5. Healthcheck em /health
6. Troca de trafego para nova versao
```

---

## Verificar Status do Deploy

### Via CLI

```bash
# Status geral
railway status

# Logs em tempo real
railway logs

# Ultimas 100 linhas
railway logs -n 100
```

### Via Dashboard

1. railway.app → Projeto → Servico
2. Clicar no deploy mais recente
3. Ver logs de Build e Deploy

---

## Logs - Filtros Uteis

### CLI

```bash
# Erros
railway logs | grep -i error

# Warnings
railway logs | grep -i warn

# Requisicoes HTTP
railway logs | grep "HTTP"
```

### Dashboard (Log Explorer)

```
# Por servico
@service:whats-agents

# Por status HTTP
@httpStatus:500

# Por path
@path:/api/webhook

# Combinado
@service:whats-agents AND "error"
@httpStatus:500 OR @httpStatus:502
```

---

## Problemas Comuns

### 1. Build Falhou

**Sintoma:** Deploy para no build

**Diagnostico:**
```bash
railway logs --build
```

**Causas comuns:**
- Dependencia nao encontrada
- Erro de sintaxe no Dockerfile
- Versao Python/Node incompativel

**Solucao:**
```bash
# Testar build local
docker build -t test .

# Verificar pyproject.toml / requirements.txt
uv sync
```

### 2. App Nao Inicia

**Sintoma:** Deploy completa mas servico fica "unhealthy"

**Diagnostico:**
```bash
railway logs -n 100
```

**Causas comuns:**
- App nao escuta em `$PORT`
- Healthcheck falhando
- Erro de inicializacao

**Solucao:**
```python
# Garantir que escuta em $PORT
import os
port = int(os.getenv("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

### 3. Healthcheck Timeout

**Sintoma:** "Healthcheck failed"

**Diagnostico:**
```bash
# Verificar se /health responde
curl http://localhost:8000/health
```

**Causas:**
- Endpoint /health nao existe
- App demora muito pra iniciar
- Porta errada

**Solucao:**
```bash
# Aumentar timeout (padrao 300s)
RAILWAY_HEALTHCHECK_TIMEOUT_SEC=600
```

```python
# Endpoint simples
@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 4. Crash Loop (Restarts)

**Sintoma:** Servico reinicia constantemente

**Diagnostico:**
```bash
railway logs -n 200 | grep -E "(error|Error|ERROR|exception|Exception)"
```

**Causas:**
- Exception nao tratada
- Memoria insuficiente
- Conexao com banco falhando

**Solucao:**
- Verificar logs de erro
- Aumentar recursos se necessario
- Verificar variaveis de ambiente

### 5. Variaveis Nao Carregam

**Sintoma:** App nao encontra config

**Diagnostico:**
```bash
railway variables
```

**Solucao:**
1. Dashboard → Service → Variables
2. Verificar se variavel existe
3. Redeploy apos adicionar

---

## Redeploy Manual

### Via CLI

```bash
railway up
```

### Via Dashboard

1. CMD + K (Command Palette)
2. "Deploy Latest Commit"

### Forcar Rebuild Completo

1. Dashboard → Service → Settings
2. "Rebuild and Deploy"

---

## Rollback

### Via Dashboard

1. Service → Deployments
2. Clicar no deploy anterior
3. "Rollback to this deployment"

---

## Monitorar em Tempo Real

```bash
# Terminal 1: Logs
railway logs

# Terminal 2: Testar endpoint
watch -n 5 'curl -s https://whats-agents-production.up.railway.app/health'
```

---

## Checklist Pre-Deploy

- [ ] Testes passando localmente
- [ ] `uv sync` sem erros
- [ ] Dockerfile buildando local (se usar)
- [ ] Endpoint `/health` funcionando
- [ ] Variaveis de ambiente configuradas
- [ ] Branch correta (main)

---

## Checklist Pos-Deploy

- [ ] `railway logs` sem erros
- [ ] Healthcheck passou
- [ ] Endpoint principal respondendo
- [ ] Webhook recebendo mensagens
- [ ] Metricas normais

---

## Comandos de Emergencia

```bash
# Ver o que esta acontecendo
railway logs -n 100

# Acessar container
railway ssh

# Rodar comando no container
railway run python -c "from app.core.config import settings; print(settings)"

# Verificar variaveis
railway variables
```
