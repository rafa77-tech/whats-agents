# E04: Guardrail campaign_cooldown

**Status:** Pendente
**Estimativa:** 0.5 dia
**Dependências:** E03 (last_touch_* fields)

---

## Objetivo

Bloquear campanha se médico foi tocado por **outra campanha** nos últimos 3 dias.

## Problema

```
Hoje:
  Campanha A toca médico segunda-feira
  Campanha B toca mesmo médico terça-feira
  Médico recebe 2 abordagens diferentes em 2 dias
  Parece spam, mesmo com textos diferentes

Depois:
  Campanha A toca médico segunda-feira
  Campanha B tenta terça → BLOCKED (campaign_cooldown)
  Médico só recebe nova campanha após 3 dias
```

## Regras de Negócio

| Regra | Comportamento |
|-------|---------------|
| Cooldown | 3 dias entre campanhas diferentes |
| Mesma campanha | Isenta (permite followup) |
| Reply | Isento (não é CAMPAIGN) |
| Followup | Isento (não é CAMPAIGN) |
| Bypass humano | Permitido via Slack |

## Checklist de Implementação

### Implementar _check_campaign_cooldown

- [ ] Verificar se `method == CAMPAIGN`
- [ ] Verificar se `last_touch_method == "campaign"`
- [ ] Calcular `days_since = (now - last_touch_at).days`
- [ ] Se `days_since < 3`:
  - [ ] Verificar se é mesma campanha (isento)
  - [ ] Verificar bypass humano
  - [ ] Se não isento → BLOCK

### Integrar em check_outbound_guardrails

- [ ] Adicionar como R4 (após contact_cap)
- [ ] Emitir evento OUTBOUND_BLOCKED

### Testes

- [ ] `test_campanha_b_bloqueada_apos_campanha_a_2_dias`
- [ ] `test_mesma_campanha_followup_permitido`
- [ ] `test_reply_nao_afetado_por_cooldown`
- [ ] `test_cooldown_expirado_permite_envio`
- [ ] `test_bypass_humano_funciona`
- [ ] `test_sem_last_touch_permite_envio`

## Arquivos a Criar/Modificar

| Arquivo | Ação |
|---------|------|
| `app/services/guardrails/check.py` | Modificar |
| `tests/unit/test_guardrail_campaign_cooldown.py` | Criar |

## Definition of Done

- [ ] Guardrail implementado
- [ ] Integrado no pipeline de guardrails
- [ ] Todos os testes passando
- [ ] Evento OUTBOUND_BLOCKED emitido
- [ ] Log claro de bloqueio
- [ ] Code review aprovado

## Implementação

### Função _check_campaign_cooldown

```python
CAMPAIGN_COOLDOWN_DAYS = 3

async def _check_campaign_cooldown(
    ctx: OutboundContext,
    state: DoctorState
) -> Optional[GuardrailResult]:
    """
    R4: Cooldown entre campanhas diferentes.
    """
    # Só aplica para CAMPAIGN
    if ctx.method != OutboundMethod.CAMPAIGN:
        return None

    # Precisa ter last_touch de campanha
    if not state or state.last_touch_method != "campaign":
        return None

    if not state.last_touch_at:
        return None

    # Calcular dias
    last_touch = state.last_touch_at
    if isinstance(last_touch, str):
        last_touch = datetime.fromisoformat(last_touch.replace("Z", "+00:00"))

    if last_touch.tzinfo is None:
        last_touch = last_touch.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    days_since = (now - last_touch).days

    # Cooldown expirou?
    if days_since >= CAMPAIGN_COOLDOWN_DAYS:
        return None

    # Mesma campanha? (followup isento)
    same_campaign = (
        ctx.campaign_id
        and state.last_touch_campaign_id
        and str(ctx.campaign_id) == str(state.last_touch_campaign_id)
    )
    if same_campaign:
        return None

    # Bypass humano?
    if _is_human_slack_bypass(ctx):
        return GuardrailResult(
            decision=GuardrailDecision.ALLOW,
            reason_code="campaign_cooldown",
            human_bypass=True,
            details={"days_since": days_since, "required": CAMPAIGN_COOLDOWN_DAYS}
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

### Integração no pipeline

```python
async def check_outbound_guardrails(ctx: OutboundContext) -> GuardrailResult:
    state = await load_doctor_state(ctx.cliente_id)

    # R0: opted_out (terminal)
    # R1: controlled_by_human
    # R2: next_allowed_at
    # R3: contact_cap_7d

    # R4: campaign_cooldown
    cooldown_result = await _check_campaign_cooldown(ctx, state)
    if cooldown_result and cooldown_result.is_blocked:
        await _emit_guardrail_event(ctx, cooldown_result, "outbound_blocked")
        logger.info(
            f"BLOCK campaign_cooldown: {ctx.cliente_id[:8]} "
            f"({cooldown_result.details['days_since']}d < {CAMPAIGN_COOLDOWN_DAYS}d)"
        )
        return cooldown_result

    # ... resto do pipeline
```

## Notas de Implementação

### Cuidado com timezone

```python
# Sempre normalizar para UTC
if last_touch.tzinfo is None:
    last_touch = last_touch.replace(tzinfo=timezone.utc)

now = datetime.now(timezone.utc)
```

### Arredondamento de .days

```python
# .days arredonda para baixo
# 2.9 dias → 2 → bloqueia (correto)
# 3.0 dias → 3 → libera (correto)
days_since = (now - last_touch).days
```

### Log claro

```python
logger.info(
    f"BLOCK campaign_cooldown: {ctx.cliente_id[:8]}... "
    f"(last={state.last_touch_campaign_id[:8]}... {days_since}d ago, "
    f"current={ctx.campaign_id[:8]}...)"
)
```
