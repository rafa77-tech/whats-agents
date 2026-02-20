# Sprint 64 — Conversas Extreme Makeover

## Status: 📋 Planejada

**Inicio:** 2026-02-19
**Estimativa:** 2 semanas

## Objetivo

Transformar a pagina /conversas de um chat generico quebrado em um **painel de supervisao funcional** da Julia — corrigindo bugs criticos (conversas de chips nao aparecendo, mobile quebrado), eliminando problemas de performance (queries N+1, polling duplo), e redesenhando a UX para o caso de uso real: **supervisao de agente autonomo**.

**Origem:** Avaliacao profunda de UX (2026-02-19) — 16 problemas identificados em 4 categorias (bugs criticos, performance, UX, dados).

---

## Diagnostico

| Metrica | Valor Atual | Meta |
|---------|-------------|------|
| Conversas visiveis por chip | Parcial (pre-Sprint 26 ausentes) | 100% |
| Mobile funcional | Nao (chat hidden) | Sim |
| Sinais visuais por card sidebar | 13+ | 5-6 |
| Tab "Atencao" com motivo | Nao | Sim |
| Resumo de conversa | Nao existe | Sim |
| Polling duplicado | Sim (SSE + setInterval) | Nao |
| Query last_message | N+1 (todas interacoes) | 1 por conversa |
| unread_count | Hardcoded 0 | Real |
| Context panel | xl only (1280px+) | lg (1024px+) |
| NotesSection bug | useState ao inves de useEffect | Corrigido |
| Feedback parseInt(UUID) | NaN | ID correto |
| Contagem "Aguardando" | Chuta 30% | Real (SQL) |

---

## Epicos

| # | Epico | Prioridade | Foco | Dependencias |
|---|-------|-----------|------|--------------|
| 01 | Fix Data Layer (Bugs Criticos) | P0 | Backfill conversation_chips, queries quebradas, bugs de codigo | Nenhuma |
| 02 | Performance & Real-Time | P1 | Polling duplo, query N+1, categorização server-side, SWR migration | Epic 01 |
| 03 | Mobile & Responsividade | P1 | Navegacao mobile, context panel responsivo | Nenhuma |
| 04 | UX Redesign: Sidebar & Triagem | P2 | Simplificar cards, tab "Atencao" com motivos, novo layout | Epics 01-02 |
| 05 | UX Redesign: Chat Panel & Contexto | P2 | Resumo de conversa, context panel melhorado | Epics 01-02 |
| 06 | Testes & Validacao | P1 | Testes para todos os epicos, regressao, E2E | Epics 01-05 |

---

## Criterios de Sucesso

- [ ] Todas as conversas de todos os chips visiveis (filtro por chip e "Todos")
- [ ] Mobile funcional: navegar lista → conversa → voltar
- [ ] Zero polling duplicado
- [ ] Queries otimizadas (last_message via lateral join ou subquery, nao N+1)
- [ ] Tab "Atencao" mostra motivo claro para cada conversa
- [ ] Card da sidebar com max 6 sinais visuais
- [ ] Context panel acessivel em telas >= 1024px
- [ ] NotesSection recarrega ao trocar conversa
- [ ] Feedback de mensagens funcional com qualquer tipo de ID
- [ ] Contagens reais (nao estimadas) em todas as tabs
- [ ] unread_count calculado de verdade
- [ ] Testes cobrindo todos os fixes (cobertura >= 80% nos componentes alterados)

---

## Riscos

| Risco | Impacto | Mitigacao |
|-------|---------|-----------|
| Backfill conversation_chips para conversas antigas sem instance_id | Conversas ficam sem chip associado | Usar instance_id da tabela conversations como fallback |
| Mudanca de layout quebra uso existente | Supervisor acostumado perde referencia | Manter mesmas cores/icones, mudar layout nao semantica |
| Migration SQL em producao | Downtime ou lock na tabela conversations | Backfill via batch (1000 por vez), sem DDL blocking |
| RPC get_supervision_tab_counts nao existe | Contagem cai no fallback que chuta | Criar RPC ou fazer query otimizada no route |

## Dependencias

| Epico | Depende de | Status |
|-------|-----------|--------|
| Epic 02 | Epic 01 (dados corretos antes de otimizar) | Pendente |
| Epic 04 | Epics 01-02 (dados e performance ok antes de redesign) | Pendente |
| Epic 05 | Epics 01-02 (idem) | Pendente |
| Epic 06 | Epics 01-05 (testar tudo junto) | Pendente |
| Epic 03 | Nenhuma (pode rodar em paralelo) | Pendente |

---

## Ordem de Execucao

```
Epic 01 (P0 bugs) ──────────┐
                              ├──→ Epic 02 (performance) ──→ Epic 04 (UX sidebar)
Epic 03 (mobile) ────────────┤                           ──→ Epic 05 (UX chat)
                              │
                              └──────────────────────────────→ Epic 06 (testes)
```

Epic 01 e Epic 03 sao independentes e podem rodar em paralelo.
Epics 04 e 05 podem rodar em paralelo apos Epic 02.
Epic 06 roda por ultimo validando tudo.
