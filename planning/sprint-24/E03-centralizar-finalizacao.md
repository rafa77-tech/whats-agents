# E03: Centralizar finalização + last_touch

**Status:** Pendente
**Estimativa:** 0.5 dia
**Dependências:** E02 (intent_dedupe)

---

## Objetivo

1. Garantir que TODO envio passe por `_finalizar_envio()` (try/finally)
2. Atualizar `last_touch_*` no `doctor_state` quando outcome é conhecido
3. Padronizar metadata de envio

## Problema

```
Hoje:
  send_outbound_message() tem 4+ returns espalhados
  Fácil esquecer de atualizar estado ou emitir evento
  Reprocessamento pode duplicar contadores

Depois:
  try/finally garante _finalizar_envio() sempre executa
  Idempotência via cache
  Outcomes padronizados
```

## Checklist de Implementação

### Migração SQL

- [ ] Adicionar campos a `doctor_state`:
  - [ ] `last_touch_at TIMESTAMPTZ`
  - [ ] `last_touch_campaign_id UUID`
  - [ ] `last_touch_method TEXT`
  - [ ] `last_touch_outcome TEXT`

- [ ] Criar índice:
  - [ ] `idx_doctor_state_last_touch(last_touch_at, last_touch_campaign_id)`

### Refatorar send_outbound_message

- [ ] Estrutura try/finally:
  ```python
  async def send_outbound_message(...) -> OutboundResult:
      result: OutboundResult = None
      try:
          # 1. Guardrail
          # 2. Intent dedupe (E02)
          # 3. Content dedupe
          # 4. Envio
          return result
      except Exception as e:
          result = OutboundResult(outcome=FAILED_UNKNOWN, ...)
          return result
      finally:
          if result and ctx.cliente_id:
              await _finalizar_envio(ctx, result)
  ```

- [ ] Integrar `verificar_intent()` do E02

### Implementar _finalizar_envio

- [ ] Idempotência via cache (TTL 1h)
- [ ] Não atualizar last_touch para BLOCKED_OPTED_OUT
- [ ] Atualizar campos:
  - [ ] `last_touch_at`
  - [ ] `last_touch_method`
  - [ ] `last_touch_outcome`
  - [ ] `last_touch_campaign_id` (se houver)
- [ ] Emitir evento para DEDUPED_INTENT

### Atualizar SendOutcome

- [ ] Separar dedupes:
  - [ ] `DEDUPED_INTENT` (por intenção)
  - [ ] `DEDUPED_CONTENT` (por content_hash)
- [ ] Adicionar `FAILED_UNKNOWN`

### Helper preparar_metadata_envio

- [ ] Criar função helper:
  ```python
  def preparar_metadata_envio(
      strategy_type: str,
      intent_type: str,
      campaign_id: str = None,
      campaign_run_id: str = None,
      template_version: str = None,
      detected_profile: str = None,
      detected_objection: str = None,
  ) -> dict
  ```

### Testes

- [ ] `test_finally_executa_em_sucesso`
- [ ] `test_finally_executa_em_excecao`
- [ ] `test_finally_executa_em_blocked`
- [ ] `test_finally_executa_em_deduped`
- [ ] `test_idempotencia_reprocessamento`
- [ ] `test_opted_out_nao_atualiza_last_touch`
- [ ] `test_evento_emitido_para_intent_duplicate`

## Arquivos a Criar/Modificar

| Arquivo | Ação |
|---------|------|
| `supabase/migrations/YYYYMMDD_last_touch_fields.sql` | Criar |
| `app/services/outbound.py` | Modificar (refatorar) |
| `app/services/guardrails/types.py` | Modificar (SendOutcome) |
| `tests/unit/test_outbound_finalization.py` | Criar |

## Definition of Done

- [ ] Migração aplicada em staging
- [ ] send_outbound_message com try/finally
- [ ] _finalizar_envio com idempotência
- [ ] SendOutcome atualizado
- [ ] Todos os testes passando
- [ ] Code review aprovado

## Notas de Implementação

### Idempotência

```python
async def _finalizar_envio(ctx, result):
    # Cache key baseado em dedupe_key ou intent_fingerprint
    cache_key = f"finalized:{result.dedupe_key or ctx.metadata.get('intent_fingerprint', '')}"

    if cache_key != "finalized:":
        already = await cache_get(cache_key)
        if already:
            return  # Já finalizado
        await cache_set(cache_key, "1", ttl=3600)

    # ... resto
```

### Quando NÃO atualizar last_touch

```python
# Optout não deve "sujar" métricas
if result.outcome == SendOutcome.BLOCKED_OPTED_OUT:
    return

# Conversa sob humano também não
if ctx.controlled_by == "human":
    return
```

### Evento para intent duplicate

```python
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
