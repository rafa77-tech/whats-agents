# Sprint 55: NFR Improvements - Performance & Observability

## Objetivo

Implementar melhorias de performance no banco de dados e aprimorar o sistema de monitoramento do dashboard para detecção proativa de problemas.

## Contexto

Baseado no **NFR Assessment** realizado em 2026-02-09, foram identificadas oportunidades de melhoria em:
- **Performance:** 39 FKs sem índices causando JOINs lentos
- **Observability:** Dashboard de monitoramento existe mas falta alertas proativos

**Score atual do sistema:** 4.25/5 (excelente base, melhorias incrementais)

---

## Épicos

| # | Épico | Estimativa | Prioridade |
|---|-------|------------|------------|
| E01 | Índices em Foreign Keys | 2h | P0 |
| E02 | Alertas Proativos no Dashboard | 4h | P0 |
| E03 | Histórico de Incidentes | 3h | P1 |
| E04 | Documentação de Operação | 1h | P2 |

**Total estimado:** ~10h

---

## Critérios de Sucesso

- [ ] Todas as FKs de alto impacto têm índices criados
- [ ] Dashboard emite notificação sonora/visual quando status vira crítico
- [ ] Browser notifications funcionando para alertas críticos
- [ ] Histórico de incidentes acessível no dashboard
- [ ] Documentação de secrets rotation no runbook

---

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Criação de índices travar banco | Alto | Usar `CREATE INDEX CONCURRENTLY` |
| Browser notifications bloqueadas | Médio | Fallback para alerta sonoro + visual |
| Migration falhar em produção | Alto | Testar em branch primeiro, ter rollback |

---

## Dependências

| Épico | Depende de | Status |
|-------|-----------|--------|
| E01 | Nenhum | ✅ Pode iniciar |
| E02 | Nenhum | ✅ Pode iniciar |
| E03 | E02 (parcial) | ⏳ Aguarda hooks de estado |
| E04 | Nenhum | ✅ Pode iniciar |

---

## Épicos Detalhados

- [Epic 01: Índices em Foreign Keys](./epic-01-indices-fk.md)
- [Epic 02: Alertas Proativos no Dashboard](./epic-02-alertas-proativos.md)
- [Epic 03: Histórico de Incidentes](./epic-03-historico-incidentes.md)
- [Epic 04: Documentação de Operação](./epic-04-documentacao.md)

---

## Referências

- [NFR Assessment 2026-02-09](../../docs/auditorias/nfr-assessment-2026-02-09.md)
- [Health Center - Sprint 43](../sprint-43/)
- [Monitor Page - Sprint 42](../sprint-42/)
