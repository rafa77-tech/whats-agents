# Meta Cloud API — Status & Merge Order

> Atualizado em 2026-02-21

## PRs Pendentes (Merge Order)

Merge na ordem abaixo. PR3 depende de PR2.

| # | PR | Branch | Base | Status | Link |
|---|-----|--------|------|--------|------|
| 1 | Sprint 69: Flows dashboard + DDD campanhas | `feat/sprint-69-flows-ddd-campanhas` | `main` | Aguardando review | [#158](https://github.com/rafa77-tech/whats-agents/pull/158) |
| 2 | Sprint 70: Meta integration bridge | `feat/sprint-70-meta-integration-bridge` | `main` | Aguardando review | [#160](https://github.com/rafa77-tech/whats-agents/pull/160) |
| 3 | Sprint 71: Meta dashboard UI | `feat/sprint-71-meta-dashboard-ui` | `feat/sprint-70-meta-integration-bridge` | Aguardando PR #160 | [#161](https://github.com/rafa77-tech/whats-agents/pull/161) |

### Procedimento de Merge

```
1. Merge PR #158 → main  (independente)
2. Merge PR #160 → main  (independente)
3. Rebase PR #161 em main (após PR #160 mergear)
4. Merge PR #161 → main
```

> **Atenção:** PR #161 foi criado com base em `feat/sprint-70-meta-integration-bridge`.
> Após merge do PR #160, fazer rebase de PR #161 em main antes de mergear.

---

## O que foi implementado (Sprints 66-71)

### Sprint 66-69 (já em main)

23 servicos em `app/services/meta/` (~5,148 LOC):

| Servico | Arquivo | Funcionalidade |
|---------|---------|----------------|
| Template CRUD | `template_service.py` | Criar, listar, buscar, atualizar templates via Graph API |
| Window Tracker | `window_tracker.py` | Rastrear janela 24h de conversa |
| Cost Optimizer | `cost_optimizer.py` | Decisao de envio (free_window/template/mm_lite) |
| MM Lite | `mm_lite.py` | Elegibilidade e metricas de Marketing Messages Lite |
| Quality Monitor | `quality_monitor.py` | Polling de quality rating, auto-degrade/recover |
| Quality Rules | `quality_rules.py` | Trust recovery, anti-flap, regras de transicao |
| Flow Service | `flow_service.py` | CRUD de WhatsApp Flows |
| Template Analyzer | `template_analyzer.py` | Metricas de performance de templates |
| Template Optimizer | `template_optimizer.py` | Recomendacoes de melhoria |
| Carousel Builder | `carousel_builder.py` | Construcao de carousel a partir de vagas |
| Template Mapper | `template_mapper.py` | Substituicao de variaveis em templates |
| OTP Builder | `otp_template_builder.py` | Templates de autenticacao/OTP |
| OTP Confirmation | `otp_confirmation.py` | Fluxo de confirmacao one-tap |
| WABA Selector | `waba_selector.py` | Selecao de WABA por quality/custo |
| BSUID Compat | `bsuid_compat.py` | Preparacao para migracao BSUID |
| Catalog Service | `catalog_service.py` | Sincronizacao de catalogo |
| Media Service | `media_service.py` | Upload e referencia de midia |
| Budget Alerts | `budget_alerts.py` | Monitoramento de budget diario/semanal/mensal |
| Conversation Analytics | `conversation_analytics.py` | Metricas de mensagens |
| Dashboard Service | `dashboard_service.py` | Agregacao de dados para UI |
| Window Keeper | `window_keeper.py` | Manutenção proativa de janelas |

Provider: `MetaCloudProvider` em `whatsapp_providers/meta_cloud.py` — send_text, send_template, send_text_mm_lite, send_interactive, send_media.

Dashboard em main: 4 tabs (Templates, Qualidade, Custos, Flows) + 7 API routes.

### Sprint 70 (PR #160) — Integration Bridge

| Epic | O que resolve |
|------|---------------|
| 70.1 Metadata Propagation | `OutboundContext.metadata` + propagacao em context_factories + fila_worker |
| 70.2 Cost Optimizer no Pipeline | `_enviar_meta_smart()` consulta cost_optimizer, roteia para free/template/mm_lite |
| 70.3 Campaign E2E | Auto-template selection + teste integracao completo |
| 70.4 Flow Decryption | AES-128-GCM implementado (cryptography lib) |

29 testes novos em 4 arquivos.

### Sprint 71 (PR #161) — Dashboard UI + Features

| Epic | O que resolve |
|------|---------------|
| 71.1 Budget Status | API route + BudgetStatusCard com progress bars |
| 71.2 MM Lite + Catalog | 5a tab "Catalogo", metricas MM Lite, lista de produtos |
| 71.3 Template Optimization | Job semanal `meta_template_optimization` no scheduler |
| 71.4 Window + Quality Timeline | Job `meta_window_keeper`, API windows, chart recharts |

4 novas API routes, 1 novo componente, 2 jobs no scheduler.

---

## O que falta desenvolver (Sprint 72+)

### Prioridade Alta

| Item | Descricao | Dependencia | Complexidade |
|------|-----------|-------------|--------------|
| Dashboard: Seletor de Template em Campanhas | Formulario de criacao de campanha deve expor seletor de Meta template | PR #160 | Media |
| Carousel no Executor | `campanha_executor` constroi cards via `carousel_builder` a partir de vagas | PR #160 | Media |
| Quality Check Job | Job recorrente (15 min) que chama `quality_monitor.verificar_quality_chips()` | — | Baixa |

### Prioridade Media (Sprint 72)

| Item | Arquivo | Descricao |
|------|---------|-----------|
| Multi-WABA Strategy | `waba_selector.py` → `chip_selector.py` | Selecao por quality/custo/capacidade. Servico existe, falta wiring |
| OTP + Confirmacao de Plantao | `otp_confirmation.py` | Conectar ao pipeline de confirmacao existente. Template AUTHENTICATION |
| Conversation Routing | `chip_selector.py` | Preferir chip que ja comunicou com o medico (historico) |
| Catalog Sync Real | `catalog_service.py` | Push via `POST /{catalog_id}/items_batch` na Graph API |

### Prioridade Baixa (Sprint 73+)

| Item | Arquivo | Descricao |
|------|---------|-----------|
| BSUID Migration | `bsuid_compat.py` | Ativar quando Meta migrar phone_number_id → BSUID |
| Policy RAG | Novo servico | Scraping + indexacao de politicas oficiais WhatsApp/Meta |

---

## Tabelas no Banco

| Tabela | Status |
|--------|--------|
| `meta_templates` | ✅ Implementada |
| `meta_flows` | ✅ Implementada |
| `meta_conversation_windows` | ✅ Implementada |
| `meta_quality_history` | ✅ Implementada |
| `meta_mm_lite_metrics` | ✅ Implementada |
| `meta_conversation_costs` | ✅ Implementada |
| `meta_catalog_products` | ⚠️ Stub |
| `meta_template_recommendations` | ⚠️ Usado pelo job Sprint 71, verificar existencia |
| `meta_waba_settings` | ❌ Necessaria para Multi-WABA (Sprint 72) |

## Config (`app/core/config.py`)

Todos os META_* settings existem. Sprint 70 adiciona:
- `META_COST_OPTIMIZER_ENABLED: bool = False` (feature flag)
