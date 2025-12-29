# Sprint 24: Controle e Mensuração de Campanhas

**Início:** 30/12/2024
**Duração estimada:** 3 dias
**Objetivo:** Transformar campanhas de "mailing list cru" em sistema mensurável com funil honesto.

---

## Contexto e Motivação

### Problema atual

A Júlia hoje "escolhe" médicos como um mailing list cru:
1. `segmentacao.buscar_segmento()` faz `SELECT * FROM clientes`
2. Aplica filtros simples (especialidade, região, tags)
3. Exclui `status != 'optout'`
4. Retorna até 10k "na ordem do banco"

**Consequências:**
- Campanha "acha" que está trabalhando 10k médicos
- Boa parte vira `blocked` / `deduped` nos guardrails
- Funil parece ruim quando o target set era inelegível desde o início
- Não há como saber "campanha foi ruim ou target set era lixo?"

### Solução

1. **Seleção qualificada:** RPC que já filtra por elegibilidade operacional
2. **Dedupe de intenção:** Evitar "2 discoveries em 3 dias" mesmo com textos diferentes
3. **Atribuição:** Saber qual campanha/estratégia gerou cada resultado
4. **Cooldown entre campanhas:** Evitar bombardeio por campanhas diferentes

---

## Épicos

| Épico | Descrição | Esforço |
|-------|-----------|---------|
| E01 | RPC `buscar_alvos_campanha` | 1 dia |
| E02 | Intent Fingerprint + `intent_log` | 1 dia |
| E03 | Centralizar finalização + last_touch | 0.5 dia |
| E04 | Guardrail `campaign_cooldown` | 0.5 dia |

**Total: 3 dias**

---

## E01: RPC `buscar_alvos_campanha`

### Objetivo

Criar função no banco que retorna médicos **já filtrados por elegibilidade operacional**, não apenas demográfica.

### Contexto técnico

Hoje `segmentacao.buscar_segmento()` seleciona em `clientes` e deixa guardrails resolverem depois. Isso gera desperdício silencioso e métricas desonestas.

### Critérios de filtro da RPC

| Critério | Descrição | Default |
|----------|-----------|---------|
| `p_dias_sem_contato` | Não tocados nos últimos X dias | 14 |
| `p_excluir_cooling` | Excluir se `next_allowed_at > now()` | true |
| `p_excluir_em_atendimento` | Excluir se `last_inbound_at < 30min` | true |
| `p_contact_cap` | Excluir se `contact_count_7d >= cap` | 5 |
| `p_limite` | Limite de resultados | 1000 |

### Regras de negócio

1. **Tratar doctor_state ausente:** Médico novo (sem `doctor_state`) é elegível
   - `COALESCE(ds.contact_count_7d, 0) < p_contact_cap`

2. **Excluir conversas sob humano:** Não enviar campanha se humano está atendendo
   - `NOT EXISTS (SELECT 1 FROM conversations WHERE controlled_by = 'human')`

3. **Excluir em atendimento ativo:** Não atropelar conversa em andamento
   - `ds.last_inbound_at IS NULL OR ds.last_inbound_at < NOW() - INTERVAL '30 minutes'`

4. **Determinismo:** Ordem fixa para cohort reproduzível
   - `ORDER BY ds.last_outbound_at ASC NULLS FIRST, c.id ASC`

5. **Conversa bot-only NÃO exclui:** Só exclui `controlled_by='human'`

### Entregáveis

| Artefato | Caminho |
|----------|---------|
| Migração SQL | `supabase/migrations/YYYYMMDD_buscar_alvos_campanha.sql` |
| Wrapper Python | `app/services/segmentacao.py` |
| Testes unitários | `tests/unit/test_segmentacao_qualificada.py` |

### Migração SQL

```sql
CREATE OR REPLACE FUNCTION buscar_alvos_campanha(
    p_filtros JSONB DEFAULT '{}',
    p_dias_sem_contato INT DEFAULT 14,
    p_excluir_cooling BOOLEAN DEFAULT TRUE,
    p_excluir_em_atendimento BOOLEAN DEFAULT TRUE,
    p_contact_cap INT DEFAULT 5,
    p_limite INT DEFAULT 1000
)
RETURNS TABLE (
    id UUID,
    nome TEXT,
    telefone TEXT,
    especialidade_nome TEXT,
    regiao TEXT,
    last_outbound_at TIMESTAMPTZ,
    contact_count_7d INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.nome,
        c.telefone,
        c.especialidade_nome,
        c.regiao,
        ds.last_outbound_at,
        COALESCE(ds.contact_count_7d, 0)::INT as contact_count_7d
    FROM clientes c
    LEFT JOIN doctor_state ds ON ds.cliente_id = c.id
    WHERE
        -- Básico: não optout
        c.status != 'optout'

        -- Tratar doctor_state ausente (COALESCE)
        AND COALESCE(ds.contact_count_7d, 0) < p_contact_cap

        -- Não tocados recentemente
        AND (
            ds.last_outbound_at IS NULL
            OR ds.last_outbound_at < NOW() - (p_dias_sem_contato || ' days')::INTERVAL
        )

        -- Excluir cooling_off
        AND (
            NOT p_excluir_cooling
            OR ds.next_allowed_at IS NULL
            OR ds.next_allowed_at < NOW()
        )

        -- Excluir conversas sob humano (NOT EXISTS evita duplicação)
        AND NOT EXISTS (
            SELECT 1 FROM conversations cv
            WHERE cv.cliente_id = c.id
              AND cv.status = 'active'
              AND cv.controlled_by = 'human'
        )

        -- Excluir em atendimento ativo (inbound < 30min)
        AND (
            NOT p_excluir_em_atendimento
            OR ds.last_inbound_at IS NULL
            OR ds.last_inbound_at < NOW() - INTERVAL '30 minutes'
        )

        -- Filtros demográficos dinâmicos
        AND (
            p_filtros->>'especialidade' IS NULL
            OR c.especialidade_nome = p_filtros->>'especialidade'
        )
        AND (
            p_filtros->>'regiao' IS NULL
            OR c.regiao = p_filtros->>'regiao'
        )

    -- Determinismo: tie-breaker por c.id
    ORDER BY ds.last_outbound_at ASC NULLS FIRST, c.id ASC
    LIMIT p_limite;
END;
$$ LANGUAGE plpgsql STABLE;
```

### Definition of Done (DoD)

- [ ] Migração aplicada no banco de staging
- [ ] Função `buscar_alvos_campanha()` em `segmentacao.py` chamando RPC
- [ ] Testes com mock:
  - [ ] Médico sem doctor_state é incluído
  - [ ] Médico com `contact_count_7d >= 5` é excluído
  - [ ] Médico com conversa `controlled_by='human'` é excluído
  - [ ] Médico com `last_inbound_at < 30min` é excluído (se flag ativa)
  - [ ] Ordem é determinística (mesmo resultado em 2 execuções)
- [ ] Rotas de campanha atualizadas para usar nova função
- [ ] Log de "target set qualificado: X médicos elegíveis de Y total"

---

## E02: Intent Fingerprint + `intent_log`

### Objetivo

Criar dedupe semântico por **intenção de mensagem**, não apenas por conteúdo.

### Problema que resolve

Hoje o dedupe é por `content_hash`:
- Campanha A: "Oi, tudo bem? Vi seu perfil..."
- Campanha B: "Dr, tudo certo? Pintou uma oportunidade..."

Textos diferentes → passa no dedupe → médico recebe 2 abordagens similares.

### Solução

Fingerprint determinístico por `intent_type`:
```
sha256(cliente_id + intent_type + reference_id + day_bucket)
```

### Tipos de intent padronizados

| Intent Type | reference_id | Janela | Semântica |
|-------------|--------------|--------|-----------|
| `discovery_first_touch` | `campaign_id` | 7 dias | 1 discovery por campanha por médico |
| `discovery_followup` | `campaign_id` | 3 dias | 1 followup de discovery por campanha |
| `offer_active` | `vaga_id` | 1 dia | 1 oferta por vaga por médico |
| `offer_reminder` | `vaga_id` | 2 dias | 1 reminder por vaga |
| `reactivation_nudge` | `None` | 7 dias | 1 reativação global por janela |
| `reactivation_value_prop` | `None` | 7 dias | 1 value prop global |
| `followup_silence` | `conversation_id` | 3 dias | 1 por conversa |
| `followup_pending_docs` | `conversation_id` | 2 dias | 1 por conversa |
| `shift_reminder` | `vaga_id` | 1 dia | 1 reminder por plantão |
| `handoff_confirmation` | `vaga_id` | 1 dia | 1 confirmação por plantão |

### Entregáveis

| Artefato | Caminho |
|----------|---------|
| Migração SQL (tabela + RPC) | `supabase/migrations/YYYYMMDD_intent_log.sql` |
| Serviço Python | `app/services/intent_dedupe.py` |
| Enum IntentType | `app/services/intent_dedupe.py` |
| Testes unitários | `tests/unit/test_intent_dedupe.py` |

### Migração SQL

```sql
-- Tabela de log de intents
CREATE TABLE intent_log (
    fingerprint TEXT PRIMARY KEY,
    cliente_id UUID NOT NULL REFERENCES clientes(id),
    intent_type TEXT NOT NULL,
    reference_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days'
);

CREATE INDEX idx_intent_log_cliente ON intent_log(cliente_id);
CREATE INDEX idx_intent_log_expires ON intent_log(expires_at);
CREATE INDEX idx_intent_log_type ON intent_log(intent_type);

-- RPC para insert idempotente (sem exceção)
CREATE OR REPLACE FUNCTION inserir_intent_se_novo(
    p_fingerprint TEXT,
    p_cliente_id UUID,
    p_intent_type TEXT,
    p_reference_id UUID DEFAULT NULL,
    p_expires_at TIMESTAMPTZ DEFAULT NULL
)
RETURNS TABLE (fingerprint TEXT, inserted BOOLEAN) AS $$
DECLARE
    v_inserted BOOLEAN := FALSE;
BEGIN
    INSERT INTO intent_log (fingerprint, cliente_id, intent_type, reference_id, expires_at)
    VALUES (
        p_fingerprint,
        p_cliente_id,
        p_intent_type,
        p_reference_id,
        COALESCE(p_expires_at, NOW() + INTERVAL '30 days')
    )
    ON CONFLICT (fingerprint) DO NOTHING;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    RETURN QUERY SELECT p_fingerprint, v_inserted > 0;
END;
$$ LANGUAGE plpgsql;
```

### Serviço Python

```python
# app/services/intent_dedupe.py

from enum import Enum
from datetime import datetime, timedelta
from typing import Tuple, Optional
import hashlib

from app.services.supabase import supabase


class IntentType(str, Enum):
    """Tipos de intenção padronizados."""
    DISCOVERY_FIRST = "discovery_first_touch"
    DISCOVERY_FOLLOWUP = "discovery_followup"
    OFFER_ACTIVE = "offer_active"
    OFFER_REMINDER = "offer_reminder"
    REACTIVATION_NUDGE = "reactivation_nudge"
    REACTIVATION_VALUE = "reactivation_value_prop"
    FOLLOWUP_SILENCE = "followup_silence"
    FOLLOWUP_DOCS = "followup_pending_docs"
    SHIFT_REMINDER = "shift_reminder"
    HANDOFF_CONFIRM = "handoff_confirmation"


# Janelas por intent (dias)
INTENT_WINDOWS: dict[str, int] = {
    "discovery_first_touch": 7,
    "discovery_followup": 3,
    "offer_active": 1,
    "offer_reminder": 2,
    "reactivation_nudge": 7,
    "reactivation_value_prop": 7,
    "followup_silence": 3,
    "followup_pending_docs": 2,
    "shift_reminder": 1,
    "handoff_confirmation": 1,
}
DEFAULT_WINDOW = 3

# reference_id por intent
INTENT_REFERENCE_FIELD: dict[str, Optional[str]] = {
    "discovery_first_touch": "campaign_id",
    "discovery_followup": "campaign_id",
    "offer_active": "vaga_id",
    "offer_reminder": "vaga_id",
    "reactivation_nudge": None,
    "reactivation_value_prop": None,
    "followup_silence": "conversation_id",
    "followup_pending_docs": "conversation_id",
    "shift_reminder": "vaga_id",
    "handoff_confirmation": "vaga_id",
}


def gerar_intent_fingerprint(
    cliente_id: str,
    intent_type: str,
    reference_id: Optional[str] = None,
    window_days: Optional[int] = None,
) -> str:
    """Fingerprint determinístico por intenção."""
    intent_str = str(intent_type)
    if window_days is None:
        window_days = INTENT_WINDOWS.get(intent_str, DEFAULT_WINDOW)

    day_bucket = datetime.utcnow().toordinal() // window_days

    raw = f"{cliente_id}:{intent_str}:{reference_id or 'none'}:{day_bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def verificar_intent(
    cliente_id: str,
    intent_type: str,
    reference_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Verifica e reserva intent para esse médico.

    Returns:
        (pode_enviar, fingerprint, motivo_se_bloqueado)
    """
    intent_str = str(intent_type)
    window_days = INTENT_WINDOWS.get(intent_str, DEFAULT_WINDOW)
    fingerprint = gerar_intent_fingerprint(
        cliente_id, intent_str, reference_id, window_days
    )

    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()

    response = supabase.rpc("inserir_intent_se_novo", {
        "p_fingerprint": fingerprint,
        "p_cliente_id": cliente_id,
        "p_intent_type": intent_str,
        "p_reference_id": reference_id,
        "p_expires_at": expires_at,
    }).execute()

    if response.data and len(response.data) > 0:
        inserted = response.data[0].get("inserted", False)
        if inserted:
            return (True, fingerprint, None)

    return (False, fingerprint, f"intent_duplicate:{intent_str}")


def obter_reference_id(intent_type: str, ctx) -> Optional[str]:
    """Obtém reference_id correto para o intent_type."""
    field = INTENT_REFERENCE_FIELD.get(str(intent_type))
    if field is None:
        return None
    return getattr(ctx, field, None) or ctx.metadata.get(field)
```

### Definition of Done (DoD)

- [ ] Migração aplicada no banco de staging
- [ ] `intent_log` criada com índices
- [ ] RPC `inserir_intent_se_novo` funcionando (sem exceção para duplicata)
- [ ] Serviço `intent_dedupe.py` implementado
- [ ] Testes:
  - [ ] Primeira inserção retorna `(True, fingerprint, None)`
  - [ ] Segunda inserção (mesmo fingerprint) retorna `(False, fingerprint, "intent_duplicate:...")`
  - [ ] Janelas diferentes geram fingerprints diferentes
  - [ ] reference_id diferente gera fingerprint diferente
- [ ] Integração com `send_outbound_message()` (E03)
- [ ] Evento `OUTBOUND_DEDUPED` com `reason_code="intent_duplicate"`
- [ ] Job de cleanup (DELETE WHERE expires_at < NOW()) configurado no scheduler

---

## E03: Centralizar finalização + last_touch

### Objetivo

1. Garantir que TODO envio (sucesso, blocked, deduped, falha) passe por `_finalizar_envio()`
2. Atualizar `last_touch_*` no `doctor_state` quando outcome é conhecido
3. Padronizar metadata de envio

### Problema que resolve

Hoje o outcome é decidido em 3+ pontos diferentes de `send_outbound_message()`, com returns espalhados. Fácil esquecer de atualizar estado ou emitir evento.

### Regras de negócio

1. **Usar try/finally:** Garantir que `_finalizar_envio` sempre execute
2. **Idempotência:** Cache com TTL 1h para evitar duplicação por reprocessamento
3. **Quando atualizar last_touch:**
   - ✅ SENT, DEDUPED, FAILED_PROVIDER, BLOCKED (exceto optout)
   - ❌ BLOCKED_OPTED_OUT (não sujar métricas)
   - ❌ Se `controlled_by='human'`

### Campos a adicionar em doctor_state

```sql
ALTER TABLE doctor_state
ADD COLUMN IF NOT EXISTS last_touch_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_touch_campaign_id UUID,
ADD COLUMN IF NOT EXISTS last_touch_method TEXT,
ADD COLUMN IF NOT EXISTS last_touch_outcome TEXT;

CREATE INDEX IF NOT EXISTS idx_doctor_state_last_touch
ON doctor_state(last_touch_at, last_touch_campaign_id);
```

### Metadata padrão de envio

```python
def preparar_metadata_envio(
    strategy_type: str,
    intent_type: str,
    campaign_id: str = None,
    campaign_run_id: str = None,  # ID da execução do batch
    template_version: str = None,
    detected_profile: str = None,
    detected_objection: str = None,
) -> dict:
    return {
        # Estratégia
        "strategy_type": strategy_type,
        "strategy_run_id": str(uuid.uuid4()),  # Por mensagem
        "campaign_run_id": campaign_run_id,     # Por batch

        # Intent
        "intent_type": intent_type,
        "intent_fingerprint": None,  # Preenchido depois

        # Atribuição
        "campaign_id": campaign_id,
        "template_version": template_version or "v1",

        # Detecção (do RAG)
        "detected_profile": detected_profile,
        "detected_objection": detected_objection,
    }
```

### Refatoração de send_outbound_message

```python
async def send_outbound_message(...) -> OutboundResult:
    result: OutboundResult = None

    try:
        # 1. Guardrail
        guardrail_result = await check_outbound_guardrails(ctx)
        if guardrail_result.is_blocked:
            result = OutboundResult(
                success=False,
                outcome=_map_guardrail_to_outcome(guardrail_result),
                blocked=True,
                block_reason=guardrail_result.reason_code,
            )
            return result

        # 2. Intent dedupe (NOVO)
        if ctx.intent_type:
            reference_id = obter_reference_id(ctx.intent_type, ctx)
            intent_ok, intent_fp, intent_reason = await verificar_intent(
                ctx.cliente_id, ctx.intent_type, reference_id
            )
            ctx.metadata["intent_fingerprint"] = intent_fp

            if not intent_ok:
                result = OutboundResult(
                    success=False,
                    outcome=SendOutcome.DEDUPED_INTENT,
                    deduped=True,
                    block_reason=intent_reason,
                )
                return result

        # 3. Content dedupe
        content_hash = _gerar_content_hash(texto)
        pode_enviar, dedupe_key, motivo = await verificar_e_reservar(...)

        if not pode_enviar:
            result = OutboundResult(
                success=False,
                outcome=SendOutcome.DEDUPED_CONTENT,
                deduped=True,
                dedupe_key=dedupe_key,
                block_reason=motivo,
            )
            return result

        # 4. Envio
        try:
            response = await evolution.enviar_mensagem(...)
            await marcar_enviado(dedupe_key)
            result = OutboundResult(
                success=True,
                outcome=SendOutcome.SENT,
                dedupe_key=dedupe_key,
                provider_message_id=response.get("key", {}).get("id"),
            )
            return result
        except Exception as e:
            await marcar_falha(dedupe_key, str(e)[:200])
            result = OutboundResult(
                success=False,
                outcome=SendOutcome.FAILED_PROVIDER,
                error=str(e),
            )
            return result

    except Exception as e:
        logger.exception(f"Erro inesperado em send_outbound_message: {e}")
        result = OutboundResult(
            success=False,
            outcome=SendOutcome.FAILED_UNKNOWN,
            error=str(e),
        )
        return result

    finally:
        # SEMPRE executa
        if result and ctx.cliente_id:
            await _finalizar_envio(ctx, result)
```

### Função _finalizar_envio

```python
async def _finalizar_envio(ctx: OutboundContext, result: OutboundResult) -> None:
    """
    Ponto único de finalização com side-effects.

    - Atualiza last_touch no doctor_state
    - Emite eventos de auditoria
    - Idempotente via cache
    """
    # Idempotência
    cache_key = f"finalized:{result.dedupe_key or ctx.metadata.get('intent_fingerprint', '')}"
    if cache_key != "finalized:":
        already = await cache_get(cache_key)
        if already:
            logger.debug(f"Já finalizado: {cache_key}")
            return
        await cache_set(cache_key, "1", ttl=3600)

    # Não atualizar last_touch para optout
    if result.outcome == SendOutcome.BLOCKED_OPTED_OUT:
        return

    # Atualizar doctor_state
    updates = {
        "last_touch_at": datetime.utcnow().isoformat(),
        "last_touch_method": ctx.method.value if ctx.method else None,
        "last_touch_outcome": result.outcome.value if result.outcome else None,
    }

    if ctx.campaign_id:
        updates["last_touch_campaign_id"] = ctx.campaign_id

    try:
        await save_doctor_state_updates(ctx.cliente_id, updates)
    except Exception as e:
        logger.warning(f"Erro ao atualizar last_touch (não crítico): {e}")

    # Emitir evento para dedupe de intent
    if result.outcome == SendOutcome.DEDUPED_INTENT:
        asyncio.create_task(
            emit_event(BusinessEvent(
                event_type=EventType.OUTBOUND_DEDUPED,
                source=EventSource.BACKEND,
                cliente_id=ctx.cliente_id,
                event_props={
                    "reason": "intent_duplicate",
                    "intent_type": ctx.metadata.get("intent_type"),
                    "fingerprint": ctx.metadata.get("intent_fingerprint"),
                },
            ))
        )
```

### Atualização do enum SendOutcome

```python
class SendOutcome(str, Enum):
    # Sucesso
    SENT = "SENT"

    # Deduplicação (separados)
    DEDUPED_INTENT = "DEDUPED_INTENT"    # Por intenção
    DEDUPED_CONTENT = "DEDUPED_CONTENT"  # Por content_hash

    # Bloqueios por guardrail
    BLOCKED_OPTED_OUT = "BLOCKED_OPTED_OUT"
    BLOCKED_COOLING_OFF = "BLOCKED_COOLING_OFF"
    BLOCKED_NEXT_ALLOWED = "BLOCKED_NEXT_ALLOWED"
    BLOCKED_CONTACT_CAP = "BLOCKED_CONTACT_CAP"
    BLOCKED_CAMPAIGNS_DISABLED = "BLOCKED_CAMPAIGNS_DISABLED"
    BLOCKED_SAFE_MODE = "BLOCKED_SAFE_MODE"
    BLOCKED_CAMPAIGN_COOLDOWN = "BLOCKED_CAMPAIGN_COOLDOWN"

    # Erros técnicos
    FAILED_PROVIDER = "FAILED_PROVIDER"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_RATE_LIMIT = "FAILED_RATE_LIMIT"
    FAILED_CIRCUIT_OPEN = "FAILED_CIRCUIT_OPEN"
    FAILED_UNKNOWN = "FAILED_UNKNOWN"

    # Override manual
    BYPASS = "BYPASS"
```

### Entregáveis

| Artefato | Caminho |
|----------|---------|
| Migração SQL | `supabase/migrations/YYYYMMDD_last_touch_fields.sql` |
| Refatoração outbound | `app/services/outbound.py` |
| SendOutcome atualizado | `app/services/guardrails/types.py` |
| Testes | `tests/unit/test_outbound_finalization.py` |

### Definition of Done (DoD)

- [ ] Migração aplicada (campos last_touch_*)
- [ ] `send_outbound_message` refatorado com try/finally
- [ ] `_finalizar_envio` implementado com idempotência
- [ ] SendOutcome atualizado (DEDUPED_INTENT, DEDUPED_CONTENT separados)
- [ ] Testes:
  - [ ] Todo path (blocked, deduped, sent, failed) chama `_finalizar_envio`
  - [ ] Reprocessamento não duplica last_touch (idempotência)
  - [ ] BLOCKED_OPTED_OUT não atualiza last_touch
- [ ] Evento OUTBOUND_DEDUPED emitido para intent_duplicate
- [ ] `preparar_metadata_envio()` disponível para campanhas

---

## E04: Guardrail `campaign_cooldown`

### Objetivo

Bloquear campanha se médico foi tocado por **outra campanha** nos últimos 3 dias.

### Regras de negócio

| Regra | Descrição |
|-------|-----------|
| Cooldown | 3 dias entre campanhas diferentes |
| Mesma campanha | Isenta (permite followup) |
| Reply/Followup | Isentos (não são CAMPAIGN) |
| Bypass humano | Permitido via Slack |

### Implementação

```python
# app/services/guardrails/check.py

CAMPAIGN_COOLDOWN_DAYS = 3

async def _check_campaign_cooldown(
    ctx: OutboundContext,
    state: DoctorState
) -> Optional[GuardrailResult]:
    """
    R4: Cooldown entre campanhas diferentes.

    - Só aplica para method=CAMPAIGN
    - Isenta mesma campanha (followup)
    - Bypass humano permitido
    """
    # Só aplica para CAMPAIGN
    if ctx.method != OutboundMethod.CAMPAIGN:
        return None

    # Precisa ter last_touch de campanha
    if not state or not state.last_touch_method:
        return None

    if state.last_touch_method != "campaign":
        return None

    if not state.last_touch_at:
        return None

    # Calcular dias desde último touch
    last_touch = state.last_touch_at
    if isinstance(last_touch, str):
        last_touch = datetime.fromisoformat(last_touch.replace("Z", "+00:00"))

    if last_touch.tzinfo is None:
        last_touch = last_touch.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    days_since = (now - last_touch).days

    # Dentro do cooldown?
    if days_since >= CAMPAIGN_COOLDOWN_DAYS:
        return None  # Cooldown expirou, pode enviar

    # Mesma campanha? (followup isento)
    same_campaign = (
        ctx.campaign_id
        and state.last_touch_campaign_id
        and str(ctx.campaign_id) == str(state.last_touch_campaign_id)
    )

    if same_campaign:
        return None  # Mesma campanha, isento

    # Verificar bypass humano
    if _is_human_slack_bypass(ctx):
        return GuardrailResult(
            decision=GuardrailDecision.ALLOW,
            reason_code="campaign_cooldown",
            human_bypass=True,
            details={
                "days_since": days_since,
                "required": CAMPAIGN_COOLDOWN_DAYS,
            }
        )

    # BLOCK
    return GuardrailResult(
        decision=GuardrailDecision.BLOCK,
        reason_code="campaign_cooldown",
        details={
            "days_since": days_since,
            "required": CAMPAIGN_COOLDOWN_DAYS,
            "last_campaign_id": str(state.last_touch_campaign_id) if state.last_touch_campaign_id else None,
        }
    )
```

### Integração em check_outbound_guardrails

```python
async def check_outbound_guardrails(ctx: OutboundContext) -> GuardrailResult:
    state = await load_doctor_state(ctx.cliente_id)

    # R0: opted_out (terminal)
    # R1: controlled_by_human
    # R2: next_allowed_at
    # R3: contact_cap_7d

    # R4: campaign_cooldown (NOVO)
    cooldown_result = await _check_campaign_cooldown(ctx, state)
    if cooldown_result and cooldown_result.is_blocked:
        await _emit_guardrail_event(ctx, cooldown_result, "outbound_blocked")
        return cooldown_result

    # ... resto
```

### Entregáveis

| Artefato | Caminho |
|----------|---------|
| Guardrail R4 | `app/services/guardrails/check.py` |
| SendOutcome | `BLOCKED_CAMPAIGN_COOLDOWN` (já existe) |
| Testes | `tests/unit/test_guardrail_campaign_cooldown.py` |

### Definition of Done (DoD)

- [ ] Guardrail `_check_campaign_cooldown` implementado
- [ ] Integrado em `check_outbound_guardrails`
- [ ] Testes:
  - [ ] Campanha B bloqueada se campanha A tocou há 2 dias
  - [ ] Campanha A (followup) não bloqueada por ela mesma
  - [ ] Reply não afetado por cooldown
  - [ ] Cooldown expirado (>= 3 dias) permite envio
  - [ ] Bypass humano funciona
- [ ] Evento `OUTBOUND_BLOCKED` com `reason_code="campaign_cooldown"`
- [ ] Log claro: "BLOCK campaign_cooldown: {cliente} (2d < 3d)"

---

## Checklist de Integração Final

Após todos os épicos implementados:

- [ ] E01 integrado nas rotas de campanha (`/api/campanhas`)
- [ ] E02 chamado em `send_outbound_message` antes do content dedupe
- [ ] E03 try/finally funcionando em todos os paths
- [ ] E04 integrado no pipeline de guardrails
- [ ] Métricas disponíveis:
  - [ ] % de target set elegível vs total
  - [ ] % de envios por outcome (sent/deduped_intent/deduped_content/blocked_*)
  - [ ] Conversão por campanha (first_touch → reply)
- [ ] Queries de análise funcionando:
  ```sql
  -- Funil honesto
  SELECT
      campaign_id,
      COUNT(*) as targeted,
      SUM(CASE WHEN outcome = 'SENT' THEN 1 ELSE 0 END) as sent,
      SUM(CASE WHEN outcome LIKE 'DEDUPED%' THEN 1 ELSE 0 END) as deduped,
      SUM(CASE WHEN outcome LIKE 'BLOCKED%' THEN 1 ELSE 0 END) as blocked
  FROM fila_mensagens
  GROUP BY campaign_id;
  ```

---

## Dependências entre épicos

```
E01 (RPC buscar_alvos)
    └─ independente

E02 (intent_log)
    └─ independente

E03 (centralizar finalização)
    ├─ depende de E02 (integrar verificar_intent)
    └─ adiciona campos last_touch_*

E04 (campaign_cooldown)
    └─ depende de E03 (usa last_touch_*)
```

**Ordem de implementação:**
1. E01 e E02 (paralelo)
2. E03 (após E02)
3. E04 (após E03)

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| RPC lenta em produção | Média | Alto | Testar com volume real em staging; adicionar EXPLAIN ANALYZE |
| intent_log crescer muito | Baixa | Médio | Job de cleanup diário; TTL 30 dias |
| Reprocessamento duplicar last_touch | Média | Médio | Cache de idempotência com TTL 1h |
| Cooldown muito restritivo | Baixa | Médio | Bypass humano disponível; parametrizável |

---

## Critérios de Aceite da Sprint

A Sprint 24 está completa quando:

1. **Funil honesto:** Query de target set retorna apenas médicos que realmente podem receber mensagem
2. **Sem spam semântico:** Mesmo médico não recebe 2 discoveries em 7 dias
3. **Atribuição funciona:** Sabe-se qual campanha/estratégia gerou cada outcome
4. **Cooldown protege:** Campanhas diferentes respeitam intervalo de 3 dias
5. **Métricas confiáveis:** Dashboard mostra breakdown real de sent/deduped/blocked
