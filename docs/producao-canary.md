# Canary de Produção - Go/No-Go e Critérios de Escala

Sprint 18.1 P0 - Documento de governança para rollout de guardrails.

---

## Resumo Executivo

| Fase | % Canary | Status | Pré-requisitos |
|------|----------|--------|----------------|
| A | 10% | **GO** | Guardrails + CI + monitoramento manual |
| B | 25% | NO-GO | Requer: retry/backoff + toggle campanhas Slack |
| C | 50% | NO-GO | Requer: gaps B + dedupe/outbox |
| D | 100% | NO-GO | Requer: gaps C + playbook de incidentes testado |

---

## Fase A - Canary 10% (ATUAL)

### Status: GO

### Pré-requisitos Atendidos

| Item | Status | Evidência |
|------|--------|-----------|
| Guardrail soberano | ✅ | `check_outbound_guardrails()` é ponto único |
| CI guard (architecture test) | ✅ | `test_architecture_guardrails.py` |
| Sem PII em eventos/logs | ✅ | Regra R6 + telefone truncado |
| Kill switch Julia | ✅ | `pausar_julia` via Slack |
| Circuit breaker | ✅ | 5 falhas → abre, 60s reset |
| Rate limiter | ✅ | 20/hora, 100/dia por telefone |
| Monitoramento | ✅ | Queries SQL + ritual diário |
| RLS habilitado (54 tabelas) | ✅ | Migration `enable_rls_critical_tables` |
| Grants anon/authenticated revogados | ✅ | Migration `revoke_anon_authenticated_grants_p0` |
| search_path hardened | ✅ | 40+ funções com `SET search_path` |

### Restrições Operacionais (OBRIGATÓRIAS)

1. **Volume de campanhas:** Pequeno, janelas curtas (1-2h)
2. **Sem reprocessamento agressivo:** Workers não devem retry sem dedupe
3. **Monitoramento diário:** Executar queries core 1x/dia

### Métricas de Saúde (24h)

```
OUTBOUND_FALLBACK = 0          # Fallback legado não usado
invalid_reply_attempts = 0     # Reply sem inbound_proof
outbound_to_opted_out = 0      # Vazamento de guardrail
provider_error_rate < 1%       # Estabilidade Evolution
```

### Security Hardening (2025-12-29)

**Migrações aplicadas:**

1. **`enable_rls_critical_tables_and_fix_search_path`**
   - RLS habilitado em 13 tabelas críticas que estavam sem
   - `search_path = public, pg_catalog` em 40+ funções
   - Proteção contra SQL injection via schema poisoning

2. **`revoke_anon_authenticated_grants_p0`**
   - Todos os grants de `anon`/`authenticated` revogados
   - Backend usa apenas `service_role` (bypassa RLS by design)
   - Default privileges configurados para novos objetos

**Verificação:**
```sql
-- Tabelas com grant para anon (deve ser 0)
SELECT COUNT(*) FROM information_schema.table_privileges
WHERE grantee = 'anon' AND table_schema = 'public';

-- Funções SECURITY DEFINER expostas (deve ser 0)
SELECT COUNT(*) FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.prosecdef = true
  AND has_function_privilege('anon', p.oid, 'EXECUTE');
```

---

## Fase B - Canary 25%

### Status: NO-GO até gaps fechados

### Gaps Obrigatórios

| Gap | Descrição | Esforço | Prioridade |
|-----|-----------|---------|------------|
| B1 | Toggle campanhas via Slack | 2h | P0 |
| B2 | Retry/backoff Evolution | 3h | P0 |

### Gap B1: Toggle Campanhas via Slack

**Problema:** Só existe `pausar_julia` (para TUDO). Falta controle granular.

**Solução:**
```python
# app/tools/slack/sistema.py

TOOL_TOGGLE_CAMPANHAS = {
    "name": "toggle_campanhas",
    "description": """Ativa ou desativa campanhas.

QUANDO USAR:
- "desativa campanhas"
- "para as campanhas"
- "liga campanhas"

ACAO CRITICA: Peca confirmacao.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "enum": ["on", "off", "status"]
            }
        },
        "required": ["acao"]
    }
}

async def handle_toggle_campanhas(params: dict, user_id: str) -> dict:
    acao = params.get("acao", "status")

    if acao == "status":
        flags = await get_campaigns_flags()
        return {"success": True, "enabled": flags.enabled}

    enabled = acao == "on"
    await set_flag("campaigns", {"enabled": enabled}, updated_by=user_id)

    # Log estruturado para auditoria
    logger.info(
        f"Campanhas {'ativadas' if enabled else 'desativadas'} por {user_id}",
        extra={"event": "campaigns_toggled", "enabled": enabled, "actor": user_id}
    )

    return {"success": True, "enabled": enabled}
```

### Gap B2: Retry/Backoff Evolution

**Problema:** Falha → circuit breaker abre. Sem retry para erros transitórios.

**Solução:**
```python
# app/services/whatsapp.py

import asyncio
import random

RETRY_CONFIG = {
    "max_attempts": 3,
    "delays": [0.3, 1.0, 3.0],  # Exponencial
    "jitter": 0.2,              # ±20%
    "retryable_codes": {429, 500, 502, 503, 504},
}

async def _fazer_request_com_retry(self, method: str, url: str, payload: dict = None) -> dict:
    """Request com retry antes de contar falha no circuit breaker."""
    last_error = None

    for attempt in range(RETRY_CONFIG["max_attempts"]):
        try:
            return await self._fazer_request_interno(method, url, payload)
        except httpx.HTTPStatusError as e:
            if e.response.status_code not in RETRY_CONFIG["retryable_codes"]:
                raise  # 4xx (exceto 429) não faz retry
            last_error = e
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_error = e

        if attempt < RETRY_CONFIG["max_attempts"] - 1:
            delay = RETRY_CONFIG["delays"][attempt]
            jitter = delay * RETRY_CONFIG["jitter"] * (2 * random.random() - 1)
            await asyncio.sleep(delay + jitter)
            logger.warning(f"Retry {attempt + 1}/{RETRY_CONFIG['max_attempts']}: {last_error}")

    raise last_error  # Último erro vai pro circuit breaker
```

### Critério de GO para 25%

- [ ] Gap B1 implementado e testado
- [ ] Gap B2 implementado e testado
- [ ] 24h estáveis em 10% após implementação
- [ ] Métricas de saúde OK

---

## Fase C - Canary 50%

### Status: NO-GO até gaps fechados

### Gaps Obrigatórios

| Gap | Descrição | Esforço | Prioridade |
|-----|-----------|---------|------------|
| C1 | Dedupe/Outbox interno | 4h | P0 |

### Gap C1: Dedupe via Outbox

**Problema:** Sem idempotency key do Evolution, timeout + retry = duplicata.

**Solução: Outbox Pattern**

```sql
-- Migration: create_outbound_messages_outbox
CREATE TABLE outbound_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dedupe_key TEXT UNIQUE NOT NULL,  -- Hash único
    cliente_id UUID NOT NULL,
    conversation_id UUID,
    method TEXT NOT NULL,             -- campaign, followup, reply, etc
    template_ref TEXT,                -- ID do template/vaga
    status TEXT NOT NULL DEFAULT 'queued',  -- queued → sending → sent → failed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    error TEXT,

    CONSTRAINT valid_status CHECK (status IN ('queued', 'sending', 'sent', 'failed'))
);

CREATE INDEX idx_outbound_messages_dedupe ON outbound_messages(dedupe_key);
CREATE INDEX idx_outbound_messages_status ON outbound_messages(status) WHERE status IN ('queued', 'sending');
```

```python
# app/services/outbound_dedup.py

import hashlib
from datetime import datetime, timezone

def gerar_dedupe_key(
    cliente_id: str,
    method: str,
    template_ref: str = None,
    window_minutes: int = 60
) -> str:
    """
    Gera chave de deduplicação.

    Janela temporal evita retry legítimo após muito tempo.
    """
    now = datetime.now(timezone.utc)
    window_bucket = now.strftime('%Y%m%d%H')  # Bucket por hora

    raw = f"{cliente_id}:{method}:{template_ref or 'none'}:{window_bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def pode_enviar_com_dedupe(
    cliente_id: str,
    method: str,
    template_ref: str = None
) -> tuple[bool, str | None]:
    """
    Verifica se pode enviar (não é duplicata).

    Returns:
        (pode_enviar, motivo_se_bloqueado)
    """
    dedupe_key = gerar_dedupe_key(cliente_id, method, template_ref)

    try:
        # Tentar inserir - falha se duplicata
        supabase.table("outbound_messages").insert({
            "dedupe_key": dedupe_key,
            "cliente_id": cliente_id,
            "method": method,
            "template_ref": template_ref,
            "status": "queued"
        }).execute()
        return True, None
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return False, "duplicata"
        raise


async def marcar_enviado(dedupe_key: str) -> None:
    """Marca como enviado com sucesso."""
    supabase.table("outbound_messages").update({
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat()
    }).eq("dedupe_key", dedupe_key).execute()


async def marcar_falha(dedupe_key: str, error: str) -> None:
    """Marca como falha (permite retry futuro se necessário)."""
    supabase.table("outbound_messages").update({
        "status": "failed",
        "error": error
    }).eq("dedupe_key", dedupe_key).execute()
```

### Critério de GO para 50%

- [ ] Gap C1 implementado e testado
- [ ] 48h estáveis em 25%
- [ ] Zero duplicatas detectadas
- [ ] Métricas de saúde OK

---

## Fase D - Canary 100%

### Status: NO-GO até critérios atendidos

### Critérios Obrigatórios

| Critério | Descrição |
|----------|-----------|
| D1 | Dedupe/Outbox funcionando (Gap C1) |
| D2 | Playbook de incidentes testado |
| D3 | 7 dias estáveis em 50% |

### D2: Playbook de Incidentes

Antes de 100%, testar pelo menos 1x:

1. **Kill switch Julia:** `pausar_julia` → verificar que para → `retomar_julia`
2. **Kill switch campanhas:** `toggle_campanhas off` → verificar → `on`
3. **Rollback canary:** Reduzir de 50% → 10% e verificar comportamento
4. **Bypass manual:** Testar bypass via Slack com `bypass_reason`

### Critério de GO para 100%

- [ ] Playbook testado e documentado
- [ ] 7 dias estáveis em 50%
- [ ] Métricas de saúde OK por 7 dias consecutivos
- [ ] Zero incidentes P0/P1 na semana

---

## SLOs para Decisão de Escala

### Métricas Core (verificar diariamente)

| Métrica | Threshold | Ação se violado |
|---------|-----------|-----------------|
| `OUTBOUND_FALLBACK` | = 0 | Investigar call-site, não escalar |
| `invalid_reply` (reply sem proof) | = 0 | Investigar race condition |
| `outbound_to_opted_out` | = 0 | Bug crítico, rollback |
| `provider_error_rate` | < 1% | Não escalar até estabilizar |
| `duplicatas_detectadas` | = 0 | Não escalar até dedupe |

### Janela de Estabilidade

| Transição | Janela Mínima |
|-----------|---------------|
| 10% → 25% | 24h estáveis |
| 25% → 50% | 48h estáveis |
| 50% → 100% | 7 dias estáveis |

### Definição de "Estável"

- Todas as métricas core dentro do threshold
- Zero alertas P0/P1
- Kill switches funcionando (teste manual OK)

---

## Painel Diário - 4 Queries Core

### Ritual: 10 minutos/dia

1. Abrir Supabase SQL Editor
2. Executar as 4 queries abaixo
3. Verificar thresholds
4. Postar resumo no Slack (manual ou automatizado)

### Query 1: Volume por Tipo de Evento (24h)

```sql
-- Q1: Sanity check - volume de eventos
SELECT
    event_type,
    COUNT(*) as total,
    COUNT(DISTINCT cliente_id) as clientes_unicos
FROM business_events
WHERE ts >= NOW() - INTERVAL '24 hours'
GROUP BY event_type
ORDER BY total DESC;
```

**O que olhar:**
- `outbound_blocked` e `outbound_bypass` devem ter proporção saudável
- `outbound_fallback` deve ser 0
- Volume geral condizente com operação

### Query 2: Guardrail Blocked/Bypass por Razão

```sql
-- Q2: Risco - motivos de bloqueio e bypass
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

**O que olhar:**
- `opted_out` deve ser a razão mais comum de bloqueio
- Bypass deve ter `bypass_reason` preenchido
- Nenhum canal/método inesperado

### Query 3: Replies Inválidos (Bug/Race)

```sql
-- Q3: Bug detection - replies sem prova de inbound
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

**O que olhar:**
- Resultado deve ser VAZIO
- Se houver linhas: race condition ou bug no pipeline

### Query 4: Erros de Provider (Estabilidade)

```sql
-- Q4: Estabilidade - falhas de envio
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

**O que olhar:**
- Idealmente vazio ou muito baixo
- Se > 1% do volume total: investigar Evolution/rede

### Query Bônus: Fallback Legado (deve ser ZERO)

```sql
-- Q5: Migração - fallbacks legados usados
SELECT
    ts,
    event_props->>'function' as funcao,
    event_props->>'telefone_prefix' as telefone_prefix
FROM business_events
WHERE event_type = 'outbound_fallback'
  AND ts >= NOW() - INTERVAL '24 hours'
ORDER BY ts DESC;
```

**O que olhar:**
- DEVE ser vazio
- Se houver linhas: call-site não migrado

---

## Automação Opcional: Job de Health Check

```python
# app/workers/daily_health.py

async def check_daily_health() -> dict:
    """
    Executa queries core e retorna status.
    Pode ser chamado por job diário que posta no Slack.
    """
    results = {}

    # Q1: Volume
    r1 = supabase.rpc("daily_health_volume").execute()
    results["volume"] = r1.data

    # Q5: Fallback (crítico)
    r5 = supabase.table("business_events").select("*").eq(
        "event_type", "outbound_fallback"
    ).gte("ts", (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()).execute()

    results["fallback_count"] = len(r5.data or [])
    results["status"] = "OK" if results["fallback_count"] == 0 else "ALERT"

    return results
```

---

## Ponte Externa (Sprint 21)

Sistema de canary separado para a ponte médico-divulgador.

### Status: PRONTO (flag desativada)

| Controle | Status | Descrição |
|----------|--------|-----------|
| Canary Flag | ✅ | `external_handoff.enabled` + `canary_pct` |
| Kill Switch | ✅ | `toggle_ponte_externa` via Slack |
| Rate Limit | ✅ | 30/min + 200/h por IP em `/handoff/confirm` |
| Guardrails | ✅ | Opt-out + horário comercial (08-20h seg-sex) |
| Unique Constraint | ✅ | Apenas 1 handoff ativo por vaga |
| Playbook | ✅ | `docs/playbook-handoff.md` |

### Ativação Gradual

```bash
# Via Slack
toggle_ponte_externa status      # Ver estado atual
toggle_ponte_externa on 10       # 10% dos clientes
toggle_ponte_externa on 50       # 50% dos clientes
toggle_ponte_externa on          # 100% (produção)
toggle_ponte_externa off         # Kill switch
```

### Canary Logic

```python
# Hash determinístico: mesmo cliente sempre no mesmo bucket
hash_bytes = hashlib.md5(cliente_id.encode()).digest()
cliente_hash = int.from_bytes(hash_bytes[:4], "big") % 100
return cliente_hash < canary_pct
```

---

## Histórico de Mudanças

| Data | Canary | Mudança | Responsável |
|------|--------|---------|-------------|
| 2025-12-29 | 10% | GO inicial - guardrails provados | - |
| 2025-12-29 | 10% | Security hardening: RLS em 54 tabelas | - |
| 2025-12-29 | 10% | Security hardening: Grants revogados de anon/authenticated | - |
| 2025-12-29 | 10% | Security hardening: search_path em 40+ funções | - |
| 2025-12-29 | - | Sprint 21: Ponte Externa pronta (flag desativada) | - |
| - | 25% | Pendente: B1 + B2 | - |
| - | 50% | Pendente: C1 | - |
| - | 100% | Pendente: D1 + D2 + D3 | - |

---

## Contatos de Escalação

| Situação | Ação |
|----------|------|
| Vazamento opted_out | Rollback imediato + `pausar_julia` |
| Duplicatas em massa | `pausar_julia` + investigar |
| Circuit breaker aberto | Verificar Evolution API |
| Dúvida operacional | Consultar este documento |
