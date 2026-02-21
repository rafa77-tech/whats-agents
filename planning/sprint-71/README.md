# Sprint 71 — Meta Dashboard UI + Advanced Features

## Status: Completa

**Inicio previsto:** 2026-02-21
**Pre-requisito:** Sprint 70 completa (PR #160 — Meta Integration Bridge)
**PR:** [#161](https://github.com/revoluna/whatsapp-api/pull/161)

## Objetivo

Evoluir o dashboard Meta com funcionalidades avancadas de monitoramento: controle de budget em tempo real com status visual, painel de catalogo com metricas MM Lite, otimizacao automatica de templates via scheduler, e gestao proativa de janelas de conversa com timeline de qualidade. Adiciona a 5a aba ("Catalogo") a pagina Meta unificada.

---

## Diagnostico (pre-sprint)

| Metrica | Sprint 70 (Antes) | Sprint 71 (Depois) |
|---------|-------------------|---------------------|
| Abas Meta dashboard | 4 (Templates, Qualidade, Custos, Flows) | 5 (+Catalogo) |
| Rotas API Meta dashboard | ~6 | 10 (+4 novas) |
| Scheduler jobs Meta | 4 | 6 (+2 novos) |
| Monitoramento de budget | Nenhum | Diario/semanal/mensal com status visual |
| Gestao de janelas | Manual | Automatizada (window keeper a cada 2h) |
| Otimizacao de templates | Nenhuma | Semanal com recomendacoes automaticas |

---

## Epicos

| # | Epico | Escopo | Dep. |
|---|-------|--------|------|
| 71.1 | Budget Status | API + componente de budget com progress bars | Nenhuma |
| 71.2 | MM Lite + Catalog Dashboard | 2 APIs + nova aba Catalogo | Nenhuma |
| 71.3 | Template Optimization | Scheduler job semanal + endpoint | Nenhuma |
| 71.4 | Window Management + Quality Timeline | Scheduler job + API + timeline chart | Nenhuma |

---

### Epic 71.1 — Budget Status

Monitoramento de gastos diario, semanal e mensal contra limites configurados via env vars. Card visual com progress bars e status color-coded.

**Tarefas:**

| # | Tarefa | Status |
|---|--------|--------|
| T1 | Criar rota `GET /api/dashboard/meta/budget` com queries em `meta_conversation_costs` | ✅ |
| T2 | Implementar logica de periodos (daily/weekly/monthly) com calculo de percentual | ✅ |
| T3 | Criar componente `BudgetStatusCard` com progress bars no `analytics-tab.tsx` | ✅ |
| T4 | Implementar status color-coded: `ok` (verde), `warning` (amarelo), `critical` (laranja), `blocked` (vermelho) | ✅ |
| T5 | Definir constante `BUDGET_FALLBACK` para type safety | ✅ |
| T6 | Adicionar mock de budget nos testes do analytics-tab | ✅ |

**Limites default:**
- Diario: `META_BUDGET_DIARIO_USD` = $50
- Semanal: `META_BUDGET_SEMANAL_USD` = $300
- Mensal: `META_BUDGET_MENSAL_USD` = $1200

---

### Epic 71.2 — MM Lite + Catalog Dashboard

Nova aba "Catalogo" com metricas de MM Lite (ultimos 7 dias) e listagem de produtos do catalogo Meta.

**Tarefas:**

| # | Tarefa | Status |
|---|--------|--------|
| T1 | Criar rota `GET /api/dashboard/meta/mm-lite` com metricas de 7 dias de `meta_mm_lite_metrics` | ✅ |
| T2 | Criar rota `GET /api/dashboard/meta/catalog` com produtos de `meta_catalog_products` | ✅ |
| T3 | Criar componente `catalog-tab.tsx` com cards de metricas MM Lite + lista de produtos | ✅ |
| T4 | Adicionar 5a aba "Catalogo" em `meta-unified-page.tsx` (grid-cols-5) | ✅ |
| T5 | Definir tipos `MetaMMLiteMetrics` e `MetaCatalogProduct` em `types/meta.ts` | ✅ |
| T6 | Adicionar funcoes `getMMLiteMetrics()` e `getCatalogProducts()` em `lib/api/meta.ts` | ✅ |
| T7 | Atualizar teste meta-page para validar 5 abas | ✅ |

---

### Epic 71.3 — Template Optimization

Job de scheduler semanal que analisa performance de templates e salva recomendacoes automaticas.

**Tarefas:**

| # | Tarefa | Status |
|---|--------|--------|
| T1 | Criar endpoint `POST /jobs/meta-template-optimization` em `meta_analytics.py` | ✅ |
| T2 | Integrar com `template_optimizer.identificar_baixa_performance()` (7 dias) | ✅ |
| T3 | Gerar sugestoes via `template_optimizer.sugerir_melhorias()` | ✅ |
| T4 | Salvar recomendacoes em `meta_template_recommendations` via upsert | ✅ |
| T5 | Registrar job `meta_template_optimization` no scheduler (cron: `0 5 * * 1` — segunda 5h) | ✅ |

---

### Epic 71.4 — Window Management + Quality Timeline

Gestao proativa de janelas de conversa com scheduler e visualizacao de historico de qualidade com grafico timeline.

**Tarefas:**

| # | Tarefa | Status |
|---|--------|--------|
| T1 | Criar endpoint `POST /jobs/meta-window-keeper` em `meta_quality.py` | ✅ |
| T2 | Integrar com `window_keeper.executar_check_in()` | ✅ |
| T3 | Registrar job `meta_window_keeper` no scheduler (cron: `0 8,10,12,14,16,18 * * 1-5` — a cada 2h, seg-sex) | ✅ |
| T4 | Criar rota `GET /api/dashboard/meta/windows` com dados de `meta_conversation_windows` | ✅ |
| T5 | Implementar sumario de janelas (active/expiring/expired) no `quality-tab.tsx` | ✅ |
| T6 | Implementar timeline chart de historico de qualidade usando recharts `LineChart` no `quality-tab.tsx` | ✅ |
| T7 | Definir tipo `MetaWindowSummary` em `types/meta.ts` | ✅ |

---

## Arquivos Modificados/Criados

### Backend (Python)

```
Modif:  app/api/routes/jobs/meta_analytics.py    (+44 linhas — endpoint template optimization)
Modif:  app/api/routes/jobs/meta_quality.py       (+23 linhas — endpoint window keeper)
Modif:  app/workers/scheduler.py                  (+12 linhas — 2 novos jobs)
```

### Dashboard — Rotas API (TypeScript)

```
Criar:  dashboard/app/api/dashboard/meta/budget/route.ts    (91 linhas — budget status)
Criar:  dashboard/app/api/dashboard/meta/mm-lite/route.ts   (46 linhas — MM Lite metrics)
Criar:  dashboard/app/api/dashboard/meta/catalog/route.ts   (28 linhas — catalog products)
Criar:  dashboard/app/api/dashboard/meta/windows/route.ts   (49 linhas — window summary)
```

### Dashboard — Componentes (TypeScript/React)

```
Criar:  dashboard/components/meta/tabs/catalog-tab.tsx       (143 linhas — nova aba Catalogo)
Modif:  dashboard/components/meta/meta-unified-page.tsx      (+51/-7 — 5a aba + grid-cols-5)
Modif:  dashboard/components/meta/tabs/analytics-tab.tsx     (+209/-46 — BudgetStatusCard + progress bars)
Modif:  dashboard/components/meta/tabs/quality-tab.tsx       (+188/-36 — timeline chart + window summary)
```

### Dashboard — Tipos e API Client

```
Modif:  dashboard/types/meta.ts                              (+101/-3 — MetaMMLiteMetrics, MetaCatalogProduct, MetaWindowSummary, BudgetStatus)
Modif:  dashboard/lib/api/meta.ts                            (+79 — getBudgetStatus, getMMLiteMetrics, getCatalogProducts, getWindowSummary)
```

### Testes

```
Modif:  dashboard/__tests__/components/meta/analytics-tab.test.tsx  (+18 — mock de budget)
Modif:  dashboard/__tests__/components/meta/meta-page.test.tsx      (+6/-2 — validacao 5 abas)
```

---

## Scheduler Jobs Adicionados

| Job | Endpoint | Cron | Descricao |
|-----|----------|------|-----------|
| `meta_template_optimization` | `/jobs/meta-template-optimization` | `0 5 * * 1` | Segunda 5h — analisa templates e salva recomendacoes |
| `meta_window_keeper` | `/jobs/meta-window-keeper` | `0 8,10,12,14,16,18 * * 1-5` | A cada 2h em horario comercial, seg-sex |

---

## Criterios de Aceite

- [x] Analytics tab exibe card de budget com progress bars (diario/semanal/mensal)
- [x] Status color-coded funcional: ok (verde), warning (amarelo), critical (laranja), blocked (vermelho)
- [x] Quality tab exibe timeline chart com historico via recharts LineChart
- [x] Quality tab exibe sumario de janelas (active/expiring/expired)
- [x] Nova aba "Catalogo" renderiza metricas MM Lite e lista de produtos
- [x] Meta page renderiza 5 abas corretamente
- [x] Job `meta_template_optimization` registrado no scheduler (semanal)
- [x] Job `meta_window_keeper` registrado no scheduler (a cada 2h, horario comercial)
- [x] 4 novas rotas API funcionais: budget, mm-lite, catalog, windows
- [x] Testes atualizados passando (analytics-tab com mock de budget, meta-page com 5 abas)

---

## Dependencias

| Epico | Depende de | Status |
|-------|-----------|--------|
| Todos | Sprint 70 (PR #160 — Meta Integration Bridge) | ✅ |
| 71.1 | Tabela `meta_conversation_costs` (Sprint 67) | ✅ |
| 71.2 | Tabelas `meta_mm_lite_metrics` e `meta_catalog_products` (Sprint 70) | ✅ |
| 71.3 | Tabela `meta_template_recommendations` + `template_optimizer` service (Sprint 70) | ✅ |
| 71.4 | Tabela `meta_conversation_windows` + `window_keeper` service (Sprint 70) | ✅ |

---

## Riscos

| Risco | Impacto | Probabilidade | Mitigacao |
|-------|---------|---------------|-----------|
| Budget API lenta com volume alto de `meta_conversation_costs` | Medio | Media | Queries com filtro por data, somatorio client-side |
| MM Lite desabilitado em producao | Baixo | Alta | Flag `META_MM_LITE_ENABLED` com fallback gracioso |
| Template optimizer sem dados suficientes | Baixo | Media | Minimo de 7 dias de dados, fallback vazio |
| Window keeper enviando check-ins desnecessarios | Medio | Baixa | Opt-in por chip, horario comercial apenas |

---

## Ordem de Execucao

1. **Fase 1 — APIs e tipos (paralelo):**
   - Epic 71.1: rota budget + tipos
   - Epic 71.2: rotas mm-lite e catalog + tipos
   - Epic 71.4: rota windows + tipos

2. **Fase 2 — Componentes (paralelo):**
   - Epic 71.1: BudgetStatusCard no analytics-tab
   - Epic 71.2: catalog-tab + 5a aba
   - Epic 71.4: timeline chart + window summary no quality-tab

3. **Fase 3 — Backend scheduler:**
   - Epic 71.3: endpoint + job template optimization
   - Epic 71.4: endpoint + job window keeper

4. **Fase 4 — Testes e validacao:**
   - Atualizar testes analytics-tab e meta-page
   - `cd dashboard && npm run validate`
   - `uv run pytest tests/workers/test_scheduler.py -v`
