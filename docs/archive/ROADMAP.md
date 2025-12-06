# Roadmap - Agente Júlia

**Início do Projeto:** Dezembro 2025
**Última atualização:** 05/12/2025

---

## Visão Geral das Fases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROADMAP AGENTE JÚLIA                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FASE 0          FASE 1           FASE 2           FASE 3         FASE 4   │
│  Setup           MVP              Prospecção       Gestão          Scale    │
│                                                                             │
│  ┌─────────┐    ┌─────────┐      ┌─────────┐      ┌─────────┐    ┌───────┐ │
│  │ Infra   │───▶│ Agente  │─────▶│ Worker  │─────▶│ Briefing│───▶│ Multi │ │
│  │ Config  │    │ Core    │      │ Cadência│      │ Reports │    │ Tenant│ │
│  │ Setup   │    │ Webhook │      │ Follow  │      │ Slack   │    │ Pool  │ │
│  └─────────┘    └─────────┘      └─────────┘      └─────────┘    └───────┘ │
│                                                                             │
│  ████████████   ░░░░░░░░░░       ░░░░░░░░░░       ░░░░░░░░░░     ░░░░░░░░ │
│  Em andamento   Próximo          Futuro           Futuro         Futuro    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Fase 0: Setup & Configuração (ATUAL)

**Objetivo:** Preparar toda a infraestrutura e documentação

### Tarefas

| # | Tarefa | Status | Responsável |
|---|--------|--------|-------------|
| 0.1 | Documentação base (PRD, Arquitetura, Database) | ✅ | PM/Dev |
| 0.2 | Análise de custos LLM | ✅ | PM |
| 0.3 | Documento de setup | ✅ | PM |
| 0.4 | Mover arquivos legacy para deprecated | ✅ | Dev |
| 0.5 | Criar projeto no Supabase | ⏳ | Dev |
| 0.6 | Configurar MCP Supabase no Claude Code | ⏳ | Dev |
| 0.7 | Criar schema do banco (SQL) | ⏳ | Dev |
| 0.8 | Obter API key Anthropic | ⏳ | Admin |
| 0.9 | Configurar Slack workspace + webhook | ⏳ | Admin |
| 0.10 | Configurar Google Docs API | ⏳ | Dev |
| 0.11 | Testar Evolution API + conectar número | ⏳ | Dev |
| 0.12 | Testar Chatwoot | ⏳ | Dev |

### Entregáveis
- [ ] Ambiente de desenvolvimento funcional
- [ ] Banco de dados com schema criado
- [ ] Todas as APIs configuradas e testadas
- [ ] Número WhatsApp de teste conectado

---

## Fase 1: MVP - Core do Agente

**Objetivo:** Júlia responde mensagens recebidas via WhatsApp

### Tarefas

| # | Tarefa | Status | Descrição |
|---|--------|--------|-----------|
| 1.1 | Estrutura do projeto Python | ⏳ | FastAPI, pastas, configs |
| 1.2 | Cliente Supabase | ⏳ | CRUD básico, conexão |
| 1.3 | Webhook Evolution API | ⏳ | Receber mensagens |
| 1.4 | Agente Júlia básico | ⏳ | System prompt, Claude API |
| 1.5 | Processamento de mensagem | ⏳ | Fluxo completo in→out |
| 1.6 | Salvamento de interações | ⏳ | Histórico no banco |
| 1.7 | Cliente Evolution (envio) | ⏳ | Enviar respostas |
| 1.8 | Simulação de digitação | ⏳ | Presença online, typing |
| 1.9 | Integração Chatwoot | ⏳ | Sync de mensagens |
| 1.10 | Sistema de handoff básico | ⏳ | IA ↔ Humano via label |

### Critérios de Aceite
- [ ] Mensagem recebida → processada → resposta enviada em <30s
- [ ] Histórico salvo corretamente no banco
- [ ] Mensagens aparecem no Chatwoot
- [ ] Handoff funciona via label "humano"
- [ ] Júlia não responde quando controlled_by='human'

### Fluxo a implementar

```
WhatsApp → Evolution API → Webhook FastAPI
                              │
                              ▼
                    ┌─────────────────┐
                    │ Busca/cria      │
                    │ médico+conversa │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ controlled_by   │
                    │ = 'ai' ?        │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │ SIM            │ NÃO
                    ▼                ▼
            ┌──────────────┐  ┌────────────┐
            │ Agente Júlia │  │ Salvar msg │
            │ processa     │  │ apenas     │
            └──────┬───────┘  └────────────┘
                   │
                   ▼
            ┌──────────────┐
            │ Enviar via   │
            │ Evolution    │
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │ Sync com     │
            │ Chatwoot     │
            └──────────────┘
```

---

## Fase 2: Prospecção Ativa

**Objetivo:** Júlia inicia conversas e faz follow-ups automáticos

### Tarefas

| # | Tarefa | Status | Descrição |
|---|--------|--------|-----------|
| 2.1 | Tabela envios (fila) | ⏳ | Estrutura para cadência |
| 2.2 | Worker de cadência | ⏳ | Loop principal |
| 2.3 | Rate limiting | ⏳ | 20/hora, 100/dia |
| 2.4 | Geração de mensagens únicas | ⏳ | Cada abertura diferente |
| 2.5 | Lógica de follow-up | ⏳ | 48h, 5d, 15d |
| 2.6 | Horário comercial | ⏳ | 08h-20h, seg-sex |
| 2.7 | Controle de opt-out | ⏳ | Respeitar bloqueios |
| 2.8 | Script de importação | ⏳ | Importar lista de médicos |

### Critérios de Aceite
- [ ] Mensagens enviadas respeitam rate limit
- [ ] Cada mensagem de abertura é única
- [ ] Follow-ups disparam nos intervalos corretos
- [ ] Opt-out bloqueia imediatamente
- [ ] Horário comercial respeitado

---

## Fase 3: Sistema de Gestão

**Objetivo:** Gestor controla e monitora a Júlia

### Tarefas

| # | Tarefa | Status | Descrição |
|---|--------|--------|-----------|
| 3.1 | Integração Google Docs | ⏳ | Ler briefing |
| 3.2 | Parser de briefing | ⏳ | Extrair diretrizes |
| 3.3 | Tabela diretrizes | ⏳ | Armazenar regras |
| 3.4 | Injeção no prompt | ⏳ | Diretrizes no contexto |
| 3.5 | Worker de reports | ⏳ | 4x/dia + semanal |
| 3.6 | Notificações Slack | ⏳ | Eventos importantes |
| 3.7 | Comandos Slack | ⏳ | @julia status, pausar, etc |
| 3.8 | Dashboard básico | ⏳ | Métricas principais |

### Critérios de Aceite
- [ ] Mudança no Google Doc reflete em 60 min
- [ ] Reports enviados nos horários corretos
- [ ] Comandos Slack funcionam
- [ ] Métricas VIP aplicadas corretamente

---

## Fase 4: Escala & Refinamento

**Objetivo:** Preparar para volume e múltiplos clientes

### Tarefas

| # | Tarefa | Status | Descrição |
|---|--------|--------|-----------|
| 4.1 | Pool de WhatsApp | ⏳ | Múltiplos chips |
| 4.2 | Roteador de modelo | ⏳ | Haiku vs Sonnet |
| 4.3 | Métricas avançadas | ⏳ | Dashboards completos |
| 4.4 | Sistema de feedback | ⏳ | Loop de melhoria |
| 4.5 | Multi-tenant | ⏳ | Múltiplas empresas |
| 4.6 | Otimização de custos | ⏳ | Cache, batch |

---

## Métricas de Sucesso por Fase

| Fase | Métrica | Target |
|------|---------|--------|
| 0 | Setup completo | 100% tarefas |
| 1 | Latência resposta | <30s |
| 1 | Uptime | >99% |
| 2 | Taxa de resposta médicos | >30% |
| 2 | Mensagens/dia | 100 |
| 3 | Reports no horário | 100% |
| 3 | Diretrizes aplicadas | 100% |
| 4 | Custo por conversa | <$0.05 |
| 4 | Taxa detecção como bot | <1% |

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Ban do WhatsApp | Média | Alto | Rate limiting conservador, warm-up |
| Custo LLM alto | Baixa | Médio | Estratégia híbrida Haiku/Sonnet |
| Médico descobre IA | Baixa | Alto | Testes intensivos de persona |
| API instável | Média | Médio | Retry, fallback, monitoramento |
| LGPD | Baixa | Alto | Consentimento, opt-out, dados protegidos |

---

## Decisões Técnicas Tomadas

| Data | Decisão | Motivo |
|------|---------|--------|
| 05/12/2025 | Supabase como banco | Managed, pgvector nativo, API REST |
| 05/12/2025 | Claude Haiku para MVP | Melhor custo-benefício para validação |
| 05/12/2025 | Estratégia híbrida Haiku+Sonnet | Economia de 73% vs Sonnet puro |
| 05/12/2025 | Manter docker-compose local | Dev environment, Evolution + Chatwoot |

---

## Changelog

### 05/12/2025 - Início do Projeto
- Criada documentação base (PRD, Arquitetura, Database)
- Análise de custos LLM concluída
- Documento de setup criado
- Arquivos legacy movidos para deprecated/
- Roadmap definido
