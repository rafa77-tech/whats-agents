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

## Visão Geral das Sprints

| Sprint | Nome | Objetivo | Stories |
|--------|------|----------|---------|
| 0 | Setup & Configuração | Todas as integrações funcionando | 17 |
| 1 | Core do Agente | Júlia responde mensagens | 15 |
| 2 | Vagas & Chatwoot | Ofertar vagas, handoff funciona | 16 |
| 3 | Testes & Ajustes | Persona validada, equipe aprova | 14 |
| 4 | Piloto Restrito | 100 médicos reais, métricas | 14 |
| 5 | Expansão | 1000+ médicos, múltiplas especialidades | 13 |

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
| Documentação técnica | `/docs/TECHNICAL.md` |
| Schema do banco | `/docs/DATABASE.md` |
| Persona Júlia | `/CLAUDE.md` |
| Fluxos de negócio | `/docs/FLUXOS.md` |
| Estratégia de testes | `/docs/ESTRATEGIA_TESTES.md` |

---

## Começando

**Próximo passo:** Acesse [Sprint 0](./sprint-0/README.md) para começar.
