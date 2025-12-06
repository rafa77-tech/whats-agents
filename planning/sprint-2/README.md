# Sprint 2: Vagas & Chatwoot

## Objetivo da Sprint

> **Júlia oferece vagas aos médicos e gestor consegue supervisionar/intervir via Chatwoot.**

Ao final desta sprint:
- Júlia busca e oferece vagas compatíveis
- Médico pode aceitar e reservar vaga
- Gestor vê todas as conversas no Chatwoot
- Gestor pode assumir conversa (handoff)

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Busca de vagas | Retorna vagas corretas |
| Reserva funciona | Vaga marcada no banco |
| Sincronização Chatwoot | Conversas visíveis |
| Handoff | Funciona em < 1 min |

---

## Epics

| Epic | Nome | Stories | Prioridade |
|------|------|---------|------------|
| E1 | [Sistema de Vagas](./epic-01-vagas.md) | 6 | P0 |
| E2 | [Integração Chatwoot](./epic-02-chatwoot.md) | 5 | P0 |
| E3 | [Sistema de Handoff](./epic-03-handoff.md) | 5 | P0 |

---

## Resumo das Stories

### Epic 1: Sistema de Vagas

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S2.E1.1 | Tool buscar_vagas_compativeis | 3h | 🔴 |
| S2.E1.2 | Tool reservar_plantao | 2h | 🔴 |
| S2.E1.3 | Verificar conflito dia/período | 1h | 🔴 |
| S2.E1.4 | Notificar gestor pós-reserva | 1h | 🔴 |
| S2.E1.5 | Integrar vagas no fluxo do agente | 2h | 🔴 |
| S2.E1.6 | Tool agendar_lembrete | 2h | 🔴 |

### Epic 2: Integração Chatwoot

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S2.E2.1 | Sincronizar conversas → Chatwoot | 3h | 🔴 |
| S2.E2.2 | Sincronizar mensagens → Chatwoot | 2h | 🔴 |
| S2.E2.3 | Criar contatos no Chatwoot | 1h | 🔴 |
| S2.E2.4 | Webhook labels do Chatwoot | 2h | 🔴 |
| S2.E2.5 | Testar fluxo completo Chatwoot | 1h | 🔴 |

### Epic 3: Sistema de Handoff

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S2.E3.1 | Detectar triggers automáticos | 2h | 🔴 |
| S2.E3.2 | Mensagem de transição | 1h | 🔴 |
| S2.E3.3 | Bloquear Júlia em conversa humana | 1h | 🔴 |
| S2.E3.4 | Registrar handoff no banco | 1h | 🔴 |
| S2.E3.5 | Notificar gestor no Slack | 1h | 🔴 |

---

## Definition of Done (Sprint)

- [ ] Médico pergunta sobre vaga → Júlia busca e oferece
- [ ] Médico aceita → Vaga reservada no banco
- [ ] Médico pede "fala comigo amanhã" → Lembrete agendado
- [ ] Todas as conversas aparecem no Chatwoot
- [ ] Todas as mensagens sincronizam em tempo real
- [ ] Label "humano" → Júlia para de responder
- [ ] Gestor é notificado de handoffs no Slack
- [ ] Rate limiting continua funcionando

---

## Teste de Aceitação

```
CENÁRIO: Oferta de Vaga
DADO que médico está conversando com Júlia
QUANDO ele diz "tenho interesse em plantão"
ENTÃO Júlia busca vagas compatíveis
E oferece uma vaga de forma natural
E médico pode aceitar ou recusar

CENÁRIO: Lembrete Solicitado
DADO que médico está conversando com Júlia
QUANDO ele diz "to em cirurgia, me manda msg amanhã às 10h"
ENTÃO Júlia confirma o agendamento
E lembrete é criado na fila
E no horário agendado, Júlia retoma a conversa

CENÁRIO: Handoff
DADO que conversa está no Chatwoot
QUANDO gestor adiciona label "humano"
ENTÃO Júlia para de responder
E gestor pode responder diretamente
```
