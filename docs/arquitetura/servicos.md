# Arquitetura de Serviços

Documentação técnica detalhada de todos os 267 módulos de serviço do sistema.

**Versão:** 2.0 (Atualizado 09/02/2026)
**Escopo:** 11 domínios de negócio, 10+ camadas de integração

---

## Visão Geral Arquitetural

O sistema é organizado em 11 domínios de negócio bem definidos:

```
app/services/
├── 1. Core Agent (7 módulos)
├── 2. Intelligence (13 módulos)
├── 3. Messaging (12 módulos)
├── 4. Resilience (8 módulos)
├── 5. Integrations (12 módulos)
├── 6. Business (24 módulos)
├── 7. Chips & Warming (8 módulos)
├── 8. Groups Pipeline (8 módulos)
├── 9. Helena Agent (4 módulos)
├── 10. Analytics & Reporting (18 módulos)
└── 11. Policy & Guards (8 módulos)
```

### Princípios de Design

1. **Separation of Concerns** - Cada serviço tem responsabilidade bem definida
2. **Async/Await Pattern** - Todo I/O é assíncrono (banco, API, cache)
3. **Dependency Injection** - Serviços recebem dependências no init
4. **Error Handling** - Exceções customizadas em `app/core/exceptions.py`
5. **Logging Estruturado** - Contexto em cada log (medico_id, conversa_id, etc)
6. **Circuit Breaker** - Proteção contra falhas em cascata
7. **Rate Limiting** - Controle de throughput por recurso

---

## 1. Core Agent

Núcleo da orquestração de processamento de mensagens e inteligência do agente Julia.

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **agente.py** | Orquestrador principal do agente Julia - processa mensagens completas através do pipeline (contexto → LLM → tool execution → resposta), gerencia tool calls e coordena fluxo de conversação |
| **agente_slack.py** | Agente conversacional exclusivo para Slack (Sprint 9) - interpreta comandos naturais, mantém sessão de contexto e orquestra tools de gestão via NLP |
| **llm/** | Pacote cliente Claude Anthropic com estratégia híbrida (80% Haiku, 20% Sonnet) - abstrai chamadas de API, gerencia modelos, implementa fallback e retry logic |
| **conversa.py** | Gestão do ciclo de vida de conversas - busca/cria, atualiza status (active/paused/escalated/completed), encerra com motivo e synchroniza estado com Chatwoot |
| **interacao.py** | Persistência de todas as mensagens trocadas - salva (origem, tipo, conteúdo, metadata), carrega histórico com limite, formata para formato Messages API |
| **contexto.py** | Monta contexto completo para LLM - agrega dados do médico, especialidade, histórico, vagas, diretrizes, estado de handoff e timestamp para inferência contextual |
| **parser.py** | Parse de payloads webhook Evolution API - extrai mensagem, tipo, ID, timestamp e metadata de diferentes formatos de evento |

### Fluxo Principal de Processamento

```
Webhook (Evolution)
  ↓
[parser.py] → extrai conteúdo
  ↓
[conversa.py] → busca/cria conversa
  ↓
[agente.py::processar_mensagem_completo()]
  ├── [contexto.py] → monta contexto
  ├── [llm/] → gera resposta com tools
  ├── [tool_call execution] → se houver
  └── resposta final
  ↓
[timing.py] → calcula humanização
  ↓
[whatsapp.py] → envia mensagem
  ↓
[interacao.py] → salva histórico
```

### Configuração Principal

```python
# Modelos LLM (strategy híbrida)
LLM_MODEL = "claude-3-5-haiku-20241022"        # 80% chamadas (custo: $0.25/1M)
LLM_MODEL_COMPLEX = "claude-sonnet-4-20250514" # 20% (custo: $5/1M, melhor qualidade)

# Parâmetros de Geração
MAX_TOKENS = 1024
TEMPERATURE = 0.7
TOP_P = 0.9
```

---

## 2. Intelligence

Módulos de inteligência que tornam Julia capaz de entender contexto, detectar padrões e tomar decisões autônomas.

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **deteccao_bot.py** | Detecta menção explícita de IA/bot em mensagens (37 padrões regex) - registra detecções em métricas e computa taxa histórica |
| **handoff_detector.py** | Detecta triggers de escalação para humano (explícito, jurídico, sentimento negativo, confiança baixa) - classifica motivo e desencadeia handoff |
| **optout.py** | Detecta pedidos de opt-out via padrões regex - processa opt-out (marca cliente, envia confirmação, encerra), verifica permissão de envio proativo |
| **memoria/** | Pacote RAG com embeddings Voyage AI - indexa chunks de conhecimento, retrieves contexto relevante por similarity search, injeta dinamicamente no prompt |
| **embedding.py** | Cliente Voyage AI para geração de embeddings - encoda texto em 1024-dim vectors para similarity search em pgvector |
| **conhecimento/** | Pacote Knowledge Base (Sprint 13) - indexa documentos de docs/julia/, detector de objeções (10 tipos), detector de perfil médico (7 tipos), detector de objetivo de conversa (8 tipos) |
| **classificacao/** | Pacote classificação de mensagens - classficador de intent, detector de handoff via sentimento, estimador de confiança LLM |
| **message_context_classifier.py** | Classifica contexto de mensagem (discovery, negociação, objection, confirmação) para injeção de conhecimento direcionado |
| **deteccao_bot.py** | Detecta padrões indicativos que médico percebeu ser uma IA |
| **validacao_output.py** | Valida output do LLM antes de envio - verifica formato, compliance com persona, ausência de revelação de IA |
| **diretrizes_contextuais.py** | Aplica diretrizes dinâmicas do briefing do gestor ao contexto de inferência |
| **sistema_guardrails.py** | Aplica guardrails de segurança ao output - bloqueia mensagens inadequadas, detecta violações de persona |
| **politica/** | Pacote Policy Engine (Sprint 15) - define e executa políticas de negócio sobre estado de conversa e decisões automáticas |

### Knowledge Base Indexing (Sprint 13)

```python
# Indexação automática de docs/julia/
- 529 chunks de conhecimento
- 7 tipos de perfil médico
- 10 tipos de objeção + subtipos
- 8 tipos de objetivo de conversa

# Injection Strategy
1. Classifica intent da mensagem
2. Busca chunks relevantes por similarity (pgvector)
3. Injeta Top-K chunks no system prompt
4. LLM usa contexto para responder com maior confiabilidade
```

---

## 3. Messaging

Camada de transporte e formatação de mensagens WhatsApp.

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **whatsapp.py** | Cliente Evolution API - envia/recebe mensagens, marca como lida, controla status "online" e "digitando", implementa retry logic |
| **whatsapp_providers/** | Pacote multi-provider WhatsApp (Sprint 6) - abstração para suportar múltiplos provedores além Evolution (Twilio, etc) |
| **mensagem.py** | Formatação de mensagens - quebra mensagens longas respeitando limite WhatsApp (4000 chars), trata truncamento e rejeição |
| **timing.py** | Humanização de timing de respostas - calcula delays baseado em tamanho (2-15s), verifica horário comercial (08h-20h seg-sex), postpone se fora horário |
| **delivery_status.py** | Rastreamento de status de entrega - monitora hooks de delivered/read/failed, atualiza interacoes com status final |
| **fila.py** | Fila de mensagens em memória - buffer local para mensagens aguardando envio com priorização |
| **fila_mensagens.py** | Fila persistente em Supabase - agenda envios futuros com retry automático, responde hooks de agendamento |
| **abertura.py** | Variações de abertura de conversa (Sprint 8) - fornece templates parametrizados de primeiro contato para diversificação |
| **parser.py** | Parse de payloads webhook - extrai estrutura de mensagem para formato interno |
| **delay_engine.py** | Motor de cálculo de delays com variabilidade - simula padrão de digitação humano com distribuição aleatória |
| **fora_horario.py** | Gerencia comportamento fora de horário comercial - postpone, agenda para próximo horário comercial ou responde automaticamente |
| **respostas_especiais.py** | Templates de respostas especiais (confirmação, opt-out, escalação, etc) |

### Pipeline de Envio

```
Mensagem Gerada
  ↓
[timing.py] → calcula delay
  ↓
[fila_mensagens.py] → agenda se futuro
  ↓
[rate_limiter.py] → valida limites
  ↓
[whatsapp.py] → envia via Evolution
  ↓
[mostrar digitando] → humanização
  ↓
[delivery_status.py] → rastreia entrega
```

### Rate Limiting Crítico

```
Limite por Hora:   20 mensagens
Limite por Dia:    100 mensagens
Intervalo Mín:     45-180 segundos
Horário Permitido: 08:00-20:00 seg-sex
Behavior:          Atraso exponencial se limite próximo
```

---

## 4. Resilience

Camada de resiliência e proteção contra falhas em cascata.

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **rate_limiter.py** | Rate limiting distribuído via Redis - valida se pode enviar (por hora, por dia), registra envios, retorna tempo até liberação |
| **circuit_breaker.py** | Circuit breaker para APIs externas - gerencia estados (CLOSED → OPEN → HALF_OPEN), protege contra cascata de falhas, implementa timeout de recuperação |
| **redis.py** | Cliente Redis para cache e distributed locks - abstrai operações de cache, sessions, counters e pub/sub |
| **monitor_whatsapp.py** | Health check de Evolution API - monitora disponibilidade, detecta degradação, dispara alertas se falha |
| **error_handler.py** | Gerenciador centralizado de erros - mapeia exceções, log estruturado, notificações críticas para Slack |
| **alertas.py** | Sistema de alertas em tempo real - define triggers (taxa de detecção de bot > 5%, latência > 30s, downtime Evolution), envia para Slack |
| **garantias.py** | Sistema de retry com backoff exponencial - implementa jitter para evitar thundering herd |
| **falhas_esperadas.py** | Fallback strategies para falhas conhecidas - responde com template de fallback se LLM falhar, re-agenda se Evolution falhar |

### Circuit Breaker Estados

```
CLOSED (Normal)
  ↓ [5 falhas consecutivas ou taxa erro > 50%]
  ↓
OPEN (Bloqueado)
  ↓ [timeout 30s]
  ↓
HALF_OPEN (Teste)
  ↓ [1 sucesso]
  ↓
CLOSED

Instâncias:
- circuit_claude    → API Claude
- circuit_evolution → Evolution API
- circuit_supabase  → Supabase DB
```

---

## 5. Integrations

Camada de integração com sistemas externos.

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **supabase.py** | Cliente Supabase (PostgreSQL + pgvector) - executa queries, migrations, RLS enforcement, pool management |
| **chatwoot.py** | Cliente Chatwoot - cria conversas, atualiza status, sincroniza labels, escalação para humano, traz contexto de handoff |
| **slack.py** | Notificações Slack (outbound) - envia alertas, relatórios, notificações críticas com formatting |
| **slack_comandos.py** | Processamento de comandos Slack (inbound) - interpreta mensagens, valida permissões, executa tools de gestão |
| **slack_formatter.py** | Formatação de respostas Slack (Sprint 9) - monta blocos JSON, tables, attachments com design consistente |
| **google_docs.py** | Leitura de briefing Google Docs - extrai conteúdo, converte para estrutura interna |
| **briefing.py** | Sincronização automática de briefing (Sprint 7) - pooling de mudanças em Google Docs, atualiza diretrizes em tempo real |
| **briefing_parser.py** | Parser de documento Google Docs (Sprint 7) - extrai estrutura (seções, tabelas, listas) em formato estruturado |
| **salvy/** | Pacote Salvy integration (Sprint 27) - gerencia números virtuais para Julia Warmer, ativa/desativa chips, rastreia aquecimento |
| **evolution_api/** | Abstração Evolution API - wrappers tipados de endpoints principais |
| **http_client.py** | Cliente HTTP com retry, circuit breaker e timeout - usado para APIs externas não integradas nativamente |
| **integracao_config.py** | Configuração centralizada de integrações - credentials, endpoints, timeouts, circuit breaker params |

### Fluxo de Integração Slack

```
Mensagem Slack
  ↓
[slack_comandos.py] → parse NLP
  ↓
[validar permissão] → apenas operadores
  ↓
[executar tool] (buscar_medico, gerar_relatorio, etc)
  ↓
[slack_formatter.py] → formata resposta
  ↓
[slack.py] → envia para Slack
```

---

## 6. Business

Lógica de negócio core - vagas, campanhas, seguimento comercial.

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **vaga.py** | Gestão de vagas e plantões - busca compatíveis com perfil, reserva, formata para mensagem, valida disponibilidade |
| **vagas/** | Pacote gestão de vagas (tipos_vaga, periodos, setores, especialidades) - taxonomia de vagas com constraints |
| **campanha.py** | Orquestração de campanhas - cria, atualiza status, processa envios em batch |
| **campanhas/** | Pacote motor de campanhas (Sprint 35+) - campanha_repository (CRUD), campanha_executor (orquestração), types (TipoCampanha, StatusCampanha) |
| **campaign_sends.py** | Execução de envios em campanha - batch processing com rate limiting, retry, atraso entre envios |
| **campaign_behaviors.py** | Comportamentos especiais de campanha - warm-up gradual, weekday/time targeting, segment targeting |
| **campaign_cooldown.py** | Controle de cooldown entre campanhas - evita spam, respeita preferência de médico, tira feedback |
| **campaign_attribution.py** | Atribuição de conversas a campanhas - rastreia qual campanha gerou qual conversa, mede ROI |
| **followup.py** | Sistema de follow-ups automáticos - agenda (48h, 5d, 15d stages), processa pendentes, personaliza por resposta |
| **segmentacao.py** | Segmentação de médicos - filters (especialidade, região, nível interesse, etc), targets para campanhas |
| **tipos_abordagem.py** | 5 tipos de abordagem (discovery, oferta, reativação, follow-up, custom) - templates e persona por tipo |
| **priorizacao_medicos.py** | Algoritmo de priorização de médicos - rank por nível de interesse, compatibilidade de vaga, histórico |
| **outbound.py** | Orquestração de mensagens outbound (proativas) - escalonamento de envios, respect opt-out, logging |
| **outbound_dedupe.py** | Deduplicação de outbound - evita enviar mesma mensagem múltiplas vezes ao mesmo médico |
| **intent_dedupe.py** | Deduplicação de intent - agrupa conversas sobre mesmo assunto, evita repetição |
| **touch_reconciliation.py** | Reconciliação de "touches" de campanha - sincroniza eventos de envio entre Supabase e Evolution |
| **confirmacao_plantao.py** | Confirmação pós-realização de plantão (Sprint 16) - envia questonário satisfação, valida conclusão |
| **feedback.py** | Sistema de feedback de interações - coleta avaliação, qualidade, objections |
| **abertura.py** | Templates de abertura variados para cold outreach |
| **hospitais.py** | Catálogo de hospitais com constraints - integração com vagas |
| **conhecimento_hospitais.py** | Base de conhecimento sobre hospitais (localização, reputação, etc) |
| **handoff.py** | Execução de handoff IA→Humano - atualiza estado, notifica humano, sinaliza em Chatwoot |
| **medico.py** | Gestão de dados do médico - perfil, especialidade, histórico, preferences |
| **hospitais_bloqueados.py** | Lista de hospitais/regiões bloqueados - compliance e decisões comerciais |

### Funil de Conversão

```
Discovery (Prospecção)
  ├─ 1ª msg: abertura fria
  ├─ segmentacao: filtros
  └─ priorizacao: rank de interesse
  ↓
Engagement
  ├─ oferta: vaga compatível
  ├─ followup: 48h, 5d, 15d
  └─ abordagem: tipos_abordagem
  ↓
Qualification
  ├─ interesse: nível medido
  ├─ objeções: conhecido patterns
  └─ decision: aceita/rejeita
  ↓
Booking
  ├─ reserva: vaga_id + medico_id
  ├─ confirmacao: pós-realização
  └─ attribution: rastreia ROI
  ↓
Analytics
  └─ metricas: taxa resposta, conversão, valor
```

---

## 7. Chips & Warming

Sistema de aquecimento de números WhatsApp (Julia Warmer) e Multi-Julia Orchestration.

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **chips/** | Pacote gestão de Chips (Sprint 40+) - chip repository (CRUD), selection strategy (least loaded, warm-up phase), trust scoring |
| **warmer/** | Pacote Julia Warmer (Sprint 25) - orquestrador de aquecimento, tracking de progresso, ajuste de strategies baseado em feedback |
| **chip_activator/** | Pacote Chip Activator (Sprint 27) - provisiona chips via VPS, integra com Salvy, ativa/desativa on-demand |
| **salvy_integration.py** | Integração com Salvy (números virtuais) - provisiona números, ativa, tira do ar |
| **julia_chips.py** | Tabela de chips Julia - quais números estão em uso, status, trust score, fase de aquecimento |
| **chip_warmer_metrics.py** | Métricas de aquecimento - taxa de resposta por chip, detecção de bot por chip, volume processado |
| **warmer_orchestration.py** | Orquestração multi-Julia - distribui load entre Julias, balanceamento automático, failover |
| **julia_instances.py** | Gestão de instâncias Julia (múltiplas) - qual Julia ativa, qual phase (warm-up, stable, cold), sync de contexto |

### Estratégia de Warming

```
Fase 1: Inatividade (1-2 semanas)
  └─ Chip criado, nenhuma mensagem

Fase 2: Warm-up (2-4 semanas)
  ├─ Mensagens low volume (5/dia)
  ├─ Tempo entre: 08h-20h seg-sex
  └─ Monitoramento: taxa detecção de bot

Fase 3: Ramp-up (4-8 semanas)
  ├─ Volume gradual (20/dia → 50/dia → 100/dia)
  └─ Monitoramento: taxa resposta, engagement

Fase 4: Stable (permanente)
  ├─ Volume full (100-150/dia)
  ├─ Rate limiting normal
  └─ Trust score tracking

Fase 5: Cold (se problemático)
  └─ Retire do ar, reinicie warm-up com novo número
```

---

## 8. Groups Pipeline

Pipeline de processamento de mensagens de grupo WhatsApp com extração LLM (Sprint 52).

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **grupos/** | Pacote gestão de grupos (Sprint 14) - configura grupos, índices, sincronização de membros |
| **group_entry/** | Pacote orquestração de entrada em grupo (Sprint 51) - decisão de entrada, timing, estratégia |
| **extraction/** | Pacote pipeline extração LLM (Sprint 52) - extrai insights (intent, leads, objections) de mensagens de grupo |
| **grupos_config.py** | Configuração de grupos - quais monitorar, filtragem de conteúdo, regras de engagement |
| **grupos_sincronizacao.py** | Sincronização de membros/mensagens - busca periodicamente, valida integridade, atualiza cache |
| **grupos_inteligencia.py** | Análise de grupo - detecta tópicos, identifica key players, sentiment analysis |
| **extraction_manager.py** | Orquestrador da extração - coordena buscas, limpa duplicatas, agrupa insights |
| **extraction_llm.py** | Calls LLM para extração estruturada - monta prompt com contexto, parseia output estruturado |

---

## 9. Helena Agent

Agente de analytics exclusivo para Slack (Sprint 47).

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **helena/** | Pacote agente Helena - orquestrador, gerenciador de session, 5 tools pré-definidas (metricas, status, handoffs, quality, trends) |
| **helena_commands.py** | Mapeamento de comandos NLP → tools - interpreta "quais foram as métricas de ontem?" → calls `metricas_service` |
| **helena_sql.py** | Execução SQL segura com rate limiting - SELECT only, LIMIT ≤ 100, validação de colunas, logging de queries |
| **helena_session.py** | Gerenciador de sessão com TTL (30 min) - mantém contexto de conversa, histórico de commands, autorização |

### Tools Disponíveis

```
1. metricas - Taxa resposta, latência, volume, conversão
2. status - Estado do sistema, Julias online, health checks
3. handoffs - Casos escaldos recentemente, motivos, tempo
4. qualidade - Avaliações, detecção de bot, objeções
5. trends - Tendências de interesse, especialidades em alta demanda
```

---

## 10. Analytics & Reporting

Camada de análise de dados, métricas e relatórios.

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **metricas.py** | Coleta de métricas em tempo real - cálculo de KPIs (resposta, latência, conversão, volume) |
| **qualidade.py** | Avaliação de qualidade de interações - scoring de resposta, compliance com persona, detecção de anti-patterns |
| **relatorio.py** | Geração de relatórios consolidados - relatórios por período (manhã, almoço, tarde, fim-dia), semanal, mensal |
| **relatorios/** | Pacote geração de relatórios (Sprint 40+) - templates estruturados, exportação (PDF, CSV, JSON) |
| **business_events/** | Pacote event sourcing (Sprint 17) - tipos de eventos (conversa_iniciada, plantao_reservado, handoff_iniciado), emission de eventos, tracking de funil |
| **event_metrics.py** | Métricas derivadas de eventos - taxa conversão, tempo em cada stage, dropoff analysis |
| **kpis.py** | KPIs agregados para dashboard - volume diário, revenue estimado, taxa resposta, cost per conversion |
| **alertas.py** | Sistema de alertas em tempo real - triggers (taxa bot > 5%, latência > 30s, downtime), envio para Slack |
| **metricas_conversa.py** | Métricas por conversa - tempo de resposta, número de turns, sentimento, outcome |
| **metricas_deteccao_bot.py** | Tracking de detecção de bot - taxa por período, padrões mais comuns, impacto |
| **avaliacoes_qualidade.py** | Avaliações de qualidade - scoring rubric, feedback loop, calibração |
| **relatorio_campanha.py** | Relatório específico de campanha - ROI, taxa resposta, conversão, cost per conversion |
| **relatorio_medico.py** | Relatório de médico individual - histórico, especialidades abertas, performance |
| **dashboard_metrics.py** | Métricas para dashboard UI - agregação otimizada, caching, queries eficientes |
| **trends.py** | Análise de tendências - especialidades em alta demanda, regiões hot, sazonalidade |
| **conversao_funnel.py** | Funil de conversão detalhado - discovery → engagement → qualification → booking |
| **delivery_analytics.py** | Analytics de entrega de mensagens - delivered vs read vs failed, timing patterns |
| **engagement_scoring.py** | Scoring de engajamento do médico - baseado em padrões de resposta, interesse estimado |

### KPIs Principais

```
Taxa de Resposta:      % médicos que responderam primeira msg
Taxa de Conversão:     % respostas que levaram a booking
Latência Média:        Tempo de resposta (target: < 30s)
Volume Diário:         Mensagens processadas
Custo por Conversão:   API spend / bookings
Taxa Detecção Bot:     % conversas em que médico percebeu IA (target: < 1%)
Uptime:                Disponibilidade de sistema (target: > 99%)
```

---

## 11. Policy & Guards

Camada de políticas de negócio e guardrails de segurança.

### Módulos

| Módulo | Responsabilidade |
|--------|-----------------|
| **policy/** | Pacote Policy Engine (Sprint 15) - define políticas sobre estado de conversa, transições permitidas, decisões automáticas |
| **guardrails/** | Pacote guardrails de segurança - bloqueia respostas perigosas, detecta violações de persona, compliance checks |
| **sistema_guardrails.py** | Aplicação de guardrails - tira de circuito outputs inadequados, logs violations, notifica |
| **validacao_output.py** | Validação estrutural de output - checa formato, presença de campos obrigatórios, conformidade com schema |
| **gatilhos_autonomos.py** | Gatilhos que disparam comportamentos autônomos - opt-out detection, handoff trigger, escalação |
| **fora_horario.py** | Comportamento fora de horário comercial - postpone, resposta automática, agendamento |
| **diretrizes_contextuais.py** | Aplicação de diretrizes do briefing - injeta constraints no contexto baseado em diretivas do gestor |
| **estados_conversa.py** | Máquina de estado de conversa - estados válidos, transições permitidas, validação |

### Policy Engine Exemplo

```python
# Conversa em estado "negotiation"
if conversa.status == "negotiation" and medico.resposta_rate < 0.3:
    # Policy: não persistir com baixa taxa de resposta
    policy_reativacao = false
    status = "dormant"

# Conversa em estado "objection"
if conversa.status == "objection" and objection.tipo == "valores":
    # Policy: não descer valor mais de 10%
    max_discount = 0.10

# Conversa em estado "closed"
if conversa.status == "closed" and dias_desde_fechamento > 30:
    # Policy: pode reagendar para reativação
    pode_reativar = true
```

---

## Padrões e Convenções

### Nomenclatura de Funções

Conforme `app/CONVENTIONS.md`:

| Padrão | Exemplo | Uso |
|--------|---------|-----|
| `buscar_` | `buscar_medico_por_telefone()` | Buscar um recurso único |
| `listar_` | `listar_vagas_disponiveis()` | Buscar múltiplos recursos |
| `criar_` | `criar_conversa()` | Criar novo recurso |
| `atualizar_` | `atualizar_status_vaga()` | Modificar recurso existente |
| `deletar_` | `deletar_handoff()` | Remover recurso |
| `pode_` | `pode_enviar_proativo()` | Validação de permissão/capacidade |
| `tem_` | `tem_datapoints_suficientes()` | Validação de existência |
| `esta_` | `esta_em_horario_comercial()` | Validação de estado atual |
| `eh_` | `eh_mensagem_de_opt_out()` | Validação de tipo/identidade |
| `enviar_` | `enviar_notificacao_slack()` | Envia para sistema externo |
| `processar_` | `processar_mensagem_completo()` | Transforma/processa dados |
| `gerar_` | `gerar_resposta()` | Cria output/resultado |
| `formatar_` | `formatar_vaga_para_mensagem()` | Transforma para exibição |

### Logging Estruturado

```python
logger.info(
    "Processamento concluído",
    extra={
        "medico_id": medico.id,
        "conversa_id": conversa.id,
        "intent": classified_intent,
        "response_time_ms": elapsed_ms
    }
)
```

### Error Handling

```python
from app.core.exceptions import (
    DatabaseError,
    ExternalAPIError,
    ValidationError,
    RateLimitError,
    NotFoundError
)

try:
    resultado = await processar()
except RateLimitError as e:
    logger.warning(f"Rate limit atingido: {e}")
    # Retry com backoff
except ExternalAPIError as e:
    logger.error(f"API externa falhou: {e}")
    # Fallback ou escalação
except Exception as e:
    logger.critical(f"Erro inesperado: {e}")
    raise
```

---

## Importação Correta

### Supabase

```python
# Correto (v2.0+)
from app.services.supabase import supabase

# Incorreto (deprecated)
from app.services.supabase import get_supabase
```

### Campanhas

```python
# Correto (Sprint 35+)
from app.services.campanhas import campanha_repository, campanha_executor
from app.services.campanhas.types import TipoCampanha, StatusCampanha

# Incorreto (deprecated)
from app.services.campanha import criar_envios_campanha
```

### LLM

```python
# Correto
from app.services.llm import gerar_resposta, gerar_resposta_com_tools

# Com circuit breaker
from app.services.circuit_breaker import circuit_claude
result = await circuit_claude.call(gerar_resposta, mensagem, contexto)
```

---

## Adicionando Novo Serviço

### Checklist de Implementação

1. **Criar arquivo** em `app/services/novo_servico.py`
2. **Implementar funções async** com type hints completos
3. **Adicionar logging estruturado** com contexto (medico_id, conversa_id, etc)
4. **Adicionar tratamento de erros** com exceptions customizadas
5. **Documentar funções** com docstrings em formato Google
6. **Criar testes** em `tests/test_novo_servico.py` (mínimo 70% cobertura)
7. **Executar validação** com `uv run pytest` e `uv run ruff check`
8. **Atualizar documentação** neste arquivo com nova seção

### Template

```python
"""
Serviço para [descrição clara da responsabilidade].

Responsabilidades:
- [item 1]
- [item 2]
- [item 3]
"""

import logging
from typing import Optional, Dict, List
from app.services.supabase import supabase
from app.core.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


async def minha_funcao_principal(
    medico_id: str,
    parametro: str
) -> Dict[str, any]:
    """
    Descrição clara do que a função faz.

    Args:
        medico_id: ID do médico no banco
        parametro: Descrição do parâmetro

    Returns:
        Dict com estrutura {chave1: valor1, chave2: valor2}

    Raises:
        DatabaseError: Se query ao banco falhar
        ValidationError: Se parametro inválido

    Example:
        >>> resultado = await minha_funcao_principal("doc_123", "param")
        >>> resultado["status"]
        "ok"
    """
    try:
        logger.info(
            "Iniciando processamento",
            extra={"medico_id": medico_id, "parametro": parametro}
        )

        # Validação
        if not parametro:
            raise ValidationError("parametro obrigatório")

        # Operação principal
        resultado = await supabase.table("tabela").select("*").eq(
            "medico_id", medico_id
        ).execute()

        if not resultado.data:
            logger.warning(f"Nenhum dado para medico_id {medico_id}")
            return {"status": "not_found"}

        logger.info("Processamento concluído com sucesso")
        return {"status": "ok", "dados": resultado.data}

    except Exception as e:
        logger.error(f"Erro inesperado: {e}", exc_info=True)
        raise
```

### Testes Mínimos

```python
import pytest
from app.services.novo_servico import minha_funcao_principal
from app.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_minha_funcao_sucesso():
    resultado = await minha_funcao_principal("doc_123", "param_valido")
    assert resultado["status"] == "ok"


@pytest.mark.asyncio
async def test_minha_funcao_parametro_invalido():
    with pytest.raises(ValidationError):
        await minha_funcao_principal("doc_123", "")


@pytest.mark.asyncio
async def test_minha_funcao_not_found():
    resultado = await minha_funcao_principal("doc_inexistente", "param")
    assert resultado["status"] == "not_found"
```

---

## Observabilidade

### Métricas Exportadas

Todos os serviços devem exportar métricas via Prometheus:

```python
from prometheus_client import Counter, Histogram

processed_count = Counter(
    'novo_servico_processed_total',
    'Total de processamentos',
    ['status']
)

processing_time = Histogram(
    'novo_servico_processing_seconds',
    'Tempo de processamento'
)

# Usar:
with processing_time.time():
    resultado = await processar()
processed_count.labels(status='ok').inc()
```

### Correlação de Logs

Usar trace ID único por request:

```python
import contextvars
import uuid

trace_id = contextvars.ContextVar('trace_id', default=None)

# No middleware:
trace_id.set(str(uuid.uuid4()))

# Em todos os logs:
logger.info("evento", extra={"trace_id": trace_id.get()})
```

---

## Dependências e Versionamento

Gerenciar com `uv`:

```bash
# Adicionar dependência
uv add requests

# Atualizar
uv sync

# Lock
uv export > requirements.lock.txt
```

Versões críticas em `pyproject.toml`:

```toml
[project]
dependencies = [
    "anthropic==0.28.0",        # LLM
    "supabase==2.4.4",          # Database
    "redis==5.0.1",             # Cache
    "fastapi==0.104.1",         # API
    "voyage-ai==0.2.0",         # Embeddings
]
```

---

## Referências

- **Documento de Convenções:** `/app/CONVENTIONS.md`
- **Exceções Customizadas:** `/app/core/exceptions.py`
- **Rate Limiting:** `docs/arquitetura/rate-limiting.md`
- **Política Engine:** `docs/arquitetura/policy-engine.md`
- **Business Events:** `docs/arquitetura/business-events.md`
- **Knowledge Base:** `docs/julia/conhecimento-index.md`
- **Integrações:** `docs/integracoes/README.md`
