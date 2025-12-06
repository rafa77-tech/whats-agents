# Planejamento de Sprints - Agente Júlia

Organização das tarefas em sprints semanais para o MVP.

---

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ROADMAP MVP - 6 SPRINTS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Sprint 0       Sprint 1       Sprint 2       Sprint 3       Sprint 4-5     │
│  Setup          Core           Vagas          Testes         Piloto         │
│                                                                              │
│  • Config       • FastAPI      • Buscar       • Sandbox      • 10 médicos   │
│  • APIs         • Webhook      • Ofertar      • Equipe       • 100 médicos  │
│  • Testes       • Agente       • Reservar     • Ajustes      • Métricas     │
│    manuais        básico       • Handoff                                     │
│                                • Chatwoot                                    │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Semana 1       Semana 2       Semana 3       Semana 4       Semana 5-6     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Sprint 0: Setup & Configuração (Semana 1)

### Objetivo
Configurar todas as integrações e validar que funcionam antes de escrever código.

### Tarefas

#### Integrações (Bloqueantes)

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 0.1 | Obter API key Anthropic | Gestor | - | 30min |
| 0.2 | Testar chamada Claude API | Dev | 0.1 | 1h |
| 0.3 | Conectar número WhatsApp na Evolution | Gestor | - | 30min |
| 0.4 | Testar envio/recebimento Evolution | Dev | 0.3 | 1h |
| 0.5 | Criar conta admin Chatwoot | Gestor | - | 30min |
| 0.6 | Criar inbox WhatsApp no Chatwoot | Dev | 0.5 | 1h |
| 0.7 | Criar webhook Slack | Gestor | - | 30min |
| 0.8 | Testar envio mensagem Slack | Dev | 0.7 | 30min |

#### Dados (Paralelo)

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 0.9 | Seed especialidades/setores/periodos | Dev | - | 1h |
| 0.10 | Cadastrar 3-5 hospitais | Gestor | 0.9 | 1h |
| 0.11 | Cadastrar 10-20 vagas reais | Gestor | 0.10 | 2h |
| 0.12 | Selecionar 100 médicos piloto | Dev | - | 1h |

#### Estrutura Projeto (Paralelo)

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 0.13 | Criar estrutura FastAPI base | Dev | - | 2h |
| 0.14 | Configurar .env com todas as vars | Dev | 0.1-0.8 | 30min |
| 0.15 | Criar cliente Supabase | Dev | - | 1h |
| 0.16 | Criar cliente Anthropic | Dev | 0.1 | 1h |

### Entregáveis
- [ ] Todas as APIs funcionando (testes manuais OK)
- [ ] Dados básicos no Supabase
- [ ] Estrutura do projeto criada
- [ ] .env completo

### Critério de Saída
- [ ] `curl` para Evolution envia mensagem
- [ ] `curl` para Claude retorna resposta
- [ ] Slack recebe notificação
- [ ] Chatwoot mostra inbox

---

## Sprint 1: Core do Agente (Semana 2)

### Objetivo
Júlia consegue receber uma mensagem e responder com a persona correta.

### Tarefas

#### Webhook & Recebimento

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 1.1 | Endpoint webhook Evolution | Dev | 0.4 | 2h |
| 1.2 | Parser de mensagens recebidas | Dev | 1.1 | 1h |
| 1.3 | Marcar como lida + presença online | Dev | 1.2 | 1h |
| 1.4 | Mostrar "digitando" | Dev | 1.3 | 30min |

#### Agente Júlia

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 1.5 | System prompt da Júlia | Dev | - | 3h |
| 1.6 | Buscar/criar médico no banco | Dev | 1.2 | 1h |
| 1.7 | Buscar/criar conversa | Dev | 1.6 | 1h |
| 1.8 | Carregar histórico recente | Dev | 1.7 | 1h |
| 1.9 | Chamar Claude com contexto | Dev | 1.5, 1.8 | 2h |
| 1.10 | Enviar resposta via Evolution | Dev | 1.9 | 1h |

#### Persistência

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 1.11 | Salvar mensagem recebida | Dev | 1.2 | 1h |
| 1.12 | Salvar resposta enviada | Dev | 1.10 | 1h |
| 1.13 | Atualizar stage do médico | Dev | 1.10 | 30min |

### Entregáveis
- [ ] Webhook funcionando
- [ ] Júlia responde mensagens
- [ ] Histórico salvo no banco

### Critério de Saída
- [ ] Enviar "oi" pelo WhatsApp → receber resposta natural
- [ ] Conversa aparece na tabela `conversations`
- [ ] Mensagens aparecem em `interacoes`

---

## Sprint 2: Vagas & Chatwoot (Semana 3)

### Objetivo
Júlia oferece vagas e gestor consegue monitorar/intervir.

### Tarefas

#### Sistema de Vagas

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 2.1 | Tool: buscar_vagas_compativeis | Dev | - | 3h |
| 2.2 | Tool: reservar_plantao | Dev | 2.1 | 2h |
| 2.3 | Verificar conflito dia/período | Dev | 2.2 | 1h |
| 2.4 | Notificar gestor pós-reserva | Dev | 2.2 | 1h |

#### Integração Chatwoot

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 2.5 | Sincronizar conversas → Chatwoot | Dev | - | 3h |
| 2.6 | Sincronizar mensagens → Chatwoot | Dev | 2.5 | 2h |
| 2.7 | Webhook labels Chatwoot | Dev | 2.6 | 2h |
| 2.8 | Detectar label "humano" → handoff | Dev | 2.7 | 1h |

#### Sistema de Handoff

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 2.9 | Triggers automáticos de handoff | Dev | - | 2h |
| 2.10 | Mensagem de transição | Dev | 2.9 | 1h |
| 2.11 | Bloquear Júlia em conversa humana | Dev | 2.10 | 1h |
| 2.12 | Registrar handoff no banco | Dev | 2.11 | 1h |
| 2.13 | Notificar gestor Slack | Dev | 2.12 | 1h |

#### Rate Limiting

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 2.14 | Controle msgs/hora | Dev | - | 2h |
| 2.15 | Controle horário comercial | Dev | 2.14 | 1h |
| 2.16 | Fila de mensagens | Dev | 2.15 | 2h |

### Entregáveis
- [ ] Júlia oferece vagas
- [ ] Reserva funciona
- [ ] Chatwoot sincronizado
- [ ] Handoff funciona

### Critério de Saída
- [ ] Médico aceita vaga → vaga reservada no banco
- [ ] Gestor vê conversa no Chatwoot
- [ ] Gestor adiciona label "humano" → Júlia para

---

## Sprint 3: Testes & Ajustes (Semana 4)

### Objetivo
Validar persona e corrigir problemas antes de médicos reais.

### Tarefas

#### Fase 0: Sandbox

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 3.1 | Script de teste de persona | Dev | - | 2h |
| 3.2 | 50+ cenários de teste | Dev | 3.1 | 4h |
| 3.3 | Validar: tom, tamanho, abreviações | Dev | 3.2 | 2h |
| 3.4 | Ajustar system prompt | Dev | 3.3 | 2h |

#### Fase 1: Equipe Interna

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 3.5 | Conectar número de teste | Gestor | - | 30min |
| 3.6 | Briefing equipe interna | Gestor | - | 1h |
| 3.7 | 5-10 pessoas testam (3-5 dias) | Equipe | 3.6 | - |
| 3.8 | Coletar feedback | Dev | 3.7 | 2h |
| 3.9 | Ajustes baseados no feedback | Dev | 3.8 | 4h |

#### Funcionalidades Complementares

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 3.10 | Report diário Slack | Dev | - | 3h |
| 3.11 | Follow-up após 48h | Dev | - | 3h |
| 3.12 | Memória básica (nome, esp) | Dev | - | 2h |

### Entregáveis
- [ ] Persona validada pela equipe
- [ ] Report diário funcionando
- [ ] Follow-up funcionando
- [ ] Zero erros críticos por 48h

### Critério de Saída
- [ ] Equipe aprova: "parece humano"
- [ ] 0% de detecção como bot nos testes
- [ ] Todos os fluxos testados sem erro

---

## Sprint 4: Piloto Restrito (Semana 5)

### Objetivo
Testar com 10 médicos reais em ambiente controlado.

### Tarefas

#### Preparação

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 4.1 | Selecionar 10 médicos beta | Gestor | - | 1h |
| 4.2 | Configurar rate limit conservador | Dev | - | 1h |
| 4.3 | Preparar protocolo de monitoramento | Dev | - | 1h |
| 4.4 | Definir critérios de pausa | Dev | - | 1h |

#### Execução (Semana 1)

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 4.5 | Dia 1-2: 5 médicos, 1 msg cada | Dev | 4.1-4.4 | - |
| 4.6 | Dia 3-4: +5 médicos (10 total) | Dev | 4.5 | - |
| 4.7 | Dia 5: Análise de respostas | Dev | 4.6 | 2h |
| 4.8 | Ajustes se necessário | Dev | 4.7 | 4h |

#### Execução (Semana 2)

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 4.9 | Expandir para 20 médicos | Dev | 4.8 | - |
| 4.10 | Follow-ups para quem não respondeu | Dev | 4.9 | - |
| 4.11 | Ofertas de vagas | Dev | 4.10 | - |
| 4.12 | Análise final do piloto | Dev | 4.11 | 3h |

### Entregáveis
- [ ] 10-20 médicos contatados
- [ ] Métricas do piloto coletadas
- [ ] Pelo menos 1 vaga fechada (meta)

### Critério de Saída
- [ ] Taxa de resposta > 15%
- [ ] 0 detecções como bot
- [ ] 0 reclamações
- [ ] 2 semanas sem incidentes

---

## Sprint 5: Expansão (Semana 6)

### Objetivo
Escalar para 100 médicos com métricas consolidadas.

### Tarefas

| # | Tarefa | Responsável | Dependência | Estimativa |
|---|--------|-------------|-------------|------------|
| 5.1 | Aumentar para 100 médicos | Dev | Sprint 4 OK | 1h |
| 5.2 | Ajustar rate limit (20/dia) | Dev | 5.1 | 30min |
| 5.3 | Monitoramento contínuo | Dev | 5.2 | contínuo |
| 5.4 | Dashboard de métricas | Dev | - | 4h |
| 5.5 | Análise semanal | Dev | 5.4 | 2h |
| 5.6 | Documentar aprendizados | Dev | 5.5 | 2h |

### Entregáveis
- [ ] 100 médicos na base ativa
- [ ] Dashboard funcionando
- [ ] Documentação de aprendizados

### Critério de Saída (MVP Completo)
- [ ] 3+ plantões fechados
- [ ] Taxa detecção bot < 10%
- [ ] Zero ban WhatsApp
- [ ] Taxa resposta > 20%
- [ ] Gestor opera independente

---

## Dependências Críticas

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GRAFO DE DEPENDÊNCIAS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [API Key Anthropic] ──────┐                                                │
│                            │                                                │
│  [Número WhatsApp] ────────┼──▶ [Sprint 1: Core] ──▶ [Sprint 2: Vagas]     │
│                            │                              │                 │
│  [Chatwoot Config] ────────┘                              │                 │
│                                                           ▼                 │
│  [Dados: Hospitais] ──────────────────────────────▶ [Sprint 2: Vagas]      │
│                                                           │                 │
│  [Dados: Vagas] ──────────────────────────────────▶ [Sprint 2: Vagas]      │
│                                                           │                 │
│                                                           ▼                 │
│                                                  [Sprint 3: Testes]         │
│                                                           │                 │
│                                                           ▼                 │
│                                                  [Sprint 4: Piloto]         │
│                                                           │                 │
│                                                           ▼                 │
│                                                  [Sprint 5: Expansão]       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Bloqueantes Absolutos

| Bloqueante | Bloqueia | Ação |
|------------|----------|------|
| API Key Anthropic | Sprint 1+ | Gestor precisa criar conta |
| Número WhatsApp conectado | Sprint 1+ | Gestor escaneia QR |
| Vagas cadastradas | Sprint 2+ | Gestor cadastra manualmente |

---

## Alocação de Tempo

### Desenvolvimento (estimativa total)

| Sprint | Horas Dev | Foco |
|--------|-----------|------|
| 0 | 12h | Setup, estrutura |
| 1 | 16h | Webhook, agente |
| 2 | 24h | Vagas, Chatwoot, handoff |
| 3 | 24h | Testes, ajustes, complementos |
| 4 | 12h | Piloto, monitoramento |
| 5 | 10h | Expansão, métricas |
| **Total** | **~100h** | ~2.5 semanas full-time |

### Gestor (paralelo)

| Sprint | Atividade |
|--------|-----------|
| 0 | APIs, dados, hospitais, vagas |
| 1-2 | Acompanhar, cadastrar mais vagas |
| 3 | Participar testes, briefing equipe |
| 4-5 | Monitorar Chatwoot, resolver handoffs |

---

## Checkpoints

### Checkpoint 1 (fim Sprint 1)
- [ ] Júlia responde mensagens
- [ ] GO/NO-GO para Sprint 2

### Checkpoint 2 (fim Sprint 2)
- [ ] Vagas funcionando
- [ ] Chatwoot integrado
- [ ] GO/NO-GO para testes

### Checkpoint 3 (fim Sprint 3)
- [ ] Persona aprovada
- [ ] Equipe deu OK
- [ ] GO/NO-GO para piloto real

### Checkpoint 4 (fim Sprint 4)
- [ ] Piloto sem incidentes
- [ ] Métricas dentro do esperado
- [ ] GO/NO-GO para expansão

### Checkpoint Final (fim Sprint 5)
- [ ] MVP completo
- [ ] Decisão: Fase 2 ou pivot

---

## Riscos por Sprint

| Sprint | Risco Principal | Mitigação |
|--------|-----------------|-----------|
| 0 | API keys atrasam | Pedir com antecedência |
| 1 | Webhook não funciona | Testar Evolution isolado primeiro |
| 2 | Chatwoot complexo | Documentar cada passo |
| 3 | Persona não convence | Iterar rápido, mais exemplos |
| 4 | Médicos não respondem | Ajustar mensagem, horário |
| 5 | Ban WhatsApp | Rate limit conservador |

---

## Próximo Passo

**Sprint 0 começa agora.** Tarefas imediatas:

1. **Gestor:** Criar conta Anthropic → gerar API key
2. **Gestor:** Escanear QR code Evolution API
3. **Dev:** Criar estrutura FastAPI
4. **Dev:** Configurar clientes (Supabase, Anthropic)
