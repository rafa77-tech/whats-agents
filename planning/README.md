# Planejamento - Agente Júlia

Este diretório contém o planejamento completo do projeto organizado em **Sprints**, **Epics** e **Stories**.

---

## Estrutura

```
/planning
├── README.md                    ← Você está aqui
├── sprint-0/                    ← Setup & Configuração
│   ├── README.md
│   ├── epic-01-integracoes.md
│   ├── epic-02-dados.md
│   └── epic-03-estrutura.md
├── sprint-1/                    ← Core do Agente
│   ├── README.md
│   ├── epic-01-webhook.md
│   ├── epic-02-agente.md
│   └── epic-03-seguranca.md
├── sprint-2/                    ← Vagas & Chatwoot
│   ├── README.md
│   ├── epic-01-vagas.md
│   ├── epic-02-chatwoot.md
│   └── epic-03-handoff.md
├── sprint-3/                    ← Testes & Ajustes
│   ├── README.md
│   ├── epic-01-persona.md
│   ├── epic-02-timing.md
│   └── epic-03-edge-cases.md
├── sprint-4/                    ← Piloto Restrito
│   ├── README.md
│   ├── epic-01-metricas.md
│   ├── epic-02-feedback.md
│   └── epic-03-piloto.md
└── sprint-5/                    ← Expansão
    ├── README.md
    ├── epic-01-especialidades.md
    ├── epic-02-campanhas.md
    └── epic-03-escalabilidade.md
```

---

## Roadmap Completo

> Para o roadmap atualizado com status de todas as sprints, ver **CLAUDE.md**.

### Sprints Iniciais (MVP)

| Sprint | Nome | Status |
|--------|------|--------|
| 0 | Setup & Configuração | ✅ Completa |
| 1 | Core do Agente | ✅ Completa |
| 2 | Vagas & Chatwoot | ✅ Completa |
| 3 | Testes & Ajustes | ✅ Completa |
| 4 | Piloto Restrito | ✅ Completa |
| 5 | Expansão | ✅ Completa |

### Sprints de Evolução (6-18)

| Sprint | Nome | Status |
|--------|------|--------|
| 6 | Multi-instância WhatsApp | ✅ Completa |
| 7 | Briefing Google Docs | ✅ Completa |
| 8 | Memória & Pipeline | ✅ Completa |
| 9 | Julia no Slack (NLP) | ✅ Completa |
| 10 | Refatoração e Dívida Técnica | ✅ Completa |
| 11 | Briefing Conversacional | ✅ Completa |
| 12 | Deploy Produção | 📋 Planejado |
| 13 | Conhecimento Dinâmico (RAG) | ✅ Completa |
| 14 | Pipeline de Grupos WhatsApp | ✅ Completa |
| 15 | Policy Engine (Estado + Decisão) | ✅ Completa |
| 16 | Confirmação de Plantão | ✅ Completa |
| 17 | Business Events e Funil | ✅ Completa |
| 18 | Auditoria e Integridade | ✅ Completa |

### Sprints Avançadas (25-33)

| Sprint | Nome | Status |
|--------|------|--------|
| 25 | Julia Warmer (Foundation) | ✅ Completa |
| 26 | Multi-Julia Orchestration | ✅ Completa |
| 27 | Chip Activator (VPS) | 🔄 Em Andamento |
| 28 | Dashboard Julia | ✅ Completa |
| 29 | Conversation Mode | ✅ Completa |
| 30 | Refatoração Arquitetural | 🔄 Em Andamento |

### Sprints Recentes (40+)

| Sprint | Nome | Status |
|--------|------|--------|
| 40 | Chips Dashboard | ✅ Completa |
| 41 | Chips Ops & Health | ✅ Completa |
| 42 | Monitor Jobs | ✅ Completa |
| 43 | UX & Operacao Unificada | 📋 Planejado |
| 44 | Correcoes Arquiteturais | ✅ Completa |
| 45 | Arquitetura da Informacao & Navegacao | 📋 Planejado |

> **Nota:** Sprints 19-24 e 31-33 estão em planejamento futuro.

---

## Como Usar Este Planejamento

### Para Tech Lead / PM

1. Acesse a sprint atual
2. Revise o README da sprint para entender o objetivo
3. Distribua as stories entre os devs
4. Acompanhe o DoD de cada story

### Para Desenvolvedores

1. Receba a story atribuída
2. Leia **todo** o documento da story antes de começar
3. Entenda o **Objetivo** - por que estamos fazendo isso
4. Siga as **Tarefas** na ordem
5. Valide usando o **Como Testar**
6. Marque o **DoD** item por item
7. Só considere pronto quando **todos** os itens do DoD estiverem ✅

### Formato das Stories

Cada story segue este formato:

```markdown
# [ID] Título da Story

## Objetivo
Por que estamos fazendo isso e qual o resultado esperado.

## Contexto
O que você precisa saber antes de começar.

## Pré-requisitos
- O que precisa estar pronto antes

## Tarefas
1. Passo a passo detalhado
2. Com código de exemplo quando aplicável
3. Cada passo é verificável

## Como Testar
Comandos e passos para validar que funcionou.

## DoD (Definition of Done)
- [ ] Item verificável 1
- [ ] Item verificável 2
- [ ] Código commitado
- [ ] Testado localmente
```

---

## Convenções

### IDs das Stories

Formato: `S{sprint}.E{epic}.{story}`

Exemplos:
- `S0.E1.1` = Sprint 0, Epic 1, Story 1
- `S1.E2.3` = Sprint 1, Epic 2, Story 3

### Status

| Status | Significado |
|--------|-------------|
| 🔴 Não iniciada | Ainda não começou |
| 🟡 Em progresso | Dev trabalhando |
| 🟢 Concluída | DoD completo |
| ⚫ Bloqueada | Esperando dependência |

### Prioridades

| Prioridade | Significado |
|------------|-------------|
| P0 | Bloqueante - fazer primeiro |
| P1 | Alta - fazer na sprint |
| P2 | Média - fazer se der tempo |

---

## Dependências Entre Sprints

```
Sprint 0 (Setup)
    │
    ├── [API Key Anthropic] ─────┐
    ├── [WhatsApp Conectado] ────┼──▶ Sprint 1 (Core)
    └── [Chatwoot Config] ───────┘         │
                                           │
Sprint 0 (Dados)                           │
    │                                      │
    ├── [Hospitais] ─────────────┐         │
    └── [Vagas] ─────────────────┼──▶ Sprint 2 (Vagas)
                                 │         │
                    Sprint 1 ────┘         │
                                           ▼
                                    Sprint 3 (Testes)
                                           │
                                           ▼
                                    Sprint 4 (Piloto)
                                           │
                                           ▼
                                    Sprint 5 (Expansão)
```

---

## Critérios de Aceite por Sprint

### Sprint 0
- [ ] Todas as APIs respondem (curl funciona)
- [ ] Dados básicos no Supabase
- [ ] Estrutura do projeto criada

### Sprint 1
- [ ] Enviar "oi" no WhatsApp → receber resposta
- [ ] Conversa salva no banco
- [ ] Histórico persistido

### Sprint 2
- [ ] Médico aceita vaga → reserva no banco
- [ ] Gestor vê conversa no Chatwoot
- [ ] Label "humano" → Júlia para

### Sprint 3
- [ ] 50+ cenários testados
- [ ] Equipe interna aprova persona
- [ ] 0 detecções como bot

### Sprint 4
- [ ] 100 médicos contactados
- [ ] Taxa resposta > 30%
- [ ] Sistema de métricas funcionando
- [ ] Feedback do gestor implementado

### Sprint 5
- [ ] 1000+ médicos na base
- [ ] 5+ especialidades suportadas
- [ ] Campanhas automatizadas
- [ ] Sistema escalável e documentado

---

## Links Úteis

| Recurso | Local |
|---------|-------|
| Fonte única de verdade | `/CLAUDE.md` |
| Arquitetura geral | `/docs/arquitetura/visao-geral.md` |
| Schema do banco | `/docs/arquitetura/banco-de-dados.md` |
| Convenções de código | `/app/CONVENTIONS.md` |
| Integrações | `/docs/integracoes/README.md` |
| Runbook operacional | `/docs/operacao/runbook.md` |

---

## Começando

Para novos desenvolvedores:
1. Leia o [CLAUDE.md](/CLAUDE.md) para entender o projeto
2. Siga o [Setup Local](/docs/setup/setup.md)
3. Consulte a sprint atual para tarefas pendentes
