# Queries de Auditoria - Guardrails

**Sprint Original:** 18.1 - Queries para análise de bloqueios e bypasses
**Atualizado:** Sprint 57 (Fevereiro 2026)

**IMPORTANTE:** Todas as queries neste documento foram validadas contra o schema atual e estão funcionais.

## 1. Bloqueios por opted_out em 24h

```sql
SELECT
    DATE_TRUNC('hour', ts) as hora,
    COUNT(*) as bloqueios
FROM business_events
WHERE event_type = 'outbound_blocked'
  AND event_props->>'block_reason' = 'opted_out'
  AND ts >= NOW() - INTERVAL '24 hours'
GROUP BY 1
ORDER BY 1;
```

## 2. Qual canal está gerando mais bypass?

```sql
SELECT
    event_props->>'channel' as canal,
    COUNT(*) as total_bypasses
FROM business_events
WHERE event_type = 'outbound_bypass'
  AND ts >= NOW() - INTERVAL '7 days'
GROUP BY 1
ORDER BY 2 DESC;
```

## 3. Quem autorizou bypass e por quê?

```sql
SELECT
    ts,
    cliente_id,
    event_props->>'actor_id' AS quem_autorizou,
    event_props->>'bypass_reason' AS motivo,
    event_props->>'block_reason' AS regra_bypassada,
    conversation_id,
    policy_decision_id
FROM business_events
WHERE event_type = 'outbound_bypass'
ORDER BY ts DESC
LIMIT 50;
```

## 4. Origem/método causando mais bloqueios

```sql
SELECT
    event_props->>'method' as metodo,
    event_props->>'block_reason' as razao,
    COUNT(*) as total
FROM business_events
WHERE event_type = 'outbound_blocked'
  AND ts >= NOW() - INTERVAL '7 days'
GROUP BY 1, 2
ORDER BY 3 DESC;
```

## 5. Reply sem inbound_proof (bug de race condition)

```sql
SELECT
    ts,
    cliente_id,
    conversation_id,
    event_props->>'inbound_interaction_id' as inbound_id,
    event_props->>'block_reason' as razao
FROM business_events
WHERE event_type IN ('outbound_blocked', 'outbound_bypass')
  AND event_props->>'method' = 'reply'
  AND (
      event_props->>'inbound_interaction_id' IS NULL
      OR conversation_id IS NULL
  )
  AND ts >= NOW() - INTERVAL '7 days'
ORDER BY ts DESC;
```

## 6. Fallbacks legados usados (migração incompleta)

```sql
SELECT
    ts,
    event_props->>'function' as funcao,
    event_props->>'telefone_prefix' as telefone_prefix
FROM business_events
WHERE event_type = 'outbound_fallback'
  AND ts >= NOW() - INTERVAL '24 hours'
ORDER BY ts DESC;
```

## 7. Resumo diário de bloqueios vs bypasses

```sql
SELECT
    DATE_TRUNC('day', ts) as dia,
    event_type,
    COUNT(*) as total
FROM business_events
WHERE event_type IN ('outbound_blocked', 'outbound_bypass')
  AND ts >= NOW() - INTERVAL '30 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

## 8. Warnings de integridade (buscar nos logs)

```bash
# Buscar warnings de integridade nos logs Railway
railway logs | grep "INTEGRITY_WARNING"

# OU localmente se tiver acesso aos logs
grep "INTEGRITY_WARNING" /var/log/julia/*.log | tail -100
```

**NOTA:** Logs do Railway podem ser acessados via `railway logs -n 100` (últimas 100 linhas) ou `railway logs` (streaming).

---

## Painel Diário (4 Queries Core)

Executar 1x/dia para monitoramento de saúde do canary.

### Q1: Volume por Tipo de Evento (24h)

```sql
SELECT
    event_type,
    COUNT(*) as total,
    COUNT(DISTINCT cliente_id) as clientes_unicos
FROM business_events
WHERE ts >= NOW() - INTERVAL '24 hours'
GROUP BY event_type
ORDER BY total DESC;
```

### Q2: Guardrail Blocked/Bypass por Razão

```sql
SELECT
    event_type,
    event_props->>'block_reason' as razao,
    event_props->>'channel' as canal,
    event_props->>'method' as metodo,
    COUNT(*) as total
FROM business_events
WHERE event_type IN ('outbound_blocked', 'outbound_bypass')
  AND ts >= NOW() - INTERVAL '24 hours'
GROUP BY 1, 2, 3, 4
ORDER BY total DESC;
```

### Q3: Replies Inválidos (Bug/Race)

```sql
SELECT
    ts,
    cliente_id,
    conversation_id,
    event_props->>'inbound_interaction_id' as inbound_id,
    event_props->>'block_reason' as razao
FROM business_events
WHERE event_type IN ('outbound_blocked', 'outbound_bypass')
  AND event_props->>'method' = 'reply'
  AND (
      event_props->>'inbound_interaction_id' IS NULL
      OR conversation_id IS NULL
  )
  AND ts >= NOW() - INTERVAL '24 hours'
ORDER BY ts DESC
LIMIT 20;
```

### Q4: Erros de Provider (Estabilidade)

```sql
SELECT
    DATE_TRUNC('hour', ts) as hora,
    event_props->>'block_reason' as razao,
    COUNT(*) as total
FROM business_events
WHERE event_type = 'outbound_blocked'
  AND event_props->>'block_reason' IN ('provider_error', 'timeout', 'circuit_open')
  AND ts >= NOW() - INTERVAL '24 hours'
GROUP BY 1, 2
ORDER BY 1 DESC;
```

---

## Contrato do Evento (Inviolável)

### Campos top-level (sempre presentes)
- `event_type`: string
- `ts`: timestamptz ISO
- `cliente_id`: UUID
- `conversation_id`: UUID|null
- `policy_decision_id`: UUID|null
- `event_props`: jsonb

### event_props (sempre presentes)
- `provider`: "evolution"
- `channel`: job|slack|api|whatsapp
- `method`: campaign|followup|reactivation|reply|button|command|manual
- `actor_type`: system|bot|human
- `actor_id`: string|null
- `is_proactive`: bool
- `campaign_id`: string|null
- `inbound_interaction_id`: int|null
- `block_reason`: opted_out|cooling_off|next_allowed_at|contact_cap|safe_mode|campaigns_disabled|...
- `bypassed`: bool
- `bypass_reason`: string|null
- `details`: object (default {})

### Regras de Integridade
1. `bypassed=false` ⇒ `bypass_reason` deve ser null
2. `bypassed=true` ⇒ `actor_type=human`, `channel in (slack,api)`, `bypass_reason` obrigatório
3. `method=reply` ⇒ `conversation_id` e `inbound_interaction_id` obrigatórios
4. Se veio do policy engine, `policy_decision_id` deve estar preenchido
5. `is_proactive=true` ⇒ `method != reply`
6. `details` nunca pode carregar PII (telefone/texto cru)

---

## Referencia de Codigo

- **Guardrails Check:** `app/services/guardrails/check.py` - verificacao de guardrails
- **Guardrails Types:** `app/services/guardrails/types.py` - tipos e estruturas
- **Business Events:** `app/services/business_events/` - emissao de eventos
- **Outbound:** `app/services/outbound.py` - controle de envios

**Event Types relevantes:**
- `OUTBOUND_BLOCKED` - envio bloqueado por guardrail
- `OUTBOUND_BYPASS` - envio permitido por bypass humano
- `OUTBOUND_FALLBACK` - fallback legado usado
- `OUTBOUND_DEDUPED` - envio bloqueado por deduplicacao

---

*Última verificacao: Sprint 57 (10/02/2026) - Queries validadas e funcionais*
