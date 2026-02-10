# ENV-CONTRACT.md - Contrato de Ambientes

> **Sprint 18 - Auditoria e Integridade**
> Contrato formal entre ambientes DEV e PROD.
> **Atualizado:** Sprint 57 (Fevereiro 2026)

---

## Visao Geral

Este documento define o contrato de configuracao entre os ambientes **DEV** e **PROD** do Agente Julia.

| Ambiente | Supabase Project Ref | Railway Environment | APP_ENV |
|----------|---------------------|---------------------|---------|
| **PROD** | `jyqgbzhqavgpxqacduoi` | `production` | `production` |
| **DEV** | `ofpnronthwcsybfxnxgj` | `dev` | `dev` |

**NOTA:** A validacao de ambiente e project ref e feita em `app/api/routes/health.py` no endpoint `/health/deep`.

---

## Variaveis de Ambiente Obrigatorias

### PROD (production)

```bash
APP_ENV=production                           # OBRIGATORIO: identifica ambiente de producao
SUPABASE_URL=https://jyqgbzhqavgpxqacduoi.supabase.co
SUPABASE_PROJECT_REF=jyqgbzhqavgpxqacduoi   # Validado pelo /health/deep
SUPABASE_SERVICE_KEY=<prod_key>
EVOLUTION_API_URL=<prod_evolution>
EVOLUTION_INSTANCE=<prod_instance>
# OUTBOUND_ALLOWLIST nao necessario em PROD
```

### DEV

```bash
APP_ENV=dev                                  # OBRIGATORIO: identifica ambiente de desenvolvimento
SUPABASE_URL=https://ofpnronthwcsybfxnxgj.supabase.co
SUPABASE_PROJECT_REF=ofpnronthwcsybfxnxgj   # Validado pelo /health/deep
SUPABASE_SERVICE_KEY=<dev_key>
EVOLUTION_API_URL=<dev_evolution>
EVOLUTION_INSTANCE=<dev_instance>
OUTBOUND_ALLOWLIST=5511999999999,5511888888888  # OBRIGATORIO: numeros de teste
```

---

## Guardrails por Ambiente

### PROD

| Guardrail | Comportamento |
|-----------|---------------|
| DEV Allowlist | **DESABILITADO** (APP_ENV=production) |
| Opted Out | Bloqueia contato com opt-out |
| Cooling Off | Bloqueia apos resposta negativa |
| Quiet Hours | Bloqueia fora do horario comercial |
| Campaign Cooldown | Bloqueia reenvio dentro do cooldown |
| Human Bypass | **PERMITIDO** via Slack |

### DEV

| Guardrail | Comportamento |
|-----------|---------------|
| DEV Allowlist | **OBRIGATORIO** (fail-closed) |
| Opted Out | Bloqueia contato com opt-out |
| Cooling Off | Bloqueia apos resposta negativa |
| Quiet Hours | Bloqueia fora do horario comercial |
| Campaign Cooldown | Bloqueia reenvio dentro do cooldown |
| Human Bypass | **DESABILITADO** |

---

## DEV Allowlist (R-2: Fail-Closed)

### Comportamento

O DEV Allowlist e o guardrail MAIS RESTRITIVO do sistema:

1. **Verifica ANTES de qualquer outro guardrail**
2. **NAO tem bypass humano** - DEV nunca pode enviar para fora da allowlist
3. **Fail-closed**: Se allowlist vazia, bloqueia TUDO

### Logica

```python
if APP_ENV == "production":
    return ALLOW  # PROD nao verifica allowlist

if OUTBOUND_ALLOWLIST vazia:
    return BLOCK(reason="dev_allowlist_empty")  # Fail-closed

if telefone NOT IN OUTBOUND_ALLOWLIST:
    return BLOCK(reason="dev_allowlist")

return ALLOW
```

### Configuracao

```bash
# Formato: lista de numeros separados por virgula (so digitos)
OUTBOUND_ALLOWLIST=5511999999999,5511888888888

# Numeros sao normalizados automaticamente:
# "+55 (11) 99999-9999" -> "5511999999999"
```

### Validacao no /health/deep

O endpoint `/health/deep` valida que em DEV:
- `OUTBOUND_ALLOWLIST` NAO esta vazia
- Se vazia, retorna status `CRITICAL`

---

## Marcadores de Ambiente (app_settings)

Cada ambiente possui marcadores no banco para validacao cruzada:

```sql
-- PROD
INSERT INTO app_settings (key, value) VALUES
('environment', 'production'),
('supabase_project_ref', 'jyqgbzhqavgpxqacduoi');

-- DEV
INSERT INTO app_settings (key, value) VALUES
('environment', 'dev'),
('supabase_project_ref', 'ofpnronthwcsybfxnxgj');
```

### Validacao no /health/deep

O endpoint `/health/deep` verifica:
1. `APP_ENV` (variavel de ambiente) == `app_settings.environment` (banco)
2. `SUPABASE_PROJECT_REF` (variavel) == `app_settings.supabase_project_ref` (banco)

Se houver mismatch, retorna `CRITICAL` e recomenda rollback.

---

## Topologia Railway

```
remarkable-communication/
├── production/
│   └── whats-agents (PROD)
│       ├── APP_ENV=production
│       └── SUPABASE_PROJECT_REF=jyqgbzhqavgpxqacduoi
│
└── dev/
    └── whats-agents (DEV)
        ├── APP_ENV=dev
        ├── SUPABASE_PROJECT_REF=ofpnronthwcsybfxnxgj
        └── OUTBOUND_ALLOWLIST=<numeros_de_teste>
```

---

## Checklist de Deploy

### Antes de Deploy PROD

- [ ] Verificar que `APP_ENV=production` esta setado
- [ ] Verificar que `SUPABASE_PROJECT_REF` bate com banco PROD
- [ ] Rodar `/health/deep` e verificar todos checks OK
- [ ] Verificar que marcadores no banco existem

### Antes de Deploy DEV

- [ ] Verificar que `APP_ENV=dev` esta setado
- [ ] Verificar que `SUPABASE_PROJECT_REF` bate com banco DEV
- [ ] Verificar que `OUTBOUND_ALLOWLIST` NAO esta vazia
- [ ] Rodar `/health/deep` e verificar todos checks OK
- [ ] Verificar que marcadores no banco existem

---

## Troubleshooting

### /health/deep retorna CRITICAL

**Sintoma**: `DEPLOY TO WRONG ENVIRONMENT DETECTED!`

**Causa**: `APP_ENV` ou `SUPABASE_PROJECT_REF` nao bate com banco.

**Solucao**:
1. Verificar variaveis de ambiente no Railway
2. Verificar marcadores no banco (`app_settings`)
3. Se necessario, atualizar marcadores ou variaveis

### DEV bloqueando todos outbound

**Sintoma**: `[DEV GUARDRAIL] BLOCKED: OUTBOUND_ALLOWLIST vazia em DEV`

**Causa**: `OUTBOUND_ALLOWLIST` esta vazia ou nao configurada.

**Solucao**:
1. No Railway DEV, adicionar variavel `OUTBOUND_ALLOWLIST`
2. Listar numeros de teste separados por virgula
3. Redeploy para aplicar

### Mismatch de environment

**Sintoma**: `ENVIRONMENT MISMATCH! APP_ENV=dev, DB=production`

**Causa**: App conectando ao banco errado.

**Solucao**:
1. Verificar `SUPABASE_URL` e `SUPABASE_SERVICE_KEY`
2. Garantir que apontam para o banco correto
3. Redeploy para aplicar

---

---

## Referencia de Codigo

- **Config:** `app/core/config.py` - classe `Settings`
- **Health Check:** `app/api/routes/health.py` - endpoint `/health/deep`
- **Guardrails:** `app/services/guardrails/check.py`

---

## Historico

| Data | Alteracao |
|------|-----------|
| 2025-12-31 | Criacao do documento (Sprint 18 Auditoria) |
| 2026-02-10 | Verificacao de acuracia (Sprint 57) - contrato validado, nenhuma mudanca necessaria |
