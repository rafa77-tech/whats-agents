# Sprint 70 — Meta Cloud API: Integration Bridge

## Status: Completa

**Inicio:** 2026-02-21
**PR:** [#160](https://github.com/revoluna/whatsapp-api/pull/160)
**Testes novos:** 29 (4 arquivos)

## Objetivo

Conectar o framework de decisao Meta (cost_optimizer, MM Lite, janela 24h) ao pipeline real de envio de mensagens, corrigir bug critico de propagacao de metadata no OutboundContext, e implementar decriptacao AES-128-GCM para respostas de WhatsApp Flows.

---

## Contexto (Gap Critico)

Nas Sprints 66-69, foram construidos os servicos de inteligencia Meta: cost_optimizer, quality_monitor, MM Lite, e WhatsApp Flows. Porem, esses componentes estavam **isolados** — nao conectados ao pipeline real de envio (`sender.py`, `fila_worker.py`, `multi_chip.py`).

Gaps especificos:

| Gap | Impacto | Descricao |
|-----|---------|-----------|
| `OutboundContext` sem campo `metadata` | **Critico** | `hasattr(ctx, "metadata")` retornava `False` em `multi_chip.py`, impedindo roteamento Meta |
| `sender.py` ignorava cost_optimizer | **Alto** | Envios Meta sempre usavam caminho unico, sem otimizacao de custo (free_window vs mm_lite vs template) |
| Sem auto-selecao de template | **Medio** | Quando cost_optimizer exigia template e nenhum era fornecido, envio falhava silenciosamente |
| Flow responses sem decriptacao | **Medio** | `flow_service.py` lancava `NotImplementedError` ao receber resposta criptografada de Flow |

---

## Epicos

### Epic 70.1 — Metadata Propagation

**Problema:** O `OutboundContext` (dataclass em `types.py`) nao possuia campo `metadata`, fazendo com que `hasattr(ctx, "metadata")` falhasse no `multi_chip.py`. Isso quebrava toda a cadeia de roteamento Meta.

**Solucao:** Adicionar `metadata: Optional[Dict[str, Any]] = None` ao `OutboundContext` e propagar por toda a cadeia de envio.

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| T1 | Adicionar campo `metadata` ao `OutboundContext` | `app/services/guardrails/types.py` | ✅ |
| T2 | Propagar metadata em `criar_contexto_campanha()` | `app/services/outbound/context_factories.py` | ✅ |
| T3 | Passar metadata no call do fila_worker | `app/workers/fila_worker.py` | ✅ |
| T4 | Testes de propagacao (7 testes) | `tests/services/outbound/test_metadata_propagation.py` | ✅ |

### Epic 70.2 — Cost Optimizer no Send Pipeline

**Problema:** `_enviar_meta_smart()` em `sender.py` nao consultava o `cost_optimizer`, enviando tudo pelo mesmo caminho independente do custo.

**Solucao:** Refatorar `sender.py` para consultar cost_optimizer e rotear entre `free_window`, `mm_lite`, ou `template` conforme decisao do otimizador. Feature flag `META_COST_OPTIMIZER_ENABLED` para rollout seguro.

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| T1 | Refatorar `_enviar_meta_smart()` para consultar cost_optimizer | `app/services/chips/sender.py` | ✅ |
| T2 | Implementar `_enviar_meta_com_cost_optimizer()` (roteamento free_window/mm_lite/template) | `app/services/chips/sender.py` | ✅ |
| T3 | Implementar `_enviar_meta_fallback()` (caminho quando flag desligada) | `app/services/chips/sender.py` | ✅ |
| T4 | Adicionar feature flag `META_COST_OPTIMIZER_ENABLED` | `app/core/config.py` | ✅ |
| T5 | Testes de roteamento cost_optimizer (9 testes) | `tests/services/chips/test_sender_cost_optimizer.py` | ✅ |

### Epic 70.3 — Campaign Meta E2E

**Problema:** Nao existia teste de integracao cobrindo o fluxo completo: fila → context → multi_chip → sender → Graph API. Alem disso, quando cost_optimizer exigia template mas nenhum era fornecido, o envio falhava.

**Solucao:** Auto-selecao de template via `_buscar_template_auto()` e teste E2E cobrindo pipeline completo.

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| T1 | Implementar `_buscar_template_auto()` para selecao automatica quando cost_optimizer exige template | `app/services/chips/sender.py` | ✅ |
| T2 | Teste de integracao E2E: fila → context → multi_chip → sender → Graph API (7 testes) | `tests/integration/test_campaign_meta_e2e.py` | ✅ |

### Epic 70.4 — Flow Decryption (AES-128-GCM)

**Problema:** `flow_service.py` lancava `NotImplementedError` ao tentar decriptar respostas de WhatsApp Flows. Formularios nativos enviam dados criptografados com AES-128-GCM, impossibilitando o processamento.

**Solucao:** Implementar decriptacao real usando a lib `cryptography` (AESGCM): base64 decode → separar IV (12 bytes) + ciphertext + tag (16 bytes) → decriptar → JSON parse.

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| T1 | Substituir `NotImplementedError` por decriptacao AES-128-GCM | `app/services/meta/flow_service.py` | ✅ |
| T2 | Adicionar `cryptography` ao `pyproject.toml` | `pyproject.toml` | ✅ |
| T3 | Testes de decriptacao (6 testes) | `tests/services/meta/test_flow_decryption.py` | ✅ |

---

## Arquivos Modificados/Criados

### Modificados

| Arquivo | Epico | Alteracao |
|---------|-------|-----------|
| `app/services/guardrails/types.py` | 70.1 | +3 linhas: campo `metadata` no `OutboundContext` |
| `app/services/outbound/context_factories.py` | 70.1 | +3/-1: propagacao de metadata em `criar_contexto_campanha()` |
| `app/workers/fila_worker.py` | 70.1 | +2/-1: passar metadata no call |
| `app/services/chips/sender.py` | 70.2, 70.3 | +179/-13: cost_optimizer routing + auto-template |
| `app/core/config.py` | 70.2 | +4: feature flag `META_COST_OPTIMIZER_ENABLED` |
| `app/services/meta/flow_service.py` | 70.4 | +38/-11: decriptacao AES-128-GCM |
| `pyproject.toml` | 70.4 | +1: dependencia `cryptography` |

### Criados

| Arquivo | Epico | Testes |
|---------|-------|--------|
| `tests/services/outbound/test_metadata_propagation.py` | 70.1 | 7 |
| `tests/services/chips/test_sender_cost_optimizer.py` | 70.2 | 9 |
| `tests/integration/test_campaign_meta_e2e.py` | 70.3 | 7 |
| `tests/services/meta/test_flow_decryption.py` | 70.4 | 6 |

---

## Criterios de Aceite

- [x] `OutboundContext` possui campo `metadata` e propaga corretamente por toda a cadeia (fila → context → multi_chip)
- [x] `hasattr(ctx, "metadata")` retorna `True` em `multi_chip.py`
- [x] `sender.py` consulta cost_optimizer quando `META_COST_OPTIMIZER_ENABLED=true`
- [x] Roteamento correto entre `free_window`, `mm_lite`, e `template` conforme decisao do otimizador
- [x] Feature flag `META_COST_OPTIMIZER_ENABLED` default `False` (rollout seguro)
- [x] Fallback funcional quando feature flag desligada (comportamento anterior preservado)
- [x] Auto-selecao de template via `_buscar_template_auto()` quando cost_optimizer exige template
- [x] Teste E2E cobrindo pipeline completo: fila → context → multi_chip → sender → Graph API
- [x] Decriptacao AES-128-GCM funcional em `flow_service.py` (substitui `NotImplementedError`)
- [x] 29 testes novos passando em 4 arquivos
- [x] Zero regressao nos testes existentes

---

## Metricas da Sprint

| Metrica | Valor |
|---------|-------|
| Arquivos modificados | 7 |
| Arquivos de teste criados | 4 |
| Testes novos | 29 |
| Linhas adicionadas | ~1.149 |
| Linhas removidas | ~26 |
| Dependencias adicionadas | 1 (`cryptography`) |

---

## Ordem de Execucao

```
Epic 70.1 (Metadata) ──→ Epic 70.2 (Cost Optimizer) ──→ Epic 70.3 (E2E)
                                                              │
Epic 70.4 (Flow Decryption) ─────────────────────────────── [paralelo]
```

1. **Epic 70.1** primeiro — corrigir o bug de metadata e fundacao para tudo funcionar
2. **Epic 70.2** depende de 70.1 — cost_optimizer precisa de metadata propagado
3. **Epic 70.3** depende de 70.2 — E2E testa o pipeline completo com cost_optimizer
4. **Epic 70.4** independente — pode ser feito em paralelo com qualquer epico
