# Banco de Dados - Documentação Técnica Empresarial

Documentação completa do schema PostgreSQL para Júlia, agente de escalação médica autônoma da Revoluna.

**Última atualização:** 09/02/2026
**Schema versão:** 93 migrações aplicadas
**Tabelas:** 64+ tabelas bootstrap + views materializadas

---

## 1. Visão Geral da Arquitetura

### Infraestrutura

| Componente | Especificação |
|-----------|---------------|
| **Sistema Gerenciador** | PostgreSQL (Supabase managed) |
| **Projeto Supabase** | jyqgbzhqavgpxqacduoi |
| **Autenticação** | Supabase RLS (Row-Level Security) |
| **Conexão** | HTTPS via Supabase API REST / direct connection |

### Extensões Habilitadas

| Extensão | Propósito | Status |
|----------|----------|--------|
| `pgvector` | Busca semântica por embeddings | Ativo |
| `pg_trgm` | Busca full-text trigram | Ativo |
| `uuid-ossp` | Geração de UUIDs | Ativo |
| `pg_net` | Requisições HTTP de dentro do PostgreSQL | Ativo |
| `pg_graphql` | Interface GraphQL automática | Ativo |
| `pg_stat_statements` | Monitoramento de performance | Ativo |
| `pgcrypto` | Funções criptográficas | Ativo |
| `supabase_vault` | Gerenciamento seguro de secrets | Ativo |
| `unaccent` | Busca sem acentuação | Ativo |

### Schemas

| Schema | Proprietário | Finalidade |
|--------|-------------|-----------|
| `public` | postgres | Tabelas operacionais e views |
| `app_config` | postgres | Configuração segura da aplicação |
| `vault` | supabase_vault | Gerenciamento de secrets |
| `graphql` | supabase | Interface GraphQL |
| `extensions` | supabase | Extensões do PostgreSQL |

---

## 2. Diagrama ER (Relacionamentos Principais)

```
┌─────────────────────────────────────────────────────────────┐
│                   CORE AGENT (Conversas)                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  clientes (médicos)                                           │
│  ├─ conversations (sessões de chat)                          │
│  │  ├─ interacoes (mensagens)                               │
│  │  └─ handoffs (escalações IA→humano)                      │
│  │                                                            │
│  ├─ doctor_context (memória embeddings)                      │
│  └─ doctor_state (estado operacional atual)                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              BUSINESS EVENTS (Auditoria/Rastreamento)        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  business_events (event stream)                              │
│  ├─ policy_events (decisões de policy engine)               │
│  ├─ circuit_transitions (circuit breaker)                    │
│  └─ touch_reconciliation_log (confirmação de entrega)        │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│            SHIFTS & VACANCIES (Gestão de Plantões)           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  vagas (plantões disponíveis)                                │
│  ├─ hospitais (registry)                                     │
│  ├─ especialidades (médicas)                                 │
│  ├─ setores (UTI, CC, PS)                                    │
│  ├─ periodos (turno/duração)                                 │
│  ├─ tipos_vaga (classificação)                               │
│  └─ vagas_grupo (detectadas de grupos WhatsApp)             │
│                                                               │
│  alias tables (fuzzy matching):                              │
│  ├─ hospitais_alias                                          │
│  └─ especialidades_alias                                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│        CAMPAIGNS & OUTBOUND (Campanhas de Outreach)          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  campanhas (templates)                                       │
│  ├─ execucoes_campanhas (instâncias de execução)            │
│  ├─ envios (log de mensagens enviadas)                       │
│  ├─ campaign_contact_history (tracking de contatos)          │
│  ├─ campaign_metrics (KPIs agregados)                        │
│  └─ outbound_dedupe (deduplicação)                           │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│         JULIA MANAGEMENT (Configuração & Inteligência)       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  diretrizes (behavioral guidelines)                          │
│  ├─ diretrizes_contextuais                                   │
│  ├─ prompts (dynamic prompt templates)                       │
│  ├─ prompts_historico (version control)                      │
│  │                                                            │
│  conhecimento_julia (knowledge base com embeddings)           │
│  │  └─ 529+ chunks de docs/julia/                            │
│  │                                                            │
│  feature_flags (feature toggles)                             │
│  └─ intent_log (NLP tracking)                                │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│       QUEUE & MESSAGE PROCESSING (Fila de Mensagens)         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  fila_mensagens (main queue)                                 │
│  ├─ fila_mensagens_dlq (dead letter queue)                   │
│  ├─ fila_processamento_grupos (group processing)             │
│  ├─ mensagens_fora_horario (off-hours buffering)            │
│  ├─ pedidos_ajuda (help requests)                            │
│  └─ webhook_dlq (failed webhook processing)                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│      MONITORING & QUALITY (Qualidade e Anomalias)            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  avaliacoes_qualidade (quality assessments)                  │
│  metricas_deteccao_bot (bot detection tracking)              │
│  metricas_conversa (conversation KPIs)                       │
│  metricas_pipeline_diarias (daily pipeline stats)            │
│  data_anomalies (anomaly detection log)                      │
│  sugestoes_prompt (prompt improvement suggestions)           │
│  audit_trail (general audit)                                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│         GROUPS PIPELINE (Extração de Vagas via Grupos)       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  grupos_whatsapp (group registry)                            │
│  ├─ mensagens_grupo (captured messages)                      │
│  ├─ contatos_grupo (group members)                           │
│  ├─ vagas_grupo (shifts extracted from groups)               │
│  ├─ vagas_grupo_fontes (source tracking)                     │
│  ├─ group_links (link registry)                              │
│  └─ group_sources (source configuration)                     │
│                                                               │
│  vagas_hospitais_bloqueados (hospital exclusions)            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Definição de Tabelas por Categoria

### 3.1 Core Agent (Conversas e Interações)

#### **clientes**

Registro de todos os médicos prospectados e cadastrados.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| primeiro_nome | varchar(50) | Nome do médico | |
| sobrenome | varchar(100) | Sobrenome | |
| cpf | varchar(11) | CPF (11 dígitos) | Única, nullable |
| crm | varchar(20) | Registro CRM | Única, nullable |
| especialidade | varchar(50) | Especialidade médica | Indexada |
| telefone | varchar(20) | WhatsApp (formato E.164) | Única, NOT NULL |
| email | varchar(100) | Email pessoal | Indexada, nullable |
| cidade | varchar(50) | Cidade | Indexada |
| estado | varchar(2) | UF (2 letras maiúsculas) | CHECK regexpr |
| bitrix_id | integer | ID no CRM Bitrix | Nullable |
| origem | varchar(100) | Como foi prospectado | |
| status | varchar(50) | novo, respondeu, inativo, optout, etc | DEFAULT 'novo' |
| observacoes | text | Anotações | |
| created_at | timestamptz | Criado em | DEFAULT now() |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |
| created_by | varchar(255) | Quem criou | |
| deleted_at | timestamptz | Soft delete | Nullable, indexado |
| opt_out | boolean | Pediu para não receber (legacy) | DEFAULT false |
| opt_out_data | timestamptz | Data do opt-out | Nullable |
| ultima_mensagem_data | timestamptz | Última mensagem recebida | Nullable |
| ultima_mensagem_tipo | text | Tipo da última campanha | Nullable |
| total_interacoes | integer | Contador de mensagens | DEFAULT 0 |
| stage_jornada | text | novo, aguardando_resposta, respondeu, etc | DEFAULT 'novo' |
| pressure_score_atual | integer | Saturação (0-100, >70 alta, >90 saturado) | DEFAULT 0 |
| deals_ativos_bitrix | jsonb | Deals abertos no Bitrix | DEFAULT '{}' |
| tags | jsonb | Array de tags personalizadas | DEFAULT '{}' |
| app_cadastrado | boolean | Cadastrado no app Revoluna | DEFAULT false |
| titulo | text | Título/cargo | Nullable |
| contexto_consolidado | text | Resumo consolidado para IA | Nullable |
| embedding | vector(1536) | Embedding do contexto (Ada-002) | Indexed with IVF |
| ultima_interacao_resumo | text | Último resumo para quick context | Nullable |
| preferencias_detectadas | jsonb | Ex: {"turno": "noturno"} | DEFAULT '{}' |
| flags_comportamento | jsonb | Ex: {"responde_rapido": true} | DEFAULT '{}' |
| qualification_score | numeric | Score 0-1 (perfil completo) | DEFAULT 0 |
| preferencias_conhecidas | jsonb | Preferências consolidadas | DEFAULT '{}' |
| grupo_piloto | boolean | Participa do MVP piloto | DEFAULT false, indexed |
| opted_out | boolean | Pediu opt-out (normalizado) | DEFAULT false |
| opted_out_at | timestamptz | Data/hora do opt-out | Nullable |
| opted_out_reason | text | Mensagem que triggou opt-out | Nullable |
| ultima_abertura | jsonb | Última abertura usada (evita repetição) | Nullable |

**Índices:** telefone (unique), cpf, crm, email, cidade, estado, status, especialidade, stage_jornada (where deleted_at IS NULL), grupo_piloto, opt_out, opted_out, criado_at DESC

**RLS:** Service role only

**Acessos típicos:**
```sql
-- Buscar médico por telefone
SELECT * FROM clientes WHERE telefone = '+5511987654321';

-- Médicos elegíveis para campanha (não optout, não saturados, sem contato recente)
SELECT * FROM clientes
WHERE status != 'optout'
  AND pressure_score_atual < 70
  AND ultima_mensagem_data < NOW() - INTERVAL '14 days';
```

---

#### **conversations**

Agrupamento de mensagens em conversas para controle de handoff IA/humano.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| cliente_id | uuid | FK -> clientes | NOT NULL, indexed |
| execucao_campanha_id | bigint | FK -> execucoes_campanhas | Nullable |
| campanha_id | bigint | FK -> campanhas | Nullable |
| instance_id | varchar(100) | WhatsApp instance usada | Nullable |
| status | varchar(50) | active, paused, escalated, completed, abandoned | DEFAULT 'active' |
| controlled_by | varchar(20) | ai ou human | DEFAULT 'ai', CHECK constraint |
| controlled_by_user_id | uuid | Usuário Supabase controlando | Nullable |
| escalation_reason | text | Por que foi escalada | Nullable |
| message_count | integer | Total de mensagens | DEFAULT 0 |
| last_message_at | timestamptz | Última mensagem | Indexado DESC |
| started_at | timestamptz | Início da conversa | DEFAULT now() |
| completed_at | timestamptz | Conclusão | Nullable |
| created_at | timestamptz | Criado em | DEFAULT now() |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |
| chatwoot_conversation_id | text | ID no Chatwoot para handoff | Nullable, indexed |
| chatwoot_contact_id | text | ID do contato Chatwoot | Nullable |
| stage | varchar(50) | novo, msg_enviada, respondeu, reservou | DEFAULT 'novo' |
| ultima_mensagem_em | timestamptz | Para calcular delay follow-up | Nullable |
| pausado_ate | timestamptz | Se NULL, conversa ativa | Nullable |
| first_touch_campaign_id | bigint | Campaign que iniciou | Nullable, indexed |
| first_touch_type | text | campaign, followup, manual, slack | Nullable |
| first_touch_at | timestamptz | Timestamp do primeiro touch | Nullable |
| last_touch_campaign_id | bigint | Última campaign que tocou | Nullable, indexed |
| last_touch_type | text | Tipo do último touch | Nullable |
| last_touch_at | timestamptz | Timestamp do último touch | Nullable, indexed DESC |

**Índices:** cliente_id, status, controlled_by, chatwoot_conversation_id, last_message_at DESC, last_touch_at DESC, primeira_touch_campaign_id, última_touch_campaign_id, composite (stage, controlled_by, ultima_mensagem_em) where pausado_ate IS NULL

**RLS:** Service role only

**Acessos típicos:**
```sql
-- Conversa ativa de um cliente
SELECT * FROM conversations
WHERE cliente_id = $1 AND status = 'active'
ORDER BY created_at DESC LIMIT 1;

-- Conversas a fazer follow-up
SELECT * FROM conversations
WHERE stage NOT IN ('respondeu', 'reservou')
  AND pausado_ate IS NULL
  AND ultima_mensagem_em < NOW() - INTERVAL '24 hours'
ORDER BY ultima_mensagem_em ASC;
```

---

#### **interacoes**

Log de TODAS as mensagens trocadas (médico, Júlia, sistema).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | bigint | Chave primária | NOT NULL, auto-increment |
| cliente_id | uuid | FK -> clientes | NOT NULL, indexed |
| envio_id | bigint | FK -> envios (se de campanha) | Nullable |
| deal_bitrix_id | text | Deal Bitrix associado | Nullable |
| parent_id | bigint | Se for resposta, ID da mensagem original | Nullable |
| origem | text | medico_whatsapp, julia, sistema, admin | NOT NULL |
| tipo | text | entrada, saida | NOT NULL |
| canal | text | whatsapp | DEFAULT 'whatsapp' |
| conteudo | text | Texto da mensagem | Nullable |
| conteudo_original | text | Conteúdo antes de transformações | Nullable |
| anexos | jsonb | Array de files (ex: images, audio) | Nullable |
| autor_user_id | text | ID do usuário que enviou | Nullable |
| autor_nome | text | Nome do autor | Nullable |
| autor_tipo | text | medico, agent, human, system | Nullable |
| sentimento_score | integer | Análise de sentimento (-1=negativo, 0=neutro, 1=positivo) | Nullable |
| classificacao_ia | jsonb | {"intencao": "...", "topicos": [...], "urgencia": "..."} | Nullable |
| requer_followup | boolean | Flag para follow-up automático | DEFAULT false |
| prioridade | text | alta, normal, baixa | Nullable |
| bitrix_message_id | text | ID da mensagem no Bitrix | Nullable |
| bitrix_activity_id | text | ID da atividade Bitrix | Nullable |
| twilio_message_sid | text | Message SID Twilio (se aplicável) | Nullable |
| contexto_conversa | jsonb | Contexto extraído (preferências, dados, etc) | Nullable |
| created_at | timestamptz | Timestamp da mensagem | DEFAULT now(), indexed DESC |
| sincronizado_bitrix_em | timestamptz | Quando foi sincronizada | Nullable |
| processado_em | timestamptz | Quando pipeline processou | Nullable |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |
| conversation_id | uuid | FK -> conversations | NOT NULL, indexed |
| ai_confidence | numeric | Confiança da resposta IA (0-1) | Nullable |
| ai_suggested_response | text | Resposta sugerida pela IA | Nullable |
| extracted_data | jsonb | Dados extraídos (nome, especialidade, etc) | Nullable |
| attributed_campaign_id | bigint | Campaign atribuído (last touch 7 dias) | Nullable |

**Índices:** cliente_id, conversation_id (indexed), created_at DESC, conversation_id + created_at DESC

**RLS:** Service role only

**Performance notes:** Tabela de alto volume (crescimento linear com conversas). Usar índices compostos para queries de paginação.

**Acessos típicos:**
```sql
-- Histórico de uma conversa
SELECT * FROM interacoes
WHERE conversation_id = $1
ORDER BY created_at ASC;

-- Últimas mensagens recebidas (inbound)
SELECT * FROM interacoes
WHERE cliente_id = $1 AND origem = 'medico_whatsapp'
ORDER BY created_at DESC
LIMIT 10;
```

---

#### **doctor_context**

Memória de longo prazo com embeddings para RAG (Retrieval-Augmented Generation).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| cliente_id | uuid | FK -> clientes | NOT NULL, indexed |
| content | text | Chunk de contexto (texto livre) | NOT NULL |
| embedding | vector(1536) | Embedding para busca semântica | NOT NULL, IVF indexed |
| source | varchar | conversation, manual, system, briefing | DEFAULT 'conversation' |
| created_at | timestamptz | Criado em | DEFAULT now(), indexed DESC |

**Índices:** cliente_id, embedding (IVF), source, created_at DESC

**RLS:** Service role only

**Função especializada:**
```sql
-- Busca de memórias similares para um médico
SELECT * FROM doctor_context
WHERE cliente_id = $1
ORDER BY embedding <=> $2  -- cosine distance
LIMIT 5;
```

---

#### **doctor_state**

Estado operacional atual de cada médico (cooldown, último contato, etc).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| cliente_id | uuid | FK -> clientes | NOT NULL, unique, indexed |
| last_outbound_at | timestamptz | Última mensagem saída | Nullable |
| last_inbound_at | timestamptz | Última mensagem entrada | Nullable |
| contact_count_7d | integer | Contatos últimos 7 dias | DEFAULT 0 |
| next_allowed_at | timestamptz | Quando pode contatar novamente (cooldown) | Nullable |
| cooling_off | boolean | Se está em período de cooldown | DEFAULT false |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |
| last_circuit_break_at | timestamptz | Último circuit break | Nullable |

**Índices:** cliente_id (unique), next_allowed_at (where cooling_off = true)

**RLS:** Service role only

---

#### **handoffs**

Auditoria completa de escalações IA → humano.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| conversation_id | uuid | FK -> conversations | NOT NULL, indexed |
| from_controller | varchar | ai ou human | NOT NULL |
| to_controller | varchar | ai ou human | NOT NULL |
| reason | text | Motivo (sentiment_negative, user_requested, complex_issue) | NOT NULL |
| created_at | timestamptz | Timestamp | DEFAULT now(), indexed DESC |

**RLS:** Service role only

---

### 3.2 Shifts & Vacancies (Gestão de Plantões)

#### **vagas**

Plantões disponíveis gerenciados pela Revoluna.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| hospital_id | uuid | FK -> hospitais | NOT NULL, indexed |
| especialidade_id | uuid | FK -> especialidades | NOT NULL, indexed |
| setor_id | uuid | FK -> setores | Nullable, indexed |
| periodo_id | uuid | FK -> periodos | Nullable |
| data | date | Data do plantão | NOT NULL, indexed |
| hora_inicio | time | Horário início | Nullable |
| hora_fim | time | Horário fim | Nullable |
| valor | integer | Valor em centavos (reais * 100) | Nullable |
| status | varchar | aberta, reservada, confirmada, pendente_confirmacao, realizada, cancelada, anunciada, fechada | DEFAULT 'aberta' |
| cliente_id | uuid | Médico que reservou/confirmou | Nullable, indexed |
| created_at | timestamptz | Criado em | DEFAULT now() |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |
| criador | text | Quem criou (admin, api, grupos) | Nullable |
| source | text | sistema, grupos_whatsapp, manual | DEFAULT 'manual' |
| numero_vagas | integer | Quantidade de posições | DEFAULT 1 |

**Índices:** hospital_id, especialidade_id, setor_id, data, status, cliente_id, (especialidade_id, data) where status='aberta'

**RLS:** Service role only

**Status transitions importantes:**
- aberta → reservada → confirmada → realizada
- Qualquer → cancelada (a qualquer tempo)

---

#### **hospitais**

Cadastro de hospitais onde plantões são oferecidos.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| nome | text | Nome do hospital | NOT NULL, indexed |
| cidade | text | Cidade | NOT NULL, indexed |
| estado | text | UF | Indexed |
| endereco_formatado | text | Endereço completo | Nullable |
| latitude | numeric | Coordenada | Nullable |
| longitude | numeric | Coordenada | Nullable |
| region_code | text | Código de região (ABC, SBC, etc) | Nullable |
| ativo | boolean | Se está ativo | DEFAULT true |

**Dados atuais:** 85+ hospitais

**Índices:** nome, cidade, estado, ativo where ativo=true

**Performance note:** Usar alias table (hospitais_alias) para fuzzy matching por nome.

---

#### **especialidades**

Especialidades médicas (Cardiologia, Pediatria, etc).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| nome | varchar(100) | Nome da especialidade | NOT NULL, unique, indexed |
| codigo | varchar(20) | Código interno | Nullable |
| alias | text[] | Aliases comuns (ex: "Cardio" para "Cardiologia") | DEFAULT '{}' |

**Dados atuais:** 56 especialidades

---

#### **setores**

Setores hospitalares (UTI, Centro Cirúrgico, Pronto-Socorro, etc).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| nome | text | Nome do setor | NOT NULL, unique |
| codigo | varchar(20) | Código | Nullable |

**Dados atuais:** 9 setores (UTI, CC, PS, Psiquiatria, etc)

---

#### **periodos**

Períodos/turnos disponíveis (Diurno, Noturno, 12h, 24h, etc).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | Chave primária | NOT NULL, DEFAULT gen_random_uuid() |
| nome | varchar(50) | Nome do período | NOT NULL, unique |
| index | smallint | Ordem de exibição | |

**Dados atuais:** 6 períodos

---

#### **hospitais_alias**

Tabela para fuzzy matching de nomes de hospitais.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| hospital_id | uuid | FK -> hospitais | |
| alias | text | Nome alternativo | indexed |
| tipo | text | acronym, abreviacao, sinonimo | |

---

#### **especialidades_alias**

Fuzzy matching para especialidades.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| especialidade_id | uuid | FK -> especialidades | |
| alias | text | Nome alternativo | indexed |
| tipo | text | acronym, sinonimo | |

---

### 3.3 Campaigns & Outbound (Campanhas)

#### **campanhas**

Templates de campanhas (discovery, oferta, reativação).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | bigint | PK | auto-increment |
| nome_template | text | Nome descritivo | NOT NULL |
| friendly_name | text | Nome para exibição | indexed |
| tipo_campanha | text | discovery, oferta, reativacao, followup, custom | |
| corpo | text | Template de mensagem | |
| tom | text | tom a usar (profissional, casual, urgent) | |
| pressure_points | integer | Pontos adicionados ao pressure_score | DEFAULT 0 |
| ativo | boolean | Se pode ser usada | DEFAULT true, indexed where ativo=true |
| status | varchar | draft, agendada, ativa, concluida, pausada | DEFAULT 'draft' |
| agendar_para | timestamptz | Quando executar (se agendada) | nullable, indexed |
| template_sid | text | ID de template no provider (ex: Twilio) | indexed |
| versao | integer | Número da versão | DEFAULT 1 |
| created_at | timestamptz | Criado em | DEFAULT now() |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |
| created_by | text | Usuário criador | |

**Índices:** ativo, status+agendar_para (where status='agendada'), template_sid, friendly_name

---

#### **execucoes_campanhas**

Instância de execução de uma campanha (segmentação, targets, resultados).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | bigint | PK | auto-increment |
| campanha_id | bigint | FK -> campanhas | indexed |
| nome_execucao | text | Nome/identificador | |
| status | text | rascunho, agendada, ativa, pausada, concluida | DEFAULT 'rascunho' |
| segmento_filtros | jsonb | Filtros de segmentação | DEFAULT '{}' |
| quantidade_alvo | integer | Total de alvos | |
| quantidade_enviada | integer | Enviadas | DEFAULT 0 |
| quantidade_respostas | integer | Respostas | DEFAULT 0 |
| quantidade_opt_out | integer | Opt-outs durante execução | DEFAULT 0 |
| created_at | timestamptz | Criado em | DEFAULT now() |
| iniciada_em | timestamptz | Quando começou | nullable |
| concluida_em | timestamptz | Quando terminou | nullable |

---

#### **envios**

Log de envios de mensagens (campaign sends com tracking).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | bigint | PK | auto-increment |
| cliente_id | uuid | FK -> clientes | NOT NULL, indexed |
| campanha_id | bigint | FK -> campanhas | indexed |
| execucao_id | bigint | FK -> execucoes_campanhas | nullable |
| conteudo_enviado | text | Mensagem que foi enviada | |
| status | text | pendente, enviada, entregue, lida, falhou, bounce, unsubscribe | DEFAULT 'pendente', indexed |
| outcome | send_outcome enum | Detalhe do resultado (SENT, BLOCKED_OPTED_OUT, FAILED_RATE_LIMIT, etc) | |
| enviado_em | timestamptz | Timestamp do envio | indexed |
| entregue_em | timestamptz | Timestamp de entrega | nullable |
| visualizado_em | timestamptz | Timestamp de leitura | nullable |
| provider_message_id | text | ID da mensagem no provider (Evolution/Twilio) | nullable, indexed |
| metadata | jsonb | Extra info (campaign_id, tentativas, etc) | DEFAULT '{}' |
| created_at | timestamptz | Criado em | DEFAULT now() |

**Índices:** cliente_id, campanha_id, status, enviado_em, provider_message_id

**High-volume table note:** Cresce com volume de campanhas. Índices em status e provider_message_id críticos para performance.

---

#### **campaign_contact_history**

Histórico de contatos por cliente para deduplicação.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | bigint | PK | auto-increment |
| cliente_id | uuid | FK -> clientes | NOT NULL, indexed |
| campanha_id | bigint | FK -> campanhas | indexed |
| campaign_type | text | discovery, oferta, etc | |
| sent_at | timestamptz | Quando foi enviado | indexed DESC |
| outcome | send_outcome enum | Resultado | |

**Índices:** cliente_id+sent_at DESC, campanha_id

---

#### **campaign_metrics**

KPIs agregados por campanha.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | bigint | PK | |
| campanha_id | bigint | FK -> campanhas | indexed |
| total_enviadas | integer | Total enviadas | |
| total_entregues | integer | Total entregues | |
| taxa_resposta_percentual | numeric | % de resposta | |
| respostas_positivas | integer | Respostas yes | |
| respostas_negativas | integer | Respostas no | |
| opt_outs | integer | Opt-outs | |
| bounces | integer | Bounces | |
| calculado_em | timestamptz | Última atualização | DEFAULT now() |

---

#### **outbound_dedupe**

Deduplicação para evitar contatar mesmo médico 2x.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | bigint | PK | |
| cliente_id | uuid | FK -> clientes | indexed |
| campaign_id | bigint | FK -> campanhas | indexed |
| sent_at | timestamptz | Quando foi enviado | indexed |
| provider_message_id | text | ID do provider | |
| metadata | jsonb | Extra (telefone, etc) | |

---

### 3.4 Julia Management (Configuração & Inteligência)

#### **diretrizes**

Diretrizes comportamentais ativas que guiam o agente.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| tipo | text | foco, evitar, tom, meta, vip, prioridade_baixa, etc | |
| conteudo | text | Descrição da diretriz | NOT NULL |
| prioridade | integer | Prioridade (maior = mais importante) | DEFAULT 0 |
| origem | text | google_docs, slack, sistema | |
| ativo | boolean | Se está aplicada | DEFAULT true, indexed |
| expira_em | timestamptz | Validade | nullable |
| created_at | timestamptz | Criado em | DEFAULT now() |
| criado_por | text | Usuário | |

**RLS:** Service role only

---

#### **prompts**

Sistema dinâmico de prompts (versionado).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| nome | text | Identificador do prompt | |
| tipo | text | principal, fallback, followup, escalacao | |
| conteudo | text | Conteúdo do prompt (pode incluir placeholders) | NOT NULL |
| versao | integer | Número da versão | |
| ativo | boolean | Se está sendo usada | DEFAULT false, única por (nome, ativo=true) |
| trigger | text | Quando aplicar (ex: "primeira_mensagem") | |
| created_at | timestamptz | Criado em | DEFAULT now() |
| created_by | text | Criado por | |

**Constraint especial:** Apenas 1 prompt pode ser ativo por (nome, tipo).

**Função DB:**
```sql
-- Garante single active prompt por trigger
CREATE FUNCTION check_single_active_prompt() RETURNS TRIGGER AS $$
BEGIN
  IF NEW.ativo = true THEN
    UPDATE prompts SET ativo = false
    WHERE nome = NEW.nome AND id != NEW.id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

#### **prompts_historico**

Version control de prompts.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| prompt_id | uuid | FK -> prompts | |
| versao_anterior | text | Conteúdo anterior | |
| versao_nova | text | Conteúdo novo | |
| mudancas | text | Descrição das mudanças | |
| alterado_em | timestamptz | Timestamp | DEFAULT now() |
| alterado_por | text | Usuário | |

---

#### **conhecimento_julia**

Knowledge base com embeddings (RAG).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| arquivo | text | Arquivo de origem (ex: docs/julia/persona.md) | indexed |
| secao | text | Seção do arquivo | |
| conteudo | text | Chunk de texto | NOT NULL |
| embedding | vector(1536) | Embedding do chunk (Ada-002) | IVF indexed |
| tipo | text | persona, regras, exemplos, conhecimento_medico | indexed |
| subtipo | text | Subtipo mais específico | indexed |
| tags | text[] | Tags de categorização | GIN indexed |
| ativo | boolean | Se pode ser usado | DEFAULT true, indexed |
| created_at | timestamptz | Criado em | DEFAULT now() |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |

**Dados atuais:** 529+ chunks de docs/julia/

**RLS:** Service role only

**Função especializada:**
```sql
-- Buscar conhecimento por similaridade semântica
SELECT * FROM conhecimento_julia
WHERE ativo = true
  AND (tipo = $2 OR $2 IS NULL)
  AND (1 - (embedding <=> $1)) >= 0.65
ORDER BY embedding <=> $1
LIMIT 5;
```

---

#### **feature_flags**

Feature toggles para controlar funcionalidades.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| flag_name | text | Nome da flag | NOT NULL, unique |
| enabled | boolean | Se está ativada | DEFAULT false |
| rollout_percentage | integer | % de rollout (0-100) | DEFAULT 100 |
| metadata | jsonb | Extra (ex: target_users) | DEFAULT '{}' |
| created_at | timestamptz | Criado em | DEFAULT now() |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |

---

#### **intent_log**

Log de intenções detectadas pelo NLP.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| interacao_id | bigint | FK -> interacoes | indexed |
| cliente_id | uuid | FK -> clientes | indexed |
| intent | text | Intenção detectada (interesse, objeção, etc) | |
| confidence | numeric | Confiança (0-1) | |
| raw_analysis | jsonb | Análise completa | |
| created_at | timestamptz | Criado em | DEFAULT now() |

---

### 3.5 Business Events & Policy Engine

#### **business_events**

Event stream completo do sistema (auditoria + rastreamento).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| ts | timestamptz | Timestamp do evento | indexed DESC, NOT NULL |
| event_type | text | doctor_inbound, doctor_outbound, offer_accepted, shift_completed, policy_decision, etc | indexed, NOT NULL |
| cliente_id | uuid | FK -> clientes | indexed, nullable |
| conversa_id | uuid | FK -> conversations | indexed, nullable |
| vaga_id | uuid | FK -> vagas | indexed, nullable |
| hospital_id | uuid | FK -> hospitais | indexed, nullable |
| interaction_id | bigint | FK -> interacoes | nullable |
| policy_decision_id | uuid | FK -> policy_events | nullable, indexed |
| payload | jsonb | Dados do evento | NOT NULL |
| metadata | jsonb | Metadata extra | DEFAULT '{}' |

**Índices:** ts DESC, event_type+ts DESC, cliente_id+ts DESC, vaga_id+ts DESC, hospital_id+ts DESC, policy_decision_id

**RLS:** Service role only

**Event types principais:**
- doctor_inbound: Médico enviou mensagem
- doctor_outbound: Júlia enviou mensagem
- offer_accepted: Médico aceitou oferta
- offer_rejected: Médico recusou
- shift_pending_confirmation: Aguardando confirmação
- shift_completed: Plantão realizado
- shift_cancelled: Plantão cancelado
- opt_out_requested: Médico pediu para sair
- handoff_triggered: Escalação IA→humano
- policy_decision: Policy engine tomou decisão

---

#### **policy_events**

Decisões da policy engine (rate limit, circuit breaker, etc).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| ts | timestamptz | Timestamp | indexed DESC |
| cliente_id | uuid | FK -> clientes | indexed |
| policy_type | text | rate_limit, circuit_breaker, cooling_off, contact_cap | |
| decision | text | allow, block, delay | |
| effect_type | text | message_sent, message_queued, message_blocked | indexed |
| reason | text | Motivo da decisão | |
| details | jsonb | Detalhes (ex: blocked_until, reason_code) | |
| created_at | timestamptz | Criado em | DEFAULT now() |

---

### 3.6 Queue & Outbound (Fila de Mensagens)

#### **fila_mensagens**

Fila principal de mensagens pendentes.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| cliente_id | uuid | FK -> clientes | indexed |
| conversa_id | uuid | FK -> conversations | indexed |
| conteudo | text | Mensagem a enviar | NOT NULL |
| tipo | text | lembrete, followup, campanha, escalacao | |
| prioridade | integer | 0-10 (maior = urgente) | DEFAULT 5, indexed |
| status | text | pendente, enviada, falhou, bloqueado, descartado | DEFAULT 'pendente', indexed |
| outcome | send_outcome enum | Detalhe do resultado | nullable |
| agendar_para | timestamptz | Quando enviar | indexed, NOT NULL |
| tentativas | integer | Número de tentativas | DEFAULT 0 |
| proxima_tentativa | timestamptz | Próxima tentativa | nullable |
| enviada_em | timestamptz | Timestamp do envio | nullable, indexed |
| motivo_falha | text | Por que falhou | nullable |
| provider_message_id | text | ID no provider (Evolution) | nullable, indexed |
| metadata | jsonb | Extra (campaign_id, etc) | DEFAULT '{}' |
| created_at | timestamptz | Criado em | DEFAULT now() |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |

**Índices:** agendar_para (where status='pendente'), status, prioridade, cliente_id, conversa_id, enviada_em

**High-volume table:** Otimizada para processamento em batch.

**Typical workflow:**
```sql
-- Buscar mensagens prontas para enviar (polling)
SELECT * FROM fila_mensagens
WHERE status = 'pendente'
  AND agendar_para <= NOW()
ORDER BY prioridade DESC, agendar_para ASC
LIMIT 100;

-- Marcar como enviada
UPDATE fila_mensagens
SET status = 'enviada', enviada_em = NOW(), provider_message_id = $1
WHERE id = $2;
```

---

#### **fila_mensagens_dlq**

Dead Letter Queue para mensagens que falharam.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| fila_mensagens_id | uuid | FK -> fila_mensagens | indexed |
| cliente_id | uuid | FK -> clientes | indexed |
| motivo_dlq | text | Razão de ir para DLQ | |
| tentativas_restantes | integer | Antes de descartar | |
| enviado_para_dlq_em | timestamptz | Timestamp | DEFAULT now() |
| resolvido_em | timestamptz | Se resolvido | nullable |
| resolucao_notas | text | Como foi resolvido | nullable |

---

#### **mensagens_fora_horario**

Buffer para mensagens fora do horário comercial (08h-20h).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| cliente_id | uuid | FK -> clientes | indexed |
| conversa_id | uuid | FK -> conversations | indexed |
| conteudo | text | Mensagem | |
| agendar_para | timestamptz | Quando será enviada | indexed |
| created_at | timestamptz | Criado em | DEFAULT now() |

---

### 3.7 Monitoring & Quality (Qualidade)

#### **avaliacoes_qualidade**

Avaliações de qualidade das conversas (automáticas ou gestor).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| conversa_id | uuid | FK -> conversations | indexed |
| naturalidade | integer | Score 1-10 | |
| persona | integer | Aderência à persona (1-10) | |
| objetivo | integer | Atingiu objetivo (1-10) | |
| satisfacao | integer | Satisfação do médico (1-10) | |
| score_geral | integer | Média geral | indexed |
| avaliador | varchar | auto ou gestor | indexed |
| notas | text | Observações | |
| tags | text[] | Tags (ex: "personality_too_corporate") | GIN indexed |
| criada_em | timestamptz | Criado em | DEFAULT now() |

---

#### **metricas_deteccao_bot**

Quando e como um médico percebe que é bot.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| cliente_id | uuid | FK -> clientes | indexed |
| conversa_id | uuid | FK -> conversations | indexed |
| mensagem | text | O que o médico disse | |
| padrao_detectado | text | Regex que matchou | |
| trecho | text | Parte que indicou bot | |
| falso_positivo | boolean | Marcado pelo gestor | |
| created_at | timestamptz | Criado em | DEFAULT now() |

---

#### **metricas_conversa**

KPIs agregados por conversa.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| conversa_id | uuid | FK -> conversations | unique, indexed |
| duracao_minutos | integer | Duração total | |
| mensagens_medico | integer | Mensagens do médico | |
| mensagens_julia | integer | Mensagens de Júlia | |
| tempo_resposta_medio | numeric | Tempo médio resposta | |
| taxa_conclusao | numeric | % de conclusão do objetivo | |
| calculado_em | timestamptz | Último cálculo | DEFAULT now() |

---

#### **metricas_pipeline_diarias**

Métricas diárias do pipeline (inbound, outbound, events).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| data | date | Data | unique, indexed |
| mensagens_inbound | integer | Mensagens recebidas | |
| mensagens_outbound | integer | Mensagens enviadas | |
| conversas_ativas | integer | Conversas ativas | |
| handoffs_triggados | integer | Escalações | |
| opt_outs | integer | Opt-outs | |
| eventos_total | integer | Total de business_events | |
| created_at | timestamptz | Criado em | DEFAULT now() |

---

#### **data_anomalies**

Detecção automática de anomalias de integridade de dados.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| anomaly_type | text | missing_event, duplicate_interaction, status_mismatch | NOT NULL |
| entity_type | text | conversation, interaction, vaga | NOT NULL |
| entity_id | uuid | ID da entidade | NOT NULL |
| expected | text | O que era esperado | NOT NULL |
| found | text | O que foi encontrado | nullable |
| first_seen_at | timestamptz | Primeira ocorrência | DEFAULT now() |
| last_seen_at | timestamptz | Última ocorrência | DEFAULT now() |
| occurrence_count | integer | Quantas vezes | DEFAULT 1 |
| severity | text | warning, error, critical | DEFAULT 'warning' |
| details | jsonb | Detalhes adicionais | DEFAULT '{}' |
| resolved | boolean | Se foi resolvida | DEFAULT false |
| resolved_at | timestamptz | Quando resolvida | nullable |
| resolved_by | text | Quem resolveu | nullable |
| resolution_notes | text | Como resolvida | nullable |

---

### 3.8 Groups Pipeline (Extração de Vagas via Grupos)

#### **grupos_whatsapp**

Registry de grupos WhatsApp monitorados.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| jid | text | WhatsApp group JID | unique, indexed |
| nome | text | Nome do grupo | indexed |
| descricao | text | Descrição | nullable |
| tipo | text | vagas, notificacoes, outros | DEFAULT 'vagas' |
| regiao | text | Região atendida | nullable, indexed |
| hospital_id | uuid | FK -> hospitais (se grupo de hospital) | nullable |
| ativo | boolean | Se está sendo monitorado | DEFAULT true |
| monitorar_ofertas | boolean | Se extrai vagas | DEFAULT true |
| total_mensagens | integer | Total de mensagens capturadas | |
| total_ofertas_detectadas | integer | Vagas encontradas | |
| total_vagas_importadas | integer | Vagas importadas | |
| primeira_mensagem_em | timestamptz | Primeira mensagem | nullable |
| ultima_mensagem_em | timestamptz | Última mensagem | nullable, indexed |
| created_at | timestamptz | Criado em | DEFAULT now() |

---

#### **mensagens_grupo**

Mensagens capturadas dos grupos.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| grupo_id | uuid | FK -> grupos_whatsapp | indexed |
| message_id | text | ID no WhatsApp | unique |
| sender_jid | text | JID do remetente | indexed |
| conteudo | text | Texto da mensagem | |
| has_offer | boolean | Contém oferta de vaga | DEFAULT false |
| extracted_data | jsonb | Dados extraídos | nullable |
| received_at | timestamptz | Quando recebida | indexed |
| processada_em | timestamptz | Quando processada | nullable |

---

#### **vagas_grupo**

Vagas extraídas dos grupos (descoberta automática).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| grupo_id | uuid | FK -> grupos_whatsapp | indexed |
| vaga_original_id | uuid | FK -> vagas (se já existe) | nullable |
| especialidade_nome | text | Especialidade (fuzzy matching) | indexed |
| hospital_nome | text | Hospital (fuzzy matching) | indexed |
| data | date | Data extraída | indexed |
| periodo_nome | text | Período extraído | nullable |
| valor | integer | Valor em centavos | nullable |
| setor | text | Setor extraído | nullable |
| raw_text | text | Texto original | |
| extraction_confidence | numeric | Confiança (0-1) | |
| message_id | text | FK -> mensagens_grupo | indexed |
| importada_como_vaga | boolean | Se foi criada em vagas | DEFAULT false |
| importada_em | timestamptz | Quando importada | nullable |
| created_at | timestamptz | Extraída em | DEFAULT now() |

---

#### **vagas_grupo_fontes**

Rastreamento de origem de vagas.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| vaga_grupo_id | uuid | FK -> vagas_grupo | indexed |
| vaga_id | uuid | FK -> vagas | indexed |
| grupo_id | uuid | FK -> grupos_whatsapp | indexed |
| source_group_name | text | Nome do grupo original | |
| descoberta_em | timestamptz | Timestamp | DEFAULT now() |

---

#### **contatos_grupo**

Membros dos grupos (para rastreamento).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| grupo_id | uuid | FK -> grupos_whatsapp | indexed |
| jid | text | JID do WhatsApp | indexed |
| telefone | text | Telefone | indexed, nullable |
| nome | text | Nome | nullable |
| empresa | text | Empresa/hospital | indexed, nullable |
| tipo | text | membro, admin, criador | indexed |
| joined_at | timestamptz | Quando entrou | |
| left_at | timestamptz | Quando saiu | nullable |

---

#### **vagas_hospitais_bloqueados**

Hospitais excluídos de certos grupos (para não importar vagas).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| grupo_id | uuid | FK -> grupos_whatsapp | indexed |
| hospital_id | uuid | FK -> hospitais | indexed |
| razao | text | Motivo da exclusão | nullable |
| created_at | timestamptz | Criado em | DEFAULT now() |

---

### 3.9 Infraestrutura & Configuração

#### **whatsapp_instances**

Pool de instâncias WhatsApp (Evolution API).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| instance_id | varchar | ID na Evolution | unique, indexed |
| instance_name | varchar | Nome descritivo | |
| phone | varchar | Número da instância | unique |
| status | varchar | connected, disconnected, authenticating | DEFAULT 'disconnected' |
| messages_sent_today | integer | Contador diário | DEFAULT 0 |
| messages_sent_hour | integer | Contador por hora | DEFAULT 0 |
| daily_limit | integer | Limite diário | DEFAULT 100 |
| hourly_limit | integer | Limite por hora | DEFAULT 20 |
| last_message_at | timestamptz | Última mensagem | nullable |
| last_status_check | timestamptz | Último health check | nullable |
| metadata | jsonb | Extra (battery, signal, etc) | DEFAULT '{}' |
| created_at | timestamptz | Criado em | DEFAULT now() |

---

#### **app_settings**

Configurações da aplicação (environment markers, feature flags globais).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| setting_key | text | Chave | unique |
| setting_value | text | Valor | |
| data_type | text | string, integer, boolean, json | |
| environment | text | development, staging, production | indexed |
| updated_at | timestamptz | Última atualização | DEFAULT now() |

---

#### **slack_sessoes**

Session management para comandos Slack.

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| user_id | text | Slack user ID | indexed |
| conversation_context | jsonb | Contexto da conversa | |
| selected_medico_id | uuid | Médico em focus | nullable |
| ultimo_comando | text | Último comando | nullable |
| created_at | timestamptz | Criado em | DEFAULT now() |
| updated_at | timestamptz | Atualizado em | DEFAULT now() |
| expires_at | timestamptz | Válido até (TTL 30min) | indexed |

---

#### **briefing_sync_log**

Log de sincronização do briefing (Google Docs).

| Coluna | Tipo | Descrição | Constraints |
|--------|------|-----------|-------------|
| id | uuid | PK | |
| doc_hash | text | Hash MD5 do conteúdo | unique, indexed |
| doc_title | text | Título do documento | |
| conteudo_raw | text | Conteúdo bruto | |
| parseado | jsonb | Secções parseadas | |
| created_at | timestamptz | Quando sincronizou | DEFAULT now() |
| sync_status | text | success, partial, failed | |

---

---

## 4. Índices - Especificação Completa

### Índices de Lookup (B-tree)

| Índice | Tabela | Colunas | WHERE | Propósito |
|--------|--------|---------|-------|----------|
| idx_clientes_telefone | clientes | telefone | - | Busca rápida por telefone (PK efetivo) |
| idx_clientes_cpf | clientes | cpf | WHERE cpf IS NOT NULL | Lookup por CPF |
| idx_clientes_crm | clientes | crm | WHERE crm IS NOT NULL | Lookup por CRM |
| idx_clientes_email | clientes | email | WHERE email IS NOT NULL | Busca por email |
| idx_clientes_status | clientes | status | - | Filtro por status |
| idx_clientes_stage | clientes | stage_jornada | WHERE deleted_at IS NULL | Funil de conversão |
| idx_clientes_grupo_piloto | clientes | grupo_piloto | WHERE grupo_piloto = true | Médicos do piloto |
| idx_clientes_opt_out | clientes | opt_out | WHERE opt_out = false AND deleted_at IS NULL | Elegíveis para contato |
| idx_clientes_opted_out | clientes | opted_out | WHERE opted_out = false | Normalizados |

### Índices de Range Queries (B-tree com ordenação)

| Índice | Tabela | Colunas | Propósito |
|--------|--------|---------|----------|
| idx_clientes_created_at | clientes | created_at DESC | Médicos mais recentes |
| idx_conversations_last_message | conversations | last_message_at DESC | Conversas mais recentes |
| idx_conversations_last_touch_at | conversations | last_touch_at DESC | Últimos touches |
| idx_interacoes_conversa_created | interacoes | conversation_id, created_at DESC | Histórico ordenado |
| idx_fila_pendente | fila_mensagens | agendar_para | Polling de mensagens pendentes |
| idx_business_events_ts | business_events | ts DESC | Event stream timeline |

### Índices Compostos

| Índice | Tabela | Colunas | WHERE | Propósito |
|--------|--------|---------|-------|----------|
| idx_conversations_cliente_status | conversations | cliente_id, status | - | Conversas ativas por cliente |
| idx_vagas_esp_data | vagas | especialidade_id, data | WHERE status = 'aberta' | Vagas abertas por especialidade/data |
| idx_business_events_cliente_ts | business_events | cliente_id, ts DESC | - | Timeline de eventos por médico |
| idx_business_events_type_ts | business_events | event_type, ts DESC | - | Events por tipo |
| idx_business_events_vaga_ts | business_events | vaga_id, ts DESC | - | Events por vaga |
| idx_campaign_contact_lookup | campaign_contact_history | cliente_id, sent_at DESC | - | Histórico de contatos |
| idx_campanhas_status_agendar | campanhas | status, agendar_para | WHERE status = 'agendada' | Campanhas agendadas |

### Índices Vetoriais (IVF - Approximate Nearest Neighbor)

| Índice | Tabela | Coluna | Config | Propósito |
|--------|--------|--------|--------|----------|
| idx_clientes_embedding | clientes | embedding | IVF, lists=100 | RAG busca semântica (contexto) |
| idx_conhecimento_embedding | conhecimento_julia | embedding | IVF, lists=100 | RAG busca de chunks |
| idx_doctor_context_embedding | doctor_context | embedding | IVF, lists=100 | Memória semântica do médico |

**Nota:** IVF (Inverted File) com lists=100 é ideal para 50K-1M vetores. Recalcular se crescer muito.

### Índices Full-Text/Trigram (GIN)

| Índice | Tabela | Coluna | Propósito |
|--------|--------|--------|----------|
| idx_conhecimento_tags | conhecimento_julia | tags | Busca por tags |
| idx_avaliacoes_tags | avaliacoes_qualidade | tags | Busca por feedback tags |
| idx_clientes_ultima_abertura | clientes | ultima_abertura | Evitar repetição de openings |
| idx_contatos_grupo_jid | contatos_grupo | jid | Lookup JID WhatsApp |

---

## 5. Row Level Security (RLS)

### Política Padrão

Todas as tabelas operacionais têm RLS habilitado com política de service role only:

```sql
-- Exemplo (em todas as tabelas)
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_access"
ON clientes
FOR ALL
USING (auth.role() = 'service_role');

-- Alternativa para views públicas (raras)
CREATE POLICY "public_read"
ON funil_conversao
FOR SELECT
USING (true);
```

### Implicações

1. **Leitura direto do Supabase Client:** Não funciona (RLS bloqueia)
2. **Acesso via API:** Use service role key ou functions SQL (SECURITY DEFINER)
3. **Queries via aplicação:** Use `from app.services.supabase import supabase` (já usa service role internamente)

---

## 6. Funções SQL Especializadas

### Funções de Busca

#### **buscar_alvos_campanha()**

Retorna médicos elegíveis para campanhas, já filtrados por rules operacionais.

```sql
buscar_alvos_campanha(
  p_filtros jsonb DEFAULT '{}',
  p_dias_sem_contato integer DEFAULT 14,
  p_excluir_cooling boolean DEFAULT true,
  p_excluir_em_atendimento boolean DEFAULT true,
  p_contact_cap integer DEFAULT 5,
  p_limite integer DEFAULT 1000
)
RETURNS TABLE (
  id uuid,
  nome text,
  telefone text,
  especialidade_nome text,
  regiao text,
  last_outbound_at timestamptz,
  contact_count_7d integer
)
```

**Lógica de filtros:**
- Não optout
- Menos de contact_cap contatos em 7d
- Não tocados há > p_dias_sem_contato
- Não em cooling_off (se flag ativa)
- Não em conversa com humano
- Não em atendimento inbound (< 30min, se flag ativa)

**Determinismo:** ORDER BY last_outbound_at ASC NULLS FIRST (nunca tocados primeiro)

---

#### **buscar_conhecimento()**

Busca chunks do knowledge base por similaridade semântica.

```sql
buscar_conhecimento(
  query_embedding vector,
  tipo_filtro text DEFAULT NULL,
  subtipo_filtro text DEFAULT NULL,
  limite integer DEFAULT 5,
  threshold double precision DEFAULT 0.65
)
RETURNS TABLE (
  id uuid,
  arquivo text,
  secao text,
  conteudo text,
  tipo text,
  subtipo text,
  tags text[],
  similaridade double precision
)
```

---

#### **buscar_candidatos_touch_reconciliation()**

Busca mensagens que precisam de reconciliação de delivery.

```sql
buscar_candidatos_touch_reconciliation(
  p_desde timestamptz,
  p_limite integer DEFAULT 1000
)
RETURNS TABLE (
  id uuid,
  cliente_id uuid,
  provider_message_id text,
  enviada_em timestamptz,
  metadata jsonb
)
```

---

### Funções de Auditoria

#### **audit_outbound_coverage()**

Audita cobertura de eventos outbound (business_events + policy_events).

```sql
audit_outbound_coverage(
  p_start timestamptz,
  p_end timestamptz
)
RETURNS TABLE (
  source text,
  expected_count bigint,
  actual_count bigint,
  coverage_pct numeric,
  layer text,
  notes text
)
```

**Verifica:**
1. Cada interação saída tem business_event doctor_outbound?
2. Cada doctor_outbound tem policy_event message_sent?

---

#### **audit_pipeline_inbound_coverage()**

Audita cobertura de events doctor_inbound para mensagens de entrada.

```sql
audit_pipeline_inbound_coverage(
  p_start timestamptz,
  p_end timestamptz
)
RETURNS TABLE (
  source text,
  expected_count bigint,
  actual_count bigint,
  coverage_pct numeric,
  missing_ids bigint[]
)
```

---

#### **audit_status_transition_coverage()**

Audita cobertura de eventos para transições de status de vagas.

```sql
audit_status_transition_coverage(
  p_start timestamptz,
  p_end timestamptz
)
RETURNS TABLE (
  status_from text,
  status_to text,
  expected_event text,
  db_transitions bigint,
  events_found bigint,
  coverage_pct numeric,
  missing_vaga_ids uuid[]
)
```

**Transições checadas:**
- * → reservada → offer_accepted
- * → pendente_confirmacao → shift_pending_confirmation
- * → realizada → shift_completed
- * → cancelada → shift_cancelled

---

---

## 7. Dados de Alto Volume (Maintenance Notes)

### Tabelas que crescem continuamente

| Tabela | Taxa de crescimento | Retenção | Strategy |
|--------|-------------------|----------|----------|
| interacoes | +100-500/dia | Indefinida | Índices otimizados, particionamento por cliente_id considerado |
| business_events | +200-1000/dia | Indefinida | Índices ts+type, archive após 2 anos |
| fila_mensagens | +50-200/dia | Até sucesso/falha | Limpeza de rows antigas (>30 dias) |
| envios | +50-200/dia | Indefinida | Índices status+enviado_em |
| metricas_* | +1/dia | Indefinida | Agregações diárias suficientes |

### Estratégias de Otimização

1. **Índices Compostos:** Sempre usar composite (col1, col2) para queries multi-coluna
2. **Particionamento:** Considerar para interacoes por cliente_id (1M+ rows)
3. **Archiving:** Mover business_events > 2 anos para tabela archive
4. **Vacuuming:** Executar VACUUM ANALYZE mensalmente
5. **Statistics:** ANALYZE automático (default) está ok

### Queries de Maintenance

```sql
-- Verificar tamanho das tabelas
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 20;

-- Verificar índices não usados
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY tablename;

-- Recalcular IVF para vetores
REINDEX INDEX idx_conhecimento_embedding;
REINDEX INDEX idx_clientes_embedding;

-- Verificar bloat de índices
SELECT * FROM pg_stat_user_indexes
WHERE schemaname != 'pg_catalog'
ORDER BY idx_blks_read DESC;
```

---

## 8. Queries Úteis (Exemplos Frequentes)

### Conversas e Interações

```sql
-- Conversa ativa de um cliente
SELECT c.*,
       COUNT(i.id) as total_msgs,
       MAX(i.created_at) as last_at
FROM conversations c
LEFT JOIN interacoes i ON i.conversation_id = c.id
WHERE c.cliente_id = $1 AND c.status = 'active'
GROUP BY c.id
ORDER BY c.created_at DESC
LIMIT 1;

-- Histórico completo de uma conversa (ordenado)
SELECT i.*, c.nome, c.telefone
FROM interacoes i
JOIN clientes c ON i.cliente_id = c.id
WHERE i.conversation_id = $1
ORDER BY i.created_at ASC;

-- Conversas pendentes de follow-up
SELECT c.*, u.nome as medico_nome,
       MAX(i.created_at) as ultima_msg
FROM conversations c
JOIN clientes u ON c.cliente_id = u.id
LEFT JOIN interacoes i ON i.conversation_id = c.id
WHERE c.status = 'active'
  AND c.controlled_by = 'ai'
  AND c.pausado_ate IS NULL
  AND c.ultima_mensagem_em < NOW() - INTERVAL '24 hours'
GROUP BY c.id, u.id
ORDER BY c.ultima_mensagem_em ASC;
```

### Vagas e Compatibilidade

```sql
-- Vagas abertas compatíveis com médico
SELECT v.*, h.nome as hospital, e.nome as especialidade, s.nome as setor
FROM vagas v
JOIN hospitais h ON v.hospital_id = h.id
JOIN especialidades e ON v.especialidade_id = e.id
LEFT JOIN setores s ON v.setor_id = s.id
WHERE v.status = 'aberta'
  AND v.especialidade_id = (
    SELECT id FROM especialidades WHERE nome = $1
  )
  AND v.data >= CURRENT_DATE
ORDER BY v.data ASC, v.valor DESC;

-- Vagas próximas ao médico (geolocation)
SELECT v.*, h.nome,
       (6371 * acos(cos(radians($1)) * cos(radians(h.latitude)) * cos(radians(h.longitude) - radians($2)) + sin(radians($1)) * sin(radians(h.latitude)))) as distancia_km
FROM vagas v
JOIN hospitais h ON v.hospital_id = h.id
WHERE v.status = 'aberta'
  AND h.latitude IS NOT NULL
  AND h.longitude IS NOT NULL
ORDER BY distancia_km ASC
LIMIT 10;
```

### Campanhas e Outbound

```sql
-- Últimos envios por médico (para deduplicação)
SELECT c.id, c.nome, c.telefone,
       MAX(ch.sent_at) as ultimo_contato,
       COUNT(ch.id) FILTER (WHERE ch.sent_at > NOW() - INTERVAL '7 days') as contatos_7d
FROM clientes c
LEFT JOIN campaign_contact_history ch ON c.id = ch.cliente_id
WHERE c.status != 'optout'
GROUP BY c.id
HAVING COUNT(ch.id) FILTER (WHERE ch.sent_at > NOW() - INTERVAL '7 days') < 5
ORDER BY ultimo_contato ASC NULLS FIRST
LIMIT 100;

-- KPI de campanha
SELECT
  ca.nome_template,
  COUNT(DISTINCT e.cliente_id) as total_enviados,
  COUNT(DISTINCT e.cliente_id) FILTER (WHERE e.status = 'entregue') as entregues,
  COUNT(DISTINCT i.cliente_id) as com_resposta,
  ROUND(
    100.0 * COUNT(DISTINCT i.cliente_id)::numeric /
    NULLIF(COUNT(DISTINCT e.cliente_id)::numeric, 0), 2
  ) as taxa_resposta_pct
FROM campanhas ca
LEFT JOIN envios e ON ca.id = e.campanha_id
LEFT JOIN interacoes i ON e.cliente_id = i.cliente_id
  AND i.created_at >= e.enviado_em
  AND i.created_at <= e.enviado_em + INTERVAL '48 hours'
WHERE ca.ativo = true
GROUP BY ca.id, ca.nome_template
ORDER BY total_enviados DESC;
```

### Business Events e Auditoria

```sql
-- Timeline de um médico
SELECT
  be.ts,
  be.event_type,
  CASE be.event_type
    WHEN 'doctor_inbound' THEN 'Mensagem recebida'
    WHEN 'doctor_outbound' THEN 'Mensagem enviada'
    WHEN 'offer_accepted' THEN 'Oferta aceita'
    WHEN 'shift_completed' THEN 'Plantão realizado'
    ELSE be.event_type
  END as descricao,
  be.payload
FROM business_events be
WHERE be.cliente_id = $1
ORDER BY be.ts DESC
LIMIT 100;

-- Cobertura de eventos (auditoria)
SELECT * FROM audit_outbound_coverage(
  NOW() - INTERVAL '7 days',
  NOW()
);

SELECT * FROM audit_pipeline_inbound_coverage(
  NOW() - INTERVAL '7 days',
  NOW()
);
```

### Qualidade e Detecção de Bot

```sql
-- Conversas com problemas de qualidade
SELECT c.id, u.nome, u.telefone, COUNT(aq.id) as avaliacoes,
       AVG(aq.score_geral) as score_medio
FROM conversations c
JOIN clientes u ON c.cliente_id = u.id
LEFT JOIN avaliacoes_qualidade aq ON c.id = aq.conversa_id
GROUP BY c.id, u.id
HAVING AVG(aq.score_geral) < 5
ORDER BY score_medio ASC
LIMIT 20;

-- Padrões detectados como bot
SELECT padrao_detectado, COUNT(*) as ocorrencias,
       COUNT(DISTINCT cliente_id) as medicos_afetados
FROM metricas_deteccao_bot
WHERE falso_positivo = false
GROUP BY padrao_detectado
ORDER BY ocorrencias DESC;
```

### Análise de Cooling Off e Rate Limits

```sql
-- Médicos em cooling off
SELECT c.id, c.nome, c.telefone,
       ds.cooling_off,
       ds.next_allowed_at,
       EXTRACT(EPOCH FROM (ds.next_allowed_at - NOW())) / 3600 as horas_restantes,
       ds.contact_count_7d
FROM clientes c
JOIN doctor_state ds ON c.id = ds.cliente_id
WHERE ds.cooling_off = true
  AND ds.next_allowed_at > NOW()
ORDER BY ds.next_allowed_at ASC;

-- Sugestões de contato (respeitando policy)
SELECT c.id, c.nome, c.telefone,
       CASE WHEN ds.next_allowed_at IS NULL THEN 'pode_contatar'
            WHEN ds.next_allowed_at < NOW() THEN 'pode_contatar'
            ELSE 'em_cooldown'
       END as status
FROM clientes c
LEFT JOIN doctor_state ds ON c.id = ds.cliente_id
WHERE c.opt_out = false
  AND c.status != 'optout'
ORDER BY ds.next_allowed_at ASC NULLS FIRST
LIMIT 50;
```

---

## 9. Type Enums

### **send_outcome**

Detalhe do resultado de um envio de mensagem (campaign send ou queue).

```sql
CREATE TYPE send_outcome AS ENUM (
  'SENT',                          -- Enviada com sucesso
  'BLOCKED_OPTED_OUT',            -- Médico em optout
  'BLOCKED_COOLING_OFF',          -- Em período de cooldown
  'BLOCKED_NEXT_ALLOWED',         -- Tempo de espera não atingido
  'BLOCKED_CONTACT_CAP',          -- Limite de contatos atingido
  'BLOCKED_CAMPAIGNS_DISABLED',   -- Campanhas desativadas
  'BLOCKED_SAFE_MODE',            -- Sistema em safe mode
  'BLOCKED_CAMPAIGN_COOLDOWN',    -- Campaign específica em cooldown
  'DEDUPED',                       -- Deduplicada
  'FAILED_PROVIDER',               -- Erro no provider (Evolution/Twilio)
  'FAILED_VALIDATION',             -- Validação falhou
  'FAILED_RATE_LIMIT',             -- Rate limit atingido
  'FAILED_CIRCUIT_OPEN',           -- Circuit breaker aberto
  'BYPASS'                         -- Bypass (teste, admin)
);
```

---

## 10. Checklist de Operação

### Daily Operations

- [ ] Monitorar fila_mensagens (pendentes não devem acumular)
- [ ] Verificar health das whatsapp_instances
- [ ] Rodar audit_outbound_coverage para verificar integridade
- [ ] Monitorar data_anomalies (resolver criticais)
- [ ] Verificar metricas_deteccao_bot (padrões novos?)

### Weekly Maintenance

- [ ] ANALYZE em tabelas de alto volume
- [ ] Verificar índices não usados
- [ ] Revisar sugestoes_prompt
- [ ] Validar metricas_pipeline_diarias

### Monthly Maintenance

- [ ] VACUUM ANALYZE completo
- [ ] Reindex em índices vetoriais (IVF)
- [ ] Archive business_events > 90 dias (considerado)
- [ ] Backup validation
- [ ] RLS policy audit

### Runbook de Troubleshooting

**Problema:** Fila de mensagens piling up
```sql
-- Ver quais estão falhando
SELECT status, COUNT(*), AVG(tentativas) as tentativas_media
FROM fila_mensagens
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY status;

-- Ver erros específicos
SELECT motivo_falha, COUNT(*) FROM fila_mensagens
WHERE status = 'falhou'
GROUP BY motivo_falha;

-- Reprocessar (se for erro transiente)
UPDATE fila_mensagens
SET status = 'pendente', tentativas = 0
WHERE status = 'falhou'
  AND motivo_falha = 'TEMPORARY_ERROR'
  AND updated_at > NOW() - INTERVAL '24 hours';
```

**Problema:** Médico recebendo mensagens apesar de optout
```sql
-- Verificar estado
SELECT c.opt_out, c.opted_out, ds.cooling_off
FROM clientes c
LEFT JOIN doctor_state ds ON c.id = ds.cliente_id
WHERE c.telefone = $1;

-- Forçar optout
UPDATE clientes SET opt_out = true, opted_out = true, opted_out_at = NOW()
WHERE telefone = $1;

-- Verificar negócio
SELECT * FROM business_events
WHERE cliente_id = (SELECT id FROM clientes WHERE telefone = $1)
  AND event_type = 'opt_out_requested'
ORDER BY ts DESC LIMIT 1;
```

---

## 11. Definições Críticas

### Statuses de Conversa

| Status | Transições | Significado |
|--------|-----------|------------|
| active | → paused, escalated, completed, abandoned | Conversa em andamento |
| paused | → active | Pausada (cooldown) |
| escalated | → active, completed | Escalada para humano |
| completed | - | Concluída com sucesso |
| abandoned | - | Abandonada (sem resposta) |

### Stages de Jornada (clientes)

| Stage | Next | Significado |
|-------|------|------------|
| novo | aguardando_resposta | Nunca contatado |
| aguardando_resposta | nao_respondeu, respondeu | Follow-up enviado |
| respondeu | em_conversacao | Respondeu primeira vez |
| em_conversacao | qualificado, perdido | Conversa ativa |
| qualificado | cadastrado, ativo | Pronto para plantão |
| cadastrado | ativo | Completou cadastro |
| ativo | - | Ativo no sistema |
| perdido | - | Conversão falhada |
| inativo | - | Sem atividade |
| optout | - | Terminal (pediu sair) |

### Statuses de Vaga

| Status | Transições | Significado |
|--------|-----------|------------|
| aberta | reservada, cancelada | Disponível |
| reservada | confirmada, cancelada, aberta | Médico interessado |
| confirmada | realizada, cancelada, pendente_confirmacao | Médico confirmou |
| pendente_confirmacao | confirmada, cancelada | Aguardando confirmação pós-plantão |
| realizada | - | Plantão concluído |
| cancelada | - | Cancelada |
| anunciada | aberta, cancelada | Divulgação |
| fechada | - | Encerrada (empresa) |

---

## Referências Rápidas

### Projeto Supabase
- **Project Ref:** jyqgbzhqavgpxqacduoi
- **URL:** https://jyqgbzhqavgpxqacduoi.supabase.co

### Migração do Schema
- **Arquivo:** `/bootstrap/01-schema.sql` (9,217 linhas)
- **Versão:** 93 migrações aplicadas (a partir de 09/02/2026)

### Documentação de Referência
- **ER Diagram:** Seção 2 deste arquivo
- **RLS Policy:** Seção 5
- **Funções SQL:** Seção 6
- **Exemplos de Queries:** Seção 8

---

## 12. Checklist para Novas Tabelas

Ao criar uma nova tabela, verificar:

### 1. Estrutura

- [ ] PK é UUID com `DEFAULT gen_random_uuid()`
- [ ] `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- [ ] `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- [ ] Trigger de `updated_at` configurado
- [ ] Constraints CHECK para validação de domínio
- [ ] NOT NULL em colunas obrigatórias

### 2. Foreign Keys

- [ ] Todas as FKs declaradas explicitamente
- [ ] **Índice criado para cada FK** (PostgreSQL não cria automaticamente)
- [ ] ON DELETE apropriado (RESTRICT, CASCADE, SET NULL)

### 3. Segurança (RLS)

- [ ] `ALTER TABLE tabela ENABLE ROW LEVEL SECURITY;`
- [ ] Policy para `service_role` (backend)
- [ ] Policy para `authenticated` (se dashboard precisar)
- [ ] Policy bloqueando `anon` (se dados sensíveis)
- [ ] COMMENT documentando propósito das policies

### 4. Performance

- [ ] Índices em colunas de busca frequente
- [ ] Índices compostos para queries com múltiplos filtros
- [ ] ANALYZE após carga de dados significativa

---

## 13. Auditoria e Histórico

### Sprint 57 (2026-02-09) - Database Security & Performance

**Correções aplicadas:**
- RLS habilitado em 6 tabelas (helena_sessoes, circuit_transitions, warmup_schedule, chip_daily_snapshots, fila_mensagens_dlq, market_intelligence_daily)
- search_path adicionado em 14 functions SECURITY DEFINER
- 31 índices criados em colunas FK
- 5 índices não utilizados removidos (~4.4 MB)
- Tabela obsoleta `campanhas_deprecated` removida

**Métricas finais:**

| Métrica | Antes | Depois |
|---------|-------|--------|
| Tabelas sem RLS | 7 | 0 |
| FKs sem índice | 31 | 0 |
| Functions sem search_path | 14 | 0 |

**Próxima auditoria:** 2026-05-09

---

**Última revisão:** 09/02/2026
**Responsável:** Time de Arquitetura
**Status:** Produção

