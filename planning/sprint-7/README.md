# Sprint 7: Correção de Gaps MVP

## Objetivo

> **Corrigir todos os gaps identificados entre a documentação PRD e a implementação atual.**

Este sprint foi criado após análise detalhada da documentação (`CLAUDE.md`, `SPEC.md`, `FLUXOS.md`, `METRICAS_MVP.md`, `INTEGRACOES.md`) comparada com o código implementado.

---

## Gaps Identificados

| # | Gap | Prioridade | Impacto |
|---|-----|------------|---------|
| 1 | Tool `buscar_vagas` ausente | P0 | Júlia não consegue oferecer vagas proativamente |
| 2 | Handoff Humano→IA incompleto | P0 | Pode travar conversa no modo humano |
| 3 | Verificação conflito de vagas | P1 | Pode oferecer vaga em dia que médico já tem |
| 4 | Cadência de follow-ups | P1 | Timing pode não seguir 48h/5d/15d/60d |
| 5 | Reports múltiplos por dia | P1 | Gestor sem visibilidade em tempo real |
| 6 | Métrica detecção como bot | P2 | Sem visibilidade se médicos percebem IA |
| 7 | Briefing via Google Docs | P2 | Gestor não consegue configurar via doc |

---

## Épicos

| # | Épico | Stories | Status |
|---|-------|---------|--------|
| 01 | Tool buscar_vagas | 4 | Pendente |
| 02 | Handoff Humano→IA | 3 | Pendente |
| 03 | Verificação Conflito Vagas | 3 | Pendente |
| 04 | Follow-up Cadência | 4 | Pendente |
| 05 | Reports Múltiplos Slack | 3 | Pendente |
| 06 | Métrica Detecção Bot | 3 | Pendente |
| 07 | Briefing Google Docs | 5 | Pendente |

---

## Dependências

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORDEM DE IMPLEMENTAÇÃO                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  P0 (Críticos - fazer primeiro):                                │
│  ┌──────────────┐    ┌──────────────────┐                       │
│  │ Epic 01:     │    │ Epic 02:         │                       │
│  │ buscar_vagas │    │ Handoff Hum→IA   │                       │
│  └──────────────┘    └──────────────────┘                       │
│         │                    │                                   │
│         └────────┬───────────┘                                   │
│                  ▼                                               │
│  P1 (Importantes):                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Epic 03:     │  │ Epic 04:     │  │ Epic 05:     │          │
│  │ Conflito     │  │ Follow-up    │  │ Reports      │          │
│  │ Vagas        │  │ Cadência     │  │ Múltiplos    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                │                  │                    │
│         └────────┬───────┴──────────────────┘                   │
│                  ▼                                               │
│  P2 (Melhorias):                                                │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ Epic 06:     │  │ Epic 07:     │                             │
│  │ Métrica Bot  │  │ Google Docs  │                             │
│  └──────────────┘  └──────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Critérios de Saída do Sprint

- [ ] Tool `buscar_vagas` funcionando com LLM
- [ ] Handoff bidirecional (IA↔Humano) testado end-to-end
- [ ] Verificação de conflito impede ofertas duplicadas
- [ ] Follow-ups seguem cadência: 48h → 5d → 15d → pausa 60d
- [ ] Reports enviados em 4 horários (10h, 13h, 17h, 20h)
- [ ] Report semanal enviado segunda às 9h
- [ ] Detecção como bot registrada em métricas
- [ ] Briefing via Google Docs atualiza diretrizes automaticamente

---

## Arquivos a Modificar/Criar

| Arquivo | Ação | Épico |
|---------|------|-------|
| `app/tools/vagas.py` | Modificar | 01 |
| `app/services/vaga.py` | Modificar | 01, 03 |
| `app/services/llm.py` | Modificar | 01 |
| `app/api/routes/chatwoot.py` | Modificar | 02 |
| `app/services/handoff.py` | Modificar | 02 |
| `app/services/followup.py` | Modificar | 04 |
| `app/config/followup.py` | Modificar | 04 |
| `app/workers/scheduler.py` | Modificar | 05 |
| `app/services/relatorio.py` | Modificar | 05 |
| `app/services/metricas.py` | Modificar | 06 |
| `app/services/handoff_detector.py` | Modificar | 06 |
| `app/services/briefing.py` | Criar | 07 |
| `app/workers/briefing_worker.py` | Criar | 07 |

---

## Estimativas

| Épico | Complexidade | Horas Estimadas |
|-------|--------------|-----------------|
| 01 | Alta | 4h |
| 02 | Média | 2h |
| 03 | Baixa | 1h |
| 04 | Média | 2h |
| 05 | Média | 2h |
| 06 | Baixa | 1h |
| 07 | Alta | 6h |
| **Total** | - | **~18h** |
