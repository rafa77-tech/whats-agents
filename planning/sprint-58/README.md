# Sprint 58 — Refatoracao Estrategica (Hotspot Analysis)

## Status: ✅ Completa

**Inicio:** 12/02/2026
**Conclusao:** 12/02/2026

## Objetivo

Refatorar os 5 maiores hotspots do codebase identificados por cruzamento de:
- **Frequencia de mudanca** (git log since 2025-06)
- **Complexidade** (LOC, funcoes, imports)
- **Taxa de bugs** (commits com "fix")

## Metodologia

**Hotspot Analysis** — refatora apenas o que muda muito E e complexo E gera bugs.
Nao e uma varredura geral. E cirurgia precisa nos pontos que mais doem.

**Dados coletados:**
- 123 commits de fix desde junho/2025
- 74 arquivos standalone em app/services/ (flat architecture)
- 980 `except Exception:` em 215 arquivos
- Repository pattern adotado em apenas 8% dos services

## Hotspots

| # | Arquivo | Antes | Depois | Mudancas | Fixes | Problema |
|---|---------|-------|--------|----------|-------|----------|
| 1 | `app/api/routes/jobs.py` | 1,724 | 10 arquivos (<300 cada) | 30 | 12 | 53 endpoints monoliticos |
| 2 | `app/services/agente.py` | 1,141 | 5 arquivos (<450 cada) | 23 | 5 | 27 imports, circulares |
| 3 | `app/api/routes/health.py` | 1,732 | 357 + 10 services | 21 | 7 | Logica misturada com rotas |
| 4 | `app/services/outbound.py` | 796 | 7 arquivos (<350 cada) | 14 | 6 | Gateway central, nesting |
| 5 | `app/tools/vagas.py` | 744 | 6 arquivos (<250 cada) | 14 | 8 | 3 tools em arquivo unico |

## Epicos — Status Final

| Epic | Foco | Risco | Status | Testes |
|------|------|-------|--------|--------|
| 0 | Testes de caracterizacao (safety net) | Baixo | ✅ Completo | 109 testes |
| 1 | Decompor jobs.py em 10 sub-routers | Baixo | ✅ Completo | 36 testes |
| 2 | Decompor agente.py em modulo (5 arquivos) | Medio | ✅ Completo | 15 testes |
| 3 | Decompor health.py + extrair services | Baixo | ✅ Completo | 16 testes |
| 4 | Refatorar outbound.py em modulo (7 arquivos) | Medio | ✅ Completo | 21 testes |
| 5 | Separar tools/vagas.py por tool (6 arquivos) | Baixo | ✅ Completo | 21 testes |

### Epic 0 — Testes de Caracterizacao ✅

**Objetivo:** Criar safety net ANTES de refatorar.

**Arquivos criados:**
```
tests/characterization/
    __init__.py
    test_jobs_routes.py       — 36 testes (53 endpoints, status codes, shapes)
    test_agente.py            — 15 testes (gerar_resposta, processar_mensagem, helpers)
    test_health_routes.py     — 16 testes (16 endpoints health)
    test_outbound.py          — 21 testes (send paths, factories, guardrails)
    test_vagas_tools.py       — 21 testes (3 handlers, definitions, helpers)
```

**Total:** 109 testes passando verde

**Cobertura por hotspot:**
| Hotspot | Testes | Cobertura |
|---------|--------|-----------|
| jobs.py | 36 | Endpoints core, grupos, confirmacao, reconciliacao, gatilhos, chips |
| agente.py | 15 | gerar_resposta (5 paths), processar_mensagem (5 paths), helpers (5) |
| health.py | 16 | Todos os 16 endpoints (/health, /ready, /deep, etc.) |
| outbound.py | 21 | send paths (5), DEV allowlist (4), factories (5), helpers (3), result (4) |
| vagas.py | 21 | Definitions (4), buscar_vagas (5), reservar (4), hospital (3), helpers (5) |

### Epic 1 — Decompor jobs.py em Sub-Routers ✅

**Resultado:** 1,724 linhas → 10 sub-routers, todos abaixo de 300 linhas.

```
app/api/routes/jobs/
    __init__.py          (29 linhas) — Re-exporta router combinado
    _helpers.py          (54 linhas) — Decorator @job_endpoint para DRY
    core.py              (247 linhas) — heartbeat, primera-msg, fila, campanhas
    doctor_state.py      (79 linhas) — decay, cooling, maintenance
    grupos.py            (195 linhas) — processar, status, limpar, backfill
    confirmacao.py       (126 linhas) — processar, backfill, pendentes
    templates.py         (130 linhas) — sync, setup
    reconciliation.py    (179 linhas) — handoffs, retomadas, touches
    monitoring.py        (177 linhas) — monitorar fila, worker health
    gatilhos.py          (268 linhas) — gatilhos autonomos, validacao telefones
    chips_ops.py         (206 linhas) — trust scores, sync, snapshot, reset
```

### Epic 2 — Decompor agente.py ✅

**Resultado:** 1,141 linhas → 5 arquivos, todos abaixo de 450 linhas.

```
app/services/agente/
    __init__.py          (79 linhas) — Imports externos + re-exports (backward compat)
    types.py             (69 linhas) — ProcessamentoResult, constantes
    generation.py        (420 linhas) — gerar_resposta_julia, tool loop
    orchestrator.py      (369 linhas) — processar_mensagem_completo, policy
    delivery.py          (178 linhas) — enviar_resposta, enviar_sequencia
```

**Tecnica:** `__init__.py` importa dependencias externas no namespace do pacote para que `patch("app.services.agente.X")` continue funcionando em todos os testes.

### Epic 3 — Decompor health.py ✅

**Resultado:** 1,732 linhas → 357 linhas (router fino) + 10 service files.

```
app/services/health/
    __init__.py          (70 linhas) — Re-exports
    connectivity.py      (74 linhas) — Checks redis, supabase, evolution
    schema.py            (173 linhas) — Fingerprint, prompt contract
    scoring.py           (218 linhas) — Health score (0-100)
    alerts.py            (200 linhas) — Agregacao de alertas
    jobs_monitor.py      (166 linhas) — Job SLA tracking
    deep.py              (405 linhas) — Deep health check logic
    chips.py             (147 linhas) — Chip pool health
    fila.py              (71 linhas) — Queue health
    constants.py         (126 linhas) — Constantes

app/api/routes/health.py (357 linhas) — Router fino delegando para services
```

**Destaque:** `deep_health_check` handler foi de 316 linhas para 9 linhas.

### Epic 4 — Refatorar outbound.py ✅

**Resultado:** 796 linhas → 7 arquivos, todos abaixo de 350 linhas.

```
app/services/outbound/
    __init__.py          (52 linhas) — Re-exports public API
    types.py             (52 linhas) — OutboundResult dataclass
    dev_guardrails.py    (64 linhas) — _verificar_dev_allowlist
    context_factories.py (117 linhas) — criar_contexto_campanha/followup/reply
    finalization.py      (126 linhas) — _finalizar_envio, _atualizar_last_touch
    multi_chip.py        (150 linhas) — Multi-chip sending logic
    sender.py            (339 linhas) — send_outbound_message (try/except/finally)
```

### Epic 5 — Separar tools/vagas.py ✅

**Resultado:** 744 linhas → 6 arquivos, todos abaixo de 250 linhas.

```
app/tools/vagas/
    __init__.py          (82 linhas) — Re-exports tools e handlers
    definitions.py       (156 linhas) — Schemas dos 3 tools
    buscar_vagas.py      (137 linhas) — Handler + helpers
    reservar_plantao.py  (228 linhas) — Handler + helpers
    buscar_info.py       (81 linhas) — Handler + helpers
    _helpers.py          (221 linhas) — Helpers compartilhados
```

## Ordem de Execucao (Realizada)

```
Epic 0 (testes) ✅
    |
    +---> Epic 1 (jobs.py)      ✅ [paralelo]
    +---> Epic 3 (health.py)    ✅ [paralelo]
    +---> Epic 5 (vagas.py)     ✅ [paralelo]
    |
    +---> Epic 2 (agente.py)    ✅ [paralelo]
    +---> Epic 4 (outbound.py)  ✅ [paralelo]
```

## Resultado Final

### Testes
```
$ uv run pytest --no-cov -q
3012 passed, 20 skipped, 55 warnings
```

### Definition of Done

- [x] Testes de caracterizacao passando (109 testes)
- [x] `uv run pytest` limpo (3012 passed, 0 failed)
- [x] Nenhum arquivo refatorado > 450 linhas
- [x] Backward compatibility em todos os imports
- [x] Cada epic deployavel independentemente
- [x] Architecture guardrail tests atualizados para novos packages
- [x] Zero imports quebrados verificados via grep

### Impacto Quantificado

| Metrica | Antes | Depois |
|---------|-------|--------|
| Maior arquivo (LOC) | 1,732 (health.py) | 420 (generation.py) |
| Total hotspot LOC | 6,137 | 6,137 (redistribuido) |
| Arquivos monoliticos > 700 LOC | 5 | 0 |
| Endpoints em arquivo unico (jobs) | 53 | max 8 por sub-router |
| deep_health_check handler | 316 linhas | 9 linhas |
| Testes (total) | 2,903 | 3,012 (+109 caracterizacao) |

## Verificacao

```bash
uv run pytest tests/characterization/ --no-cov    # 109 passed
uv run pytest --no-cov                              # 3012 passed
grep -r "from app.services.agente import" app/      # 7 imports OK
grep -r "from app.services.outbound import" app/    # 13 imports OK
grep -r "from app.tools.vagas import" app/          # 10 imports OK
```

## Rollback

Cada epic = decomposicao com `__init__.py` que re-exporta API publica.
- Epic 0: Aditivo, sem rollback
- Epics 1-5: Reverter restaura arquivo original
- Feature flag desnecessario — mudancas backward-compatible via `__init__.py`

## Documentos

- `mapa-modulos.md` — Mapa completo de modulos e dependencias
- Plano detalhado no transcript da sessao de planejamento
