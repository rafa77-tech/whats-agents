# Sprint 1: Core do Agente

## Objetivo da Sprint

> **Júlia consegue receber uma mensagem no WhatsApp e responder com a persona correta.**

Ao final desta sprint, você poderá:
- Enviar "Oi" no WhatsApp para o número da Júlia
- Receber uma resposta informal e natural
- Ver a conversa salva no banco de dados

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Webhook funcionando | 100% |
| Tempo de resposta | < 30 segundos |
| Persona correta | Resposta informal |
| Dados persistidos | Conversa e interações salvas |

---

## Epics

| Epic | Nome | Stories | Prioridade |
|------|------|---------|------------|
| E1 | [Webhook & Recebimento](./epic-01-webhook.md) | 5 | P0 |
| E2 | [Agente Júlia](./epic-02-agente.md) | 7 | P0 |
| E3 | [Segurança & Resiliência](./epic-03-seguranca.md) | 3 | P0 |

---

## Resumo das Stories

### Epic 1: Webhook & Recebimento

| ID | Story | Estimativa | Dependência | Status |
|----|-------|------------|-------------|--------|
| S1.E1.1 | Criar endpoint webhook Evolution | 2h | Sprint 0 | 🔴 |
| S1.E1.2 | Parser de mensagens recebidas | 1h | S1.E1.1 | 🔴 |
| S1.E1.3 | Marcar como lida + presença online | 1h | S1.E1.2 | 🔴 |
| S1.E1.4 | Mostrar "digitando" | 30min | S1.E1.3 | 🔴 |
| S1.E1.5 | Ignorar mensagens próprias e grupos | 1h | S1.E1.2 | 🔴 |

### Epic 2: Agente Júlia

| ID | Story | Estimativa | Dependência | Status |
|----|-------|------------|-------------|--------|
| S1.E2.1 | System prompt completo da Júlia | 3h | - | 🔴 |
| S1.E2.2 | Buscar/criar médico no banco | 1h | S1.E1.2 | 🔴 |
| S1.E2.3 | Buscar/criar conversa | 1h | S1.E2.2 | 🔴 |
| S1.E2.4 | Carregar histórico recente | 1h | S1.E2.3 | 🔴 |
| S1.E2.5 | Montar contexto para LLM | 2h | S1.E2.4 | 🔴 |
| S1.E2.6 | Chamar Claude e processar resposta | 2h | S1.E2.1, S1.E2.5 | 🔴 |
| S1.E2.7 | Enviar resposta e salvar interação | 1h | S1.E2.6 | 🔴 |

### Epic 3: Segurança & Resiliência

| ID | Story | Estimativa | Dependência | Status |
|----|-------|------------|-------------|--------|
| S1.E3.1 | Rate Limiting | 3h | S1.E2.7 | 🔴 |
| S1.E3.2 | Circuit Breaker | 2h | S1.E1.1 | 🔴 |
| S1.E3.3 | Opt-out Imediato | 2h | S1.E2.7 | 🔴 |

---

## Fluxo Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUXO: MÉDICO → JÚLIA                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MÉDICO              WHATSAPP          EVOLUTION         FASTAPI             │
│    │                    │                 │                 │                │
│    │  1. Envia "Oi"     │                 │                 │                │
│    │───────────────────▶│                 │                 │                │
│    │                    │────────────────▶│                 │                │
│    │                    │                 │───webhook──────▶│                │
│    │                    │                 │                 │                │
│    │                    │                 │                 │  2. Parser     │
│    │                    │                 │                 │  3. Mark read  │
│    │                    │                 │◀──presence──────│  4. Online     │
│    │◀───"online"────────│◀────────────────│                 │                │
│    │                    │                 │◀──composing─────│  5. Digitando  │
│    │◀───"digitando"─────│◀────────────────│                 │                │
│    │                    │                 │                 │                │
│    │                    │                 │                 │  6. Busca/cria │
│    │                    │                 │                 │     médico     │
│    │                    │                 │                 │  7. Busca/cria │
│    │                    │                 │                 │     conversa   │
│    │                    │                 │                 │  8. Carrega    │
│    │                    │                 │                 │     histórico  │
│    │                    │                 │                 │  9. Chama LLM  │
│    │                    │                 │                 │                │
│    │                    │                 │◀──send msg──────│  10. Resposta  │
│    │                    │◀────────────────│                 │                │
│    │◀───"Oi! Tudo..."───│                 │                 │  11. Salva     │
│    │                    │                 │                 │      interação │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Ordem de Execução

```
Dia 1:
├── S1.E2.1 - System prompt (pode começar em paralelo)
├── S1.E1.1 - Endpoint webhook
├── S1.E1.2 - Parser mensagens
└── S1.E1.5 - Filtrar msgs próprias/grupos

Dia 2:
├── S1.E1.3 - Mark read + presença
├── S1.E1.4 - Digitando
├── S1.E2.2 - Buscar/criar médico
└── S1.E2.3 - Buscar/criar conversa

Dia 3:
├── S1.E2.4 - Carregar histórico
├── S1.E2.5 - Montar contexto
├── S1.E2.6 - Chamar Claude
└── S1.E2.7 - Enviar resposta

Dia 4-5:
└── Testes e ajustes
```

---

## Definition of Done (Sprint)

A sprint só está completa quando:

- [ ] Webhook recebe mensagens da Evolution
- [ ] Mensagens próprias e de grupos são ignoradas
- [ ] Médico vê "online" e "digitando" antes da resposta
- [ ] Resposta é gerada pelo Claude com persona Júlia
- [ ] Resposta é enviada via WhatsApp
- [ ] Conversa e interações salvas no Supabase
- [ ] Tempo total < 30 segundos
- [ ] Rate limiting ativo (20/hora, 100/dia)
- [ ] Opt-out detectado e respeitado imediatamente
- [ ] Circuit breakers protegem serviços externos

---

## Teste de Aceitação

```
DADO que tenho o número da Júlia salvo
QUANDO eu envio "Oi, tudo bem?"
ENTÃO eu vejo "online" no status
E eu vejo "digitando..."
E eu recebo uma resposta informal em até 30 segundos
E a resposta usa "vc", "pra", "tá" ou similares
E a resposta tem no máximo 3 linhas
```

---

## Próximos Passos

1. Comece pelo [Epic 1: Webhook](./epic-01-webhook.md)
2. Em paralelo, trabalhe no [Epic 2: System Prompt](./epic-02-agente.md#s1e21)
3. Integre tudo ao final
