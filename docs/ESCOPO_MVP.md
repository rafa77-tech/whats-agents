# Escopo do MVP - Agente Júlia

Este documento define **exatamente** o que entra no MVP e o que fica para depois.

---

## Princípio Orientador

> **MVP = Mínimo para validar que Júlia consegue fechar plantões sem ser detectada como bot**

Não estamos construindo o produto final. Estamos construindo o suficiente para:
1. Provar que a abordagem funciona
2. Coletar dados para melhorar
3. Fechar alguns plantões reais

---

## Escopo: IN (Entra no MVP)

### Funcionalidades Core

| # | Funcionalidade | Descrição | Prioridade |
|---|----------------|-----------|------------|
| 1 | **Prospecção básica** | Enviar mensagem de abertura para médicos | P0 |
| 2 | **Responder mensagens** | Receber e responder via WhatsApp | P0 |
| 3 | **Persona Júlia** | Tom e estilo definidos no system prompt | P0 |
| 4 | **Ofertar 1 vaga** | Apresentar vaga compatível na conversa | P0 |
| 5 | **Handoff manual** | Gestor assume via Chatwoot | P0 |
| 6 | **Rate limiting** | Respeitar limites do WhatsApp | P0 |

### Funcionalidades de Suporte

| # | Funcionalidade | Descrição | Prioridade |
|---|----------------|-----------|------------|
| 7 | **Visualização Chatwoot** | Gestor vê conversas em tempo real | P0 |
| 8 | **Report diário Slack** | Métricas básicas 1x/dia | P1 |
| 9 | **Follow-up 1x** | Um follow-up após 48h sem resposta | P1 |
| 10 | **Memória básica** | Lembrar nome e especialidade | P1 |

### Integrações

| Integração | Escopo MVP |
|------------|------------|
| Evolution API | Enviar/receber mensagens, presença, digitando |
| Chatwoot | Visualizar conversas, labels para handoff |
| Supabase | Médicos, conversas, interações, vagas |
| Slack | Webhook para reports (1x/dia) |
| Claude API | Haiku para conversas |

### Dados

| Dado | Escopo MVP |
|------|------------|
| Médicos | 100 anestesistas (piloto) |
| Vagas | 10-20 vagas reais cadastradas manualmente |
| Hospitais | 3-5 hospitais da região |

---

## Escopo: OUT (Fica para Depois)

### Funcionalidades Adiadas

| # | Funcionalidade | Motivo | Fase |
|---|----------------|--------|------|
| 1 | Follow-ups múltiplos | Complexidade, validar primeiro se 1 funciona | 2 |
| 2 | Coleta de documentos | Foco em fechar primeiro | 2 |
| 3 | Negociação automática | Risco alto, gestor faz manualmente | 2 |
| 4 | Google Docs briefing | Complexidade de integração | 2 |
| 5 | Comandos Slack | Gestor usa Chatwoot por enquanto | 2 |
| 6 | Reports automáticos 4x/dia | 1 report diário suficiente | 2 |
| 7 | Modo gestor conversacional | Foco no médico primeiro | 2 |
| 8 | RAG/memória avançada | Memória simples funciona | 2 |
| 9 | Multi-especialidade | Foco só em anestesia | 2 |
| 10 | Campanhas automatizadas | Prospecção manual basta | 2 |

### Integrações Adiadas

| Integração | Motivo | Fase |
|------------|--------|------|
| Google Docs | Complexidade | 2 |
| Bitrix24 | Legado, não essencial | 3 |
| Twilio | Evolution suficiente | 3 |
| n8n workflows | Não precisa para MVP | 2 |

### Dados Adiados

| Dado | Motivo | Fase |
|------|--------|------|
| 1.660 médicos | Muito volume para MVP, risco de ban | 2 |
| Múltiplas especialidades | Foco em anestesia | 2 |
| Histórico de plantões | Não tem ainda | 2 |

---

## Definição de Pronto (MVP)

### Cenário de Uso Mínimo

```
1. Gestor cadastra vaga no Supabase
2. Gestor seleciona 10 médicos para contatar
3. Worker envia mensagens de abertura (respeitando rate limit)
4. Médico responde
5. Júlia conversa naturalmente
6. Júlia oferece vaga compatível
7. Se médico aceita: marca vaga como reservada, notifica gestor
8. Se médico recusa: agradece, encerra cordialmente
9. Se situação complexa: handoff para gestor
10. Gestor vê tudo no Chatwoot
11. No fim do dia: report básico no Slack
```

### Checklist de Entrega

**Infraestrutura:**
- [ ] FastAPI rodando
- [ ] Evolution API conectada
- [ ] Chatwoot sincronizado
- [ ] Supabase com dados básicos
- [ ] Slack webhook configurado

**Funcional:**
- [ ] Enviar mensagem de abertura
- [ ] Receber mensagem do médico
- [ ] Responder com persona Júlia
- [ ] Buscar vagas compatíveis
- [ ] Oferecer vaga naturalmente
- [ ] Reservar vaga quando aceita
- [ ] Handoff via label Chatwoot
- [ ] Report diário no Slack

**Dados:**
- [ ] 100 médicos importados
- [ ] 10+ vagas cadastradas
- [ ] 3+ hospitais cadastrados
- [ ] Especialidade anestesia configurada

**Qualidade:**
- [ ] 10 conversas de teste sem falhas
- [ ] Persona validada (não parece bot)
- [ ] Rate limiting funcionando
- [ ] Zero erros críticos por 24h

---

## User Stories do MVP

### US-01: Enviar Prospecção
```
Como gestor
Quero que Júlia envie mensagens de abertura para médicos selecionados
Para iniciar conversas de prospecção

Critérios de Aceite:
- [ ] Mensagens são únicas (não parecem template)
- [ ] Respeita rate limit (20/h, 100/dia)
- [ ] Só envia em horário comercial (08-20h, seg-sex)
- [ ] Salva interação no banco
- [ ] Atualiza stage do médico
```

### US-02: Responder Médico
```
Como médico
Quero receber respostas rápidas e naturais
Para ter uma boa experiência de conversa

Critérios de Aceite:
- [ ] Resposta em menos de 30 segundos
- [ ] Mostra "digitando" antes de responder
- [ ] Resposta contextualizada ao que eu disse
- [ ] Tom informal e amigável
- [ ] Não parece automático
```

### US-03: Oferecer Vaga
```
Como médico interessado
Quero receber ofertas de vagas compatíveis com meu perfil
Para encontrar plantões que me interessam

Critérios de Aceite:
- [ ] Vaga é da minha especialidade
- [ ] Apresentação é natural (não lista)
- [ ] Inclui: hospital, data, horário, valor
- [ ] Posso perguntar mais detalhes
- [ ] Posso aceitar ou recusar
```

### US-04: Aceitar Vaga
```
Como médico
Quero confirmar interesse em uma vaga
Para reservar o plantão

Critérios de Aceite:
- [ ] Júlia confirma a reserva
- [ ] Vaga é marcada como reservada no sistema
- [ ] Gestor é notificado
- [ ] Júlia me diz próximos passos
```

### US-05: Handoff para Humano
```
Como gestor
Quero assumir uma conversa quando necessário
Para resolver situações que Júlia não consegue

Critérios de Aceite:
- [ ] Adiciono label "humano" no Chatwoot
- [ ] Júlia para de responder
- [ ] Vejo todo o histórico da conversa
- [ ] Posso responder direto pelo Chatwoot
- [ ] Médico recebe minha resposta normalmente
```

### US-06: Ver Report Diário
```
Como gestor
Quero receber um resumo diário das atividades
Para acompanhar o desempenho da Júlia

Critérios de Aceite:
- [ ] Report chega no Slack às 20h
- [ ] Mostra: enviadas, respondidas, qualificados, fechados
- [ ] Lista plantões fechados no dia
- [ ] Lista handoffs que precisei fazer
```

### US-07: Monitorar Conversas
```
Como gestor
Quero ver todas as conversas em tempo real
Para acompanhar e intervir quando necessário

Critérios de Aceite:
- [ ] Chatwoot mostra todas as conversas
- [ ] Vejo mensagens do médico e da Júlia
- [ ] Vejo status (aberta, fechada, handoff)
- [ ] Posso filtrar por status
```

---

## Riscos do MVP

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Ban WhatsApp | Média | Alto | Rate limit conservador, warm-up lento |
| Detecção como bot | Média | Alto | Testes intensivos de persona |
| Médicos reclamam | Baixa | Alto | Opt-out fácil, tom respeitoso |
| Falha técnica | Média | Médio | Monitoramento, alertas |
| Gestor não consegue usar | Baixa | Médio | Treinamento, documentação |

---

## Cronograma Sugerido

| Semana | Foco | Entregável |
|--------|------|------------|
| 1 | Setup + Integração Evolution | Enviar/receber mensagens funcionando |
| 2 | Agente Júlia básico | Conversar com persona |
| 3 | Vagas + Chatwoot | Ofertar vagas, handoff |
| 4 | Testes internos | 20+ conversas simuladas |
| 5 | Piloto restrito | 10 médicos reais, monitorado |
| 6 | Ajustes + Expansão | 100 médicos, métricas |

---

## Decisões de Design

### Por que só 100 médicos?
- Menos risco de ban
- Mais controle para ajustes
- Dados suficientes para validar

### Por que só anestesia?
- Base de dados mais completa (81% com CRM)
- Conhecemos bem o mercado
- Menos variáveis

### Por que não coleta de documentos?
- Foco em validar conversa primeiro
- Coleta pode ser manual pós-aceite
- Adiciona complexidade prematura

### Por que não negociação automática?
- Risco alto de erro
- Gestor pode negociar manualmente
- Validar depois com dados reais

### Por que só 1 follow-up?
- Validar se follow-up funciona
- Menos spam para médicos
- Expandir baseado em dados

---

## Definição de Sucesso do MVP

> **MVP é sucesso se em 4 semanas:**
>
> 1. Júlia fechou pelo menos 3 plantões
> 2. Taxa de detecção como bot < 10%
> 3. Zero ban de WhatsApp
> 4. Gestor consegue operar com Chatwoot
> 5. Taxa de resposta > 20%

Se atingirmos isso, estamos prontos para Fase 2.
