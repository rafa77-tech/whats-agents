# Sprint 67 — Intelligence Layer (Meta Cloud API)

## Status: Planejado

**Inicio previsto:** 2026-02-21
**Pre-requisito:** Sprint 66 completa e em producao

## Objetivo

Transformar a integracao basica da Meta Cloud API (Sprint 66) em inteligencia agentica. Julia nao apenas usa a API — ela toma decisoes inteligentes sobre COMO usar: monitora quality em tempo real, envia mensagens interativas quando faz sentido, e otimiza custos automaticamente.

---

## Diagnostico (pre-sprint)

| Metrica | Sprint 66 (Atual) | Sprint 67 (Meta) |
|---------|-------------------|-------------------|
| Quality monitoring | Manual (webhook status) | Auto-polling + auto-degrade + alerts |
| Interactive messages | Provider-level only | Agente Julia decide quando usar |
| Template analytics | Nenhum | Delivery, read, click tracking |
| Conversation analytics | Nenhum | Custo por tipo, volume, budget |
| Testes Meta total | 105 | ~210 |

---

## Gap Analysis do Roadmap

### Gaps identificados no roadmap original (`roadmap-meta-nivel-twilio.md`)

| # | Gap | Impacto | Resolucao |
|---|-----|---------|-----------|
| R1 | **Interactive tools nao integram com LLM** — Julia usa Claude tool calling, nao funcoes Python | Alto | Epic 67.0 T-R1: modificar `generation.py` (JULIA_TOOLS + handlers) |
| R2 | **delivery.py so envia texto** — `enviar_resposta()` e `send_outbound_message()` nao suportam interactive | Medio | Epic 67.0 T-R2: novo `send_outbound_interactive()` |
| R3 | **Outbound guardrails nao validam interactive** — payload bypassa validacao de conteudo | Medio | Epic 67.0 T-R3: `validar_payload_interactive()` + `sanitizar_payload_interactive()` |
| R4 | **Quality Monitor sem tabela de historico** | Baixo | ✅ Coberto em Epic 67.1 T1 |
| R5 | **Template Analytics sem periodicidade de polling** | Baixo | ✅ Coberto em Epic 67.3 T4 (cron diario 6h) |
| R6 | **Pricing hardcoded** — Meta mudou pricing Jul/2025, precisa ser configuravel | Medio | Epic 67.0 T-R6: pricing via `settings` |
| R7 | **response_formatter.py sem formato interactive** | Medio | ✅ Coberto em Epic 67.2 T4 + Epic 67.0 T-R7 (compatibilidade) |
| R8 | **Webhook para interactive responses** | Baixo | ✅ Ja funciona (webhook_meta.py linhas 269-275) |
| R9 | **Sem rollback strategy para quality auto-degrade** | Medio | Epic 67.0 T-R9: regras de recovery + anti-flap |
| R10 | **CTA URL + janela 24h** — interactive so funciona dentro da janela | Alto | Epic 67.0 T-R10: window check em todos os handlers |

### O que o roadmap cobre bem

- [x] Quality Monitor com polling e auto-degradacao — conceito correto
- [x] Interactive messages: cenarios de uso claros (vagas, confirmacao)
- [x] Template Analytics: endpoint da Meta bem documentado
- [x] Conversation Analytics: tipos de custo bem mapeados
- [x] Diferenciais agenticos: bem definidos vs concorrentes

---

## Epicos

| # | Epico | Testes | Dep. | Doc |
|---|-------|--------|------|-----|
| 67.0 | Resolucao de Gaps do Roadmap | ~35 | Nenhuma | `epic-67-0-gap-resolution.md` |
| 67.1 | Quality Monitor Service | ~18 | Nenhuma | `epic-67-1-quality-monitor.md` |
| 67.2 | Interactive Messages no Agente Julia | ~25 | 67.0, 67.1 | `epic-67-2-interactive-messages.md` |
| 67.3 | Template Analytics | ~14 | Nenhuma | `epic-67-3-template-analytics.md` |
| 67.4 | Conversation Analytics & Cost Tracking | ~12 | 67.0 (R6) | `epic-67-4-conversation-analytics.md` |

**Total estimado:** ~104 testes novos

---

## Criterios de Sucesso

- [ ] Quality Monitor polling a cada 15 min com auto-degrade funcional
- [ ] Auto-recovery funcional com protecao anti-flap
- [ ] Julia envia reply buttons quando tem opcoes claras (vagas, confirmacao)
- [ ] Julia envia list message quando tem >3 opcoes
- [ ] Fallback para texto quando chip nao e Meta
- [ ] Nenhum interactive enviado fora da janela 24h (R10)
- [ ] Interactive passa por guardrails e validacao de payload (R3)
- [ ] Interactive integrado com tool calling do Claude (R1)
- [ ] Template analytics coletando delivery/read rates
- [ ] Conversation analytics rastreando custo por tipo
- [ ] Pricing configuravel via env vars (R6)
- [ ] Slack alerts para quality YELLOW/RED e budget excedido
- [ ] 104+ testes novos passando
- [ ] Zero regressao nos 105 testes Meta da Sprint 66

---

## Riscos

| Risco | Impacto | Probabilidade | Mitigacao |
|-------|---------|---------------|-----------|
| Quality API rate limit | Medio | Baixa | Cache 15 min, polling conservador |
| Interactive msg rejeitada pelo usuario | Alto | Media | A/B test: interactive vs texto |
| Template Analytics API indisponivel | Baixo | Baixa | Retry + cache stale data |
| Breaking change na delivery pipeline | Alto | Media | Testes de regressao + feature flag |
| Julia envia interactive fora da janela 24h | Critico | Media | Window check obrigatorio (R10) |
| Tool interactive envia payload invalido | Medio | Media | Validacao + sanitizacao (R3) |
| Quality flapping (oscilacao rapida) | Medio | Baixa | Anti-flap com cooldown 6h (R9) |

---

## Dependencias

| Epico | Depende de | Status |
|-------|-----------|--------|
| 67.0 | Sprint 66 completa | ✅ |
| 67.1 | Meta Quality API access (WABA configurado) | Precisa WABA em producao |
| 67.2 | 67.0 (gaps R1-R3, R10), 67.1 (quality check) | Sequencial |
| 67.3 | Meta Template Analytics API | Precisa WABA com templates ativos |
| 67.4 | 67.0 (gap R6 — pricing config) | Sequencial parcial |
| Todos | Sprint 66 gaps G1-G4 resolvidos | ✅ Commit 9ff38fa |

---

## Arquivos por Epico (resumo)

### Epic 67.0 — Gap Resolution
```
Modif:  app/services/agente/generation.py (R1: JULIA_TOOLS + handlers)
Modif:  app/services/outbound/sender.py (R2: send_outbound_interactive)
Modif:  app/services/outbound/__init__.py (R2: re-export)
Modif:  app/services/outbound/multi_chip.py (R2: interactive routing)
Modif:  app/services/chips/sender.py (R2: enviar_interactive_via_chip)
Modif:  app/core/config.py (R6: META_PRICING_* settings)
Modif:  app/services/meta/quality_monitor.py (R9: recovery + anti-flap)
Criar:  tests/services/agente/test_generation_interactive.py (R1)
Criar:  tests/services/outbound/test_interactive_outbound.py (R2)
Criar:  tests/tools/test_interactive_validation.py (R3)
Criar:  tests/services/meta/test_pricing_config.py (R6)
Criar:  tests/tools/test_interactive_formatter_compat.py (R7)
Criar:  tests/services/meta/test_quality_recovery.py (R9)
Criar:  tests/tools/test_interactive_window.py (R10)
```

### Epic 67.1 — Quality Monitor
```
Criar:  app/services/meta/quality_monitor.py
Criar:  app/workers/meta_quality_worker.py
Criar:  tests/services/meta/test_quality_monitor.py
Criar:  tests/workers/test_meta_quality_worker.py
Modif:  app/services/chips/orchestrator.py (auto-degrade hook)
Modif:  app/workers/scheduler.py (novo job)
Migr:   meta_quality_history (nova tabela)
```

### Epic 67.2 — Interactive Messages
```
Criar:  app/tools/interactive_messages.py
Criar:  tests/tools/test_interactive_messages.py
Modif:  app/tools/registry.py (registrar novas tools)
Modif:  app/tools/vagas/definitions.py (hint interactive no prompt)
Modif:  app/tools/response_formatter.py (formato interactive)
```

### Epic 67.3 — Template Analytics
```
Criar:  app/services/meta/template_analytics.py
Criar:  app/api/routes/meta_analytics.py
Criar:  tests/services/meta/test_template_analytics.py
Criar:  tests/api/routes/test_meta_analytics.py
Modif:  app/main.py (registrar router)
Modif:  app/workers/scheduler.py (novo job)
Migr:   meta_template_analytics (nova tabela)
```

### Epic 67.4 — Conversation Analytics
```
Criar:  app/services/meta/conversation_analytics.py
Criar:  tests/services/meta/test_conversation_analytics.py
Modif:  app/services/chips/sender.py (registrar custo pos-envio)
Modif:  app/workers/scheduler.py (novo job)
Migr:   meta_conversation_costs (nova tabela + view)
```

---

## Ordem de Execucao

```
                    ┌─ Epic 67.0 T-R6 (pricing) ──→ Epic 67.4 (Conversation Analytics)
                    │
                    ├─ Epic 67.0 T-R9 (recovery) ─→ Epic 67.1 (Quality Monitor)
                    │
Epic 67.0 (Gaps) ──┤  Epic 67.3 (Template Analytics) [paralelo, sem dep]
                    │
                    ├─ Epic 67.0 T-R3 (validacao) ─┐
                    ├─ Epic 67.0 T-R10 (janela) ────┤
                    ├─ Epic 67.0 T-R1 (LLM) ────────┼──→ Epic 67.2 (Interactive Messages)
                    ├─ Epic 67.0 T-R2 (delivery) ───┤
                    └─ Epic 67.0 T-R7 (formatter) ──┘
```

### Fases

**Fase 1 — Fundacao (paralelo):**
- Epic 67.0 T-R6 (pricing config)
- Epic 67.0 T-R9 (auto-recovery + anti-flap)
- Epic 67.0 T-R3 (validacao interactive)
- Epic 67.3 (Template Analytics)

**Fase 2 — Core services (paralelo):**
- Epic 67.1 (Quality Monitor) — depende de R9
- Epic 67.4 (Conversation Analytics) — depende de R6
- Epic 67.0 T-R10 (window check)
- Epic 67.0 T-R2 (delivery pipeline)

**Fase 3 — Integracao (sequencial):**
- Epic 67.0 T-R1 (LLM integration)
- Epic 67.0 T-R7 (formatter compat)
- Epic 67.2 (Interactive Messages) — depende de tudo acima
