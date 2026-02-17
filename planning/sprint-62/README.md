# Sprint 62 — Enterprise Testing & CI Standards

## Status: 📋 Planejada

**Inicio:** Pendente
**Estimativa:** 2 semanas

## Objetivo

Transformar o CI de decorativo em funcional, atingir cobertura enterprise nos modulos criticos, e estabelecer quality gates que impedem deploy de codigo quebrado.

**Origem:** Auditoria de cobertura e CI (2026-02-17) — CI backend 100% `continue-on-error`, cobertura nunca verificada, modulos Tier 1 com gaps criticos.

---

## Diagnostico

| Metrica | Valor Atual | Meta |
|---------|-------------|------|
| Backend CI blocking | 0 de 3 jobs | 3 de 3 |
| Backend coverage verificada no CI | Nao (--no-cov) | Sim, com threshold por tier |
| Testes falhando | 4 | 0 |
| Erros de lint (ruff) | 27 | 0 |
| Arquivos para formatar | 21 | 0 |
| Tier 1 coverage (estimada) | ~35% | >85% |
| Dashboard API routes testadas | 43 de 135 | +20 routes criticas |
| Dashboard API excluida do coverage | Sim | Nao (parcial) |

### Causas raiz

1. CI backend tem `continue-on-error: true` em lint, testes e formatter — nada bloqueia
2. Testes rodam com `--no-cov` — threshold de 45% nunca e verificado
3. Modulos Tier 1 (rate limiting, handoff flow, pipeline core, reserva de plantao) tem gaps criticos
4. Dashboard exclui `app/api/**` inteiro do coverage — 92 routes invisiveis
5. Nao existem markers pytest para separar unit/integration
6. Documentacao (CLAUDE.md) diz 70% mas configs dizem 40-45%

---

## Epicos

| # | Epico | Foco | Dependencias |
|---|-------|------|--------------|
| 01 | Fix & Unblock CI | Corrigir testes falhando, lint, e remover continue-on-error | Nenhuma |
| 02 | Tier 1 Coverage — Rate Limiting & Circuit Breaker | Cobertura >90% nos modulos de protecao | Epic 01 |
| 03 | Tier 1 Coverage — Handoff & Opt-out Flow | Cobertura >90% nos modulos de handoff | Epic 01 |
| 04 | Tier 1 Coverage — Message Pipeline Core | Cobertura >80% no pipeline de mensagens | Epic 01 |
| 05 | Tier 1 Coverage — Business Events & Reserva | Cobertura >80% nos modulos de negocios | Epic 01 |
| 06 | Dashboard API Coverage | Remover exclusao de app/api, testar routes criticas | Epic 01 |
| 07 | CI Hardening & Coverage Gates | Thresholds por modulo, markers pytest, doc alignment | Epics 02-06 |

---

## Criterios de Sucesso

- [ ] CI backend bloqueia merge em caso de falha de lint, testes ou coverage
- [ ] CI dashboard mantem gates existentes + inclui API routes no coverage
- [ ] Zero testes falhando em ambos os pipelines
- [ ] Modulos Tier 1 com >85% de cobertura de linhas
- [ ] Markers pytest definidos (unit, integration, e2e)
- [ ] CLAUDE.md alinhado com thresholds reais
- [ ] Nenhum `continue-on-error: true` residual nos jobs criticos

## Riscos

| Risco | Impacto | Mitigacao |
|-------|---------|-----------|
| Corrigir lint pode introduzir bugs (F821) | Alto | F821 sao bugs reais — corrigir com testes |
| Testes novos podem ser frageis (mocks demais) | Medio | Preferir contract tests nas fronteiras |
| Coverage threshold muito alto bloqueia desenvolvimento | Medio | Thresholds incrementais por tier |
| Testes de integracao lentos no CI | Baixo | Separar com markers, rodar em paralelo |

## Dependencias Externas

| Dependencia | Status |
|-------------|--------|
| GitHub Actions secrets (Supabase, etc) | Ja configurados |
| Redis no CI | Ja configurado como service |
| Nenhuma nova infra necessaria | - |

---

## Ordem de Execucao

```
Epic 01 (Fix & Unblock) ─────┬──> Epic 02 (Rate Limit + CB)
                              ├──> Epic 03 (Handoff + Opt-out)
                              ├──> Epic 04 (Pipeline Core)
                              ├──> Epic 05 (Events + Reserva)
                              └──> Epic 06 (Dashboard API)
                                        │
                              Todos ────>  Epic 07 (CI Hardening)
```

Epics 02-06 sao paralelizaveis apos Epic 01.
