# Banco de Dados

> Schema completo das 32 tabelas e relacionamentos

---

## Visao Geral

- **Banco:** PostgreSQL via Supabase
- **Extensoes:** pgvector (embeddings), uuid-ossp
- **RLS:** Ativo em todas as tabelas
- **Migracoes:** 30 aplicadas

---

## Diagrama ER (Simplificado)

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│  clientes   │──────<│  conversations  │>──────│  interacoes │
│  (medicos)  │       │                 │       │             │
└─────────────┘       └────────┬────────┘       └─────────────┘
      │                        │
      │                        │
      ▼                        ▼
┌─────────────┐       ┌─────────────────┐
│doctor_context│       │    handoffs     │
│  (memoria)  │       │                 │
└─────────────┘       └─────────────────┘

┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│  campanhas  │──────<│     envios      │       │    vagas    │
│             │       │                 │       │             │
└─────────────┘       └─────────────────┘       └──────┬──────┘
                                                       │
                           ┌───────────────────────────┼───────────────────────────┐
                           │                           │                           │
                           ▼                           ▼                           ▼
                    ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
                    │  hospitais  │            │especialidades│           │   setores   │
                    └─────────────┘            └─────────────┘            └─────────────┘
```

---

## Tabelas por Categoria

### Core do Agente

#### clientes

Medicos cadastrados no sistema.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| primeiro_nome | varchar | Nome |
| sobrenome | varchar | Sobrenome |
| cpf | varchar | CPF |
| crm | varchar | Registro CRM |
| especialidade | varchar | Especialidade medica |
| telefone | varchar | Telefone WhatsApp (unique) |
| email | varchar | Email |
| cidade | varchar | Cidade |
| estado | varchar(2) | UF |
| status | varchar | novo, respondeu, inativo, etc |
| opt_out | boolean | Nao quer receber mensagens |
| opt_out_data | timestamptz | Quando pediu opt-out |
| stage_jornada | text | Stage atual do funil |
| pressure_score_atual | int | Score de saturacao (0-100) |
| preferencias_detectadas | jsonb | Preferencias extraidas |
| grupo_piloto | boolean | Participa do piloto |
| contexto_consolidado | text | Resumo do historico |
| embedding | vector(1536) | Embedding para RAG |

#### conversations

Agrupamento de mensagens em conversas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| cliente_id | uuid | FK -> clientes |
| status | varchar | active, paused, escalated, completed |
| controlled_by | varchar | ai ou human |
| controlled_by_user_id | uuid | Quem esta controlando |
| escalation_reason | text | Motivo da escalacao |
| message_count | int | Total de mensagens |
| last_message_at | timestamptz | Ultima mensagem |
| chatwoot_conversation_id | text | ID no Chatwoot |

#### interacoes

Todas as mensagens trocadas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | bigint | PK |
| cliente_id | uuid | FK -> clientes |
| conversation_id | uuid | FK -> conversations |
| origem | text | medico, julia, sistema |
| tipo | text | texto, audio, imagem |
| canal | text | whatsapp |
| conteudo | text | Texto da mensagem |
| sentimento_score | int | Score de sentimento |
| classificacao_ia | jsonb | Analise do LLM |
| ai_confidence | float | Confianca da resposta |
| created_at | timestamptz | Quando foi criada |

#### handoffs

Registros de transferencia IA <-> Humano.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| conversation_id | uuid | FK -> conversations |
| from_controller | varchar | Quem estava (ai/human) |
| to_controller | varchar | Quem assumiu |
| reason | text | Motivo da troca |
| created_at | timestamptz | Quando ocorreu |

#### doctor_context

Memoria de longo prazo do agente.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| cliente_id | uuid | FK -> clientes |
| content | text | Chunk de contexto |
| embedding | vector(1536) | Para busca semantica |
| source | varchar | conversation, manual, system |
| created_at | timestamptz | Quando foi criado |

---

### Gestao de Vagas

#### vagas

Plantoes disponiveis.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| hospital_id | uuid | FK -> hospitais |
| especialidade_id | uuid | FK -> especialidades |
| setor_id | uuid | FK -> setores |
| periodo_id | uuid | FK -> periodos |
| data | date | Data do plantao |
| hora_inicio | time | Hora inicio |
| hora_fim | time | Hora fim |
| valor | int | Valor em reais |
| status | varchar | aberta, reservada, confirmada, etc |
| cliente_id | uuid | Medico que assumiu |

**Status possiveis:**
- `aberta`: Disponivel
- `reservada`: Medico interessado
- `confirmada`: Confirmada
- `cancelada`: Cancelada
- `realizada`: Concluida
- `fechada`: Encerrada
- `anunciada`: Em divulgacao

#### hospitais

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| nome | text | Nome do hospital |
| cidade | text | Cidade |
| estado | text | UF |
| endereco_formatado | text | Endereco completo |
| latitude | numeric | Coordenada |
| longitude | numeric | Coordenada |

**Dados atuais:** 85 hospitais

#### especialidades

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| nome | varchar | Nome da especialidade |

**Dados atuais:** 56 especialidades

#### setores

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| nome | text | Nome do setor |

**Dados atuais:** 9 setores (UTI, CC, PS, etc)

#### periodos

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| nome | varchar | Nome do periodo |
| index | smallint | Ordem |

**Dados atuais:** 6 periodos (Diurno, Noturno, 12h, 24h, etc)

---

### Campanhas

#### campanhas

Templates de mensagens para outreach.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | bigint | PK |
| nome_template | text | Nome do template |
| tipo_campanha | text | discovery, oferta, reativacao |
| corpo | text | Texto da mensagem |
| tom | text | Tom a ser usado |
| pressure_points | int | Pontos que adiciona ao pressure_score |
| ativo | boolean | Se esta ativa |

#### execucoes_campanhas

Instancias de execucao de campanhas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | bigint | PK |
| nome_execucao | text | Nome da execucao |
| status | text | rascunho, agendada, ativa, concluida |
| segmento_filtros | jsonb | Filtros de segmentacao |
| quantidade_alvo | int | Total de alvos |
| quantidade_enviada | int | Ja enviadas |
| quantidade_respostas | int | Respostas recebidas |

#### envios

Log de todas as mensagens enviadas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | bigint | PK |
| cliente_id | uuid | FK -> clientes |
| campanha_id | bigint | FK -> campanhas |
| conteudo_enviado | text | Mensagem enviada |
| status | text | pendente, enviada, entregue, falhou |
| enviado_em | timestamptz | Quando foi enviada |
| entregue_em | timestamptz | Quando foi entregue |
| visualizado_em | timestamptz | Quando foi lida |

#### metricas_campanhas

KPIs agregados por campanha.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | bigint | PK |
| campanha_id | bigint | FK -> campanhas |
| total_enviadas | int | Total enviadas |
| total_entregues | int | Total entregues |
| taxa_resposta_percentual | numeric | Taxa de resposta |
| respostas_positivas | int | Respostas positivas |
| opt_outs | int | Opt-outs |

---

### Gestao Julia

#### diretrizes

Diretrizes ativas que guiam o comportamento.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| tipo | text | foco, evitar, tom, meta, vip, etc |
| conteudo | text | Conteudo da diretriz |
| prioridade | int | Prioridade (maior = mais importante) |
| origem | text | google_docs, slack, sistema |
| ativo | boolean | Se esta ativa |
| expira_em | timestamptz | Quando expira |

#### feedbacks_gestor

Feedbacks do gestor sobre conversas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| conversa_id | uuid | FK -> conversations |
| interacao_id | bigint | FK -> interacoes |
| tipo | text | positivo, negativo, correcao |
| conteudo | text | Texto do feedback |
| impacto | text | aplicar_sempre, este_medico, registro |
| aplicado | boolean | Se foi aplicado |

#### reports

Reports periodicos gerados.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| tipo | text | manha, almoco, tarde, semanal |
| periodo_inicio | timestamptz | Inicio do periodo |
| periodo_fim | timestamptz | Fim do periodo |
| metricas | jsonb | Metricas coletadas |
| analise | text | Analise em texto |
| enviado_slack | boolean | Se foi enviado |

#### julia_status

Historico de status operacional.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| status | text | ativo, pausado, manutencao, erro |
| motivo | text | Motivo da mudanca |
| alterado_por | text | Quem alterou |
| alterado_via | text | slack, sistema, api |

---

### Qualidade e Metricas

#### avaliacoes_qualidade

Avaliacoes de qualidade das conversas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| conversa_id | uuid | FK -> conversations |
| naturalidade | int | Score 1-10 |
| persona | int | Score 1-10 |
| objetivo | int | Score 1-10 |
| satisfacao | int | Score 1-10 |
| score_geral | int | Media geral |
| avaliador | varchar | auto ou gestor |
| notas | text | Observacoes |

#### metricas_deteccao_bot

Registra quando medicos percebem a IA.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| cliente_id | uuid | FK -> clientes |
| conversa_id | uuid | FK -> conversations |
| mensagem | text | Mensagem do medico |
| padrao_detectado | text | Regex que matchou |
| trecho | text | Parte que indicou |
| falso_positivo | boolean | Marcado pelo gestor |

#### sugestoes_prompt

Sugestoes de melhoria do prompt.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| conversa_id | uuid | FK -> conversations |
| tipo | varchar | adicionar_regra, ajustar_tom |
| descricao | text | Descricao da sugestao |
| exemplo_ruim | text | O que nao fazer |
| exemplo_bom | text | O que fazer |
| status | varchar | pendente, implementada, rejeitada |

---

### Infraestrutura

#### whatsapp_instances

Pool de instancias WhatsApp.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| instance_id | varchar | ID na Evolution |
| instance_name | varchar | Nome |
| phone | varchar | Telefone |
| status | varchar | connected, disconnected |
| messages_sent_today | int | Contador diario |
| messages_sent_hour | int | Contador por hora |
| daily_limit | int | Limite diario |
| hourly_limit | int | Limite por hora |

#### fila_mensagens

Fila de mensagens agendadas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| cliente_id | uuid | FK -> clientes |
| conversa_id | uuid | FK -> conversations |
| conteudo | text | Mensagem a enviar |
| tipo | text | lembrete, followup, campanha |
| prioridade | int | 0-10 (maior = mais urgente) |
| status | text | pendente, enviada, falhou |
| agendar_para | timestamptz | Quando enviar |

#### briefing_sync_log

Log de sincronizacao do briefing.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id | uuid | PK |
| doc_hash | text | Hash MD5 do conteudo |
| doc_title | text | Titulo do documento |
| conteudo_raw | text | Conteudo bruto |
| parseado | jsonb | Secoes parseadas |
| created_at | timestamptz | Quando sincronizou |

---

## Indices Importantes

```sql
-- Busca de cliente por telefone
CREATE INDEX idx_clientes_telefone ON clientes(telefone);

-- Conversas ativas por cliente
CREATE INDEX idx_conversations_cliente_status ON conversations(cliente_id, status);

-- Interacoes por conversa (ordenadas)
CREATE INDEX idx_interacoes_conversa_created ON interacoes(conversation_id, created_at DESC);

-- Vagas abertas por especialidade e data
CREATE INDEX idx_vagas_esp_data ON vagas(especialidade_id, data) WHERE status = 'aberta';

-- Fila de mensagens pendentes
CREATE INDEX idx_fila_pendente ON fila_mensagens(agendar_para) WHERE status = 'pendente';
```

---

## RLS (Row Level Security)

Todas as tabelas tem RLS ativado:

```sql
-- Politica padrao (acesso via service_role)
CREATE POLICY "service_role_access"
ON public.clientes
FOR ALL
USING (auth.role() = 'service_role');
```

---

## Queries Uteis

### Buscar conversa ativa de um cliente

```sql
SELECT * FROM conversations
WHERE cliente_id = $1
  AND status = 'active'
ORDER BY created_at DESC
LIMIT 1;
```

### Historico de uma conversa

```sql
SELECT * FROM interacoes
WHERE conversation_id = $1
ORDER BY created_at ASC;
```

### Vagas compativeis

```sql
SELECT v.*, h.nome as hospital_nome, e.nome as especialidade_nome
FROM vagas v
JOIN hospitais h ON v.hospital_id = h.id
JOIN especialidades e ON v.especialidade_id = e.id
WHERE v.especialidade_id = $1
  AND v.status = 'aberta'
  AND v.data >= CURRENT_DATE
ORDER BY v.data, v.valor DESC;
```

### Metricas de periodo

```sql
SELECT
    COUNT(*) as total_mensagens,
    COUNT(DISTINCT conversation_id) as conversas,
    AVG(EXTRACT(EPOCH FROM (lead_created - created_at))) as tempo_resposta_medio
FROM interacoes
WHERE created_at BETWEEN $1 AND $2;
```
