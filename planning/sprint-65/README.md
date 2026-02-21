# Sprint 65 — Warmup System Fix & Hardening

## Status: 📋 Planejada

**Inicio:** 2026-02-20
**Estimativa:** 1.5 semanas

## Objetivo

Corrigir o sistema de warmup que esta 100% quebrado (CONVERSA_PAR com 0% de sucesso) devido a 8 causas raiz identificadas em auditoria, e elevar a robustez para nivel enterprise com pre-send validation, error handling estruturado e observabilidade completa.

**Origem:** Auditoria de warmup (2026-02-20) — 17 CONVERSA_PAR falharam, 5 MENSAGEM_GRUPO falharam, apenas MARCAR_LIDO funciona. 5 chips parados em primeiros_contatos com metricas zeradas.

---

## Diagnostico

| Metrica | Valor Atual | Meta |
|---------|-------------|------|
| Taxa sucesso CONVERSA_PAR | 0% (17/17 falhas) | >90% |
| Taxa sucesso MENSAGEM_GRUPO | 0% (5/5 falhas - stub) | N/A (remover) |
| Chips progredindo de fase | 0 de 5 | 5 de 5 |
| warming_day atualizado | 0 para todos | Calculado automaticamente |
| Chip z-api ativo | Desconectado (Event loop closed) | Reconectado ou substituido |
| Circuit breaker pre-send | Nao verificado | Verificado |
| Health check endpoint | Nao existe | /warmer/health operacional |

### Causas raiz (8 identificadas)

1. **Pairing Engine filtra status inexistente** — `pairing_engine.py:109` usa `.eq("status", "connected")` mas nenhum chip tem esse status. Status reais: warming, active, degraded, provisioned. Query retorna 0 chips → CONVERSA_PAR impossivel.
2. **warming_day nunca incrementado** — Campo em 0 para todos os chips. Nenhum codigo atualiza.
3. **Stubs agendados como trabalho real** — ENTRAR_GRUPO, MENSAGEM_GRUPO, ATUALIZAR_PERFIL retornam False sempre. Scheduler agenda → falham → degradam trust score.
4. **Timestamp errado na transicao** — `orchestrator.py:271` usa `created_at` ao inves de `warming_started_at`.
5. **Chip z-api desconectado** — Chip ...8618 com "Event loop is closed", 24 erros/24h.
6. **Metricas zeradas** — 5 chips com msgs_enviadas=0, conversas_bidirecionais=0. Consequencia da causa 1.
7. **Circuit breaker ignorado** — Executor nao verifica ChipCircuitBreaker antes de enviar.
8. **Exception handling engole erros** — `except Exception as e: return False` sem stack trace.

---

## Epicos

| # | Epico | Prioridade | Foco | Dependencias |
|---|-------|-----------|------|--------------|
| 01 | Fix Pairing Engine & Scheduler | P0 (Critico) | Desbloquear CONVERSA_PAR e remover stubs | Nenhuma |
| 02 | Fix Transicao de Fase | P0 (Critico) | warming_day, timestamp, criterios de grupos | Epic 01 |
| 03 | Pre-send Validation & Error Handling | P1 (Alto) | Circuit breaker, cooldown, retry, logging | Nenhuma |
| 04 | Chip Z-API Recovery | P1 (Alto) | Reconectar chip degradado, connection check z-api | Nenhuma |
| 05 | Observabilidade & Health Check | P2 (Medio) | /warmer/health, metricas estruturadas, daily summary | Epics 01-03 |

---

## Criterios de Sucesso

- [ ] CONVERSA_PAR com taxa de sucesso >90% (entre chips conectados)
- [ ] Pelo menos 1 chip transicionando de fase em 3 dias apos deploy
- [ ] warming_day calculado e atualizado automaticamente a cada ciclo
- [ ] Zero stubs agendados como atividades reais no scheduler
- [ ] Circuit breaker verificado antes de cada envio
- [ ] Health check endpoint /warmer/health retornando status real do pool
- [ ] Logs com stack trace completo em erros (exc_info=True)
- [ ] Todos os testes passando, cobertura >85% nos arquivos alterados

---

## Riscos

| Risco | Impacto | Mitigacao |
|-------|---------|-----------|
| Fix do pairing engine causa flood de mensagens | Chips enviam muitas msgs de uma vez | Respeitar limites por fase ja existentes (LIMITES_FASE) |
| Reconexao z-api falha | Chip principal continua offline | Priorizar chips Evolution que estao conectados |
| Relaxar criterios de grupo facilita chips fracos | Chips mal aquecidos chegam em operacao | Manter criterios rigorosos em trust_score e conversas_bidirecionais |
| Retry com backoff causa timeout no ciclo | Ciclo de 5 min ultrapassa janela | Limitar retry a 1 tentativa, timeout de 10s |

## Dependencias

| Epico | Depende de | Status |
|-------|-----------|--------|
| Epic 02 | Epic 01 (CONVERSA_PAR funcionando antes de validar transicao) | Pendente |
| Epic 05 | Epics 01-03 (sistema funcionando antes de monitorar) | Pendente |
| Epic 03 | Nenhuma (pode rodar em paralelo com Epic 01) | Pendente |
| Epic 04 | Nenhuma (pode rodar em paralelo) | Pendente |

---

## Ordem de Execucao

```
Epic 01 (P0 pairing + scheduler) ──→ Epic 02 (P0 transicao)
                                                    │
Epic 03 (P1 pre-send) ─────────────────────────────┤
                                                    │
Epic 04 (P1 z-api recovery) ───────────────────────┤
                                                    │
                                         Epic 05 (P2 observabilidade)
```

Epics 01, 03 e 04 sao independentes e podem rodar em paralelo.
Epic 02 depende de Epic 01.
Epic 05 roda por ultimo validando tudo.
