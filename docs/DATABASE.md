# Schema do Banco de Dados

**27 tabelas** | **PostgreSQL + pgvector** | **Supabase**

---

## Diagrama de Relacionamentos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE DO AGENTE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐    │
│  │   clientes   │──────▶│  conversations   │──────▶│    handoffs      │    │
│  │  (médicos)   │       │ (controle IA/H)  │       │ (log de trocas)  │    │
│  └──────┬───────┘       └────────┬─────────┘       └──────────────────┘    │
│         │                        │                                          │
│         │                        ▼                                          │
│         │               ┌──────────────────┐                               │
│         ├──────────────▶│    interacoes    │◀─────────────────┐            │
│         │               │  (mensagens)     │                  │            │
│         │               └──────────────────┘                  │            │
│         │                                                     │            │
│         ▼                                                     │            │
│  ┌──────────────┐       ┌──────────────────┐                 │            │
│  │doctor_context│       │      envios      │─────────────────┘            │
│  │ (memória RAG)│       │ (fila de envio)  │                              │
│  └──────────────┘       └──────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          GESTÃO DA JÚLIA                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ briefing_    │   │  diretrizes  │   │   reports    │   │ julia_status │ │
│  │ config       │   │              │   │              │   │              │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘ │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │ briefing_    │   │ feedbacks_   │   │ slack_       │                    │
│  │ historico    │   │ gestor       │   │ comandos     │                    │
│  └──────────────┘   └──────────────┘   └──────────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              GESTÃO DE VAGAS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  hospitais ──┐                                                              │
│              │     ┌──────────────────┐                                     │
│  especial. ──┼────▶│      vagas       │────▶ clientes (quem fechou)        │
│              │     └──────────────────┘                                     │
│  setores ────┤                                                              │
│              │                                                              │
│  periodos ───┤                                                              │
│              │                                                              │
│  tipos_vaga ─┘                                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tabelas Principais

### CLIENTES (Médicos)

Cadastro central de médicos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `telefone` | varchar | **UNIQUE** - Identificador principal |
| `primeiro_nome`, `sobrenome` | varchar | Nome |
| `crm` | varchar | Número do CRM |
| `especialidade` | varchar | Especialidade médica |
| `stage_jornada` | text | Estágio no funil (ver valores) |
| `opt_out` | boolean | Pediu para não receber msgs |
| `pressure_score_atual` | int | Score de saturação (0-100) |
| `contexto_consolidado` | text | Resumo para o agente |
| `embedding` | vector(1536) | Embedding para RAG |
| `preferencias_detectadas` | jsonb | Ex: `{"turno": "noturno"}` |

**Valores de `stage_jornada`:**
`novo` → `msg_enviada` → `aguardando_resposta` → `respondeu` → `em_conversacao` → `qualificado` → `docs_pendentes` → `cadastrado` → `ativo`

Alternativos: `nao_respondeu`, `inativo`, `perdido`, `opt_out`

---

### CONVERSATIONS

Controle de conversas e handoff IA ↔ Humano.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `cliente_id` | uuid | FK → clientes |
| `status` | varchar | `active`, `paused`, `escalated`, `completed` |
| `controlled_by` | varchar | **`ai` ou `human`** |
| `escalation_reason` | text | Motivo da escalação |
| `message_count` | int | Total de mensagens |
| `chatwoot_conversation_id` | text | ID no Chatwoot |

---

### INTERACOES

Histórico de todas as mensagens.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | bigint | PK |
| `cliente_id` | uuid | FK → clientes |
| `conversation_id` | uuid | FK → conversations |
| `origem` | text | `entrada` (médico) ou `saida` (nós) |
| `tipo` | text | `texto`, `audio`, `imagem`, `documento` |
| `conteudo` | text | Texto da mensagem |
| `autor_tipo` | text | `medico`, `julia`, `humano` |
| `sentimento_score` | int | -100 a +100 |
| `ai_confidence` | float | Confiança da IA (0-1) |

---

### HANDOFFS

Log de trocas de controle IA ↔ Humano.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `conversation_id` | uuid | FK → conversations |
| `from_controller` | varchar | `ai` ou `human` |
| `to_controller` | varchar | `ai` ou `human` |
| `reason` | text | Motivo da troca |

---

### DOCTOR_CONTEXT

Memória de longo prazo (RAG).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `cliente_id` | uuid | FK → clientes |
| `content` | text | Chunk de contexto |
| `embedding` | vector(1536) | Para busca semântica |
| `source` | varchar | `conversation`, `manual`, `import` |

---

### DIRETRIZES

Regras que guiam o comportamento da Júlia.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `tipo` | text | Ver tipos abaixo |
| `conteudo` | text | Texto da diretriz |
| `cliente_id` | uuid | FK (se específica de um médico) |
| `vaga_id` | uuid | FK (se específica de uma vaga) |
| `prioridade` | int | Maior = mais importante |
| `origem` | text | `google_docs`, `slack`, `sistema` |
| `ativo` | boolean | Se está ativa |
| `expira_em` | timestamptz | Quando expira |

**Tipos:** `foco`, `evitar`, `tom`, `meta`, `vip`, `bloqueado`, `vaga_prioritaria`, `instrucao_geral`

---

### VAGAS

Plantões disponíveis.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `hospital_id` | uuid | FK → hospitais |
| `especialidade_id` | uuid | FK → especialidades |
| `data` | date | Data do plantão |
| `hora_inicio`, `hora_fim` | time | Horário |
| `valor` | int | Valor em reais |
| `status` | varchar | `aberta`, `reservada`, `confirmada`, `cancelada` |
| `cliente_id` | uuid | FK → clientes (quem fechou) |
| `fechada_por` | text | `julia`, `humano`, `app` |

---

### WHATSAPP_INSTANCES

Pool de chips WhatsApp com rate limiting.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `instance_id` | varchar | **UNIQUE** - ID na Evolution API |
| `status` | varchar | `connected`, `disconnected`, `banned` |
| `messages_sent_today` | int | Contador diário |
| `messages_sent_hour` | int | Contador horário |
| `daily_limit` | int | Limite diário (default: 500) |
| `hourly_limit` | int | Limite por hora (default: 50) |

---

## Queries Úteis

### Carregar diretrizes ativas
```sql
SELECT tipo, conteudo, contexto, prioridade
FROM diretrizes
WHERE ativo = true
  AND (expira_em IS NULL OR expira_em > now())
ORDER BY prioridade DESC;
```

### Verificar se médico é VIP ou bloqueado
```sql
SELECT tipo, conteudo
FROM diretrizes
WHERE cliente_id = $1
  AND tipo IN ('vip', 'bloqueado')
  AND ativo = true;
```

### Buscar contexto RAG (similaridade)
```sql
SELECT content
FROM doctor_context
WHERE cliente_id = $1
ORDER BY embedding <-> $2
LIMIT 5;
```

### Métricas do período
```sql
SELECT
  COUNT(*) FILTER (WHERE origem = 'saida') as enviadas,
  COUNT(*) FILTER (WHERE origem = 'entrada') as recebidas,
  COUNT(DISTINCT cliente_id) FILTER (WHERE origem = 'entrada') as medicos_responderam
FROM interacoes
WHERE created_at BETWEEN $1 AND $2;
```

### Conversas ativas controladas pela IA
```sql
SELECT c.*, cl.primeiro_nome, cl.especialidade
FROM conversations c
JOIN clientes cl ON c.cliente_id = cl.id
WHERE c.status = 'active'
  AND c.controlled_by = 'ai';
```

### Vagas disponíveis para especialidade
```sql
SELECT v.*, h.nome as hospital, e.nome as especialidade
FROM vagas v
JOIN hospitais h ON v.hospital_id = h.id
JOIN especialidades e ON v.especialidade_id = e.id
WHERE v.status = 'aberta'
  AND e.nome ILIKE $1
  AND v.data >= CURRENT_DATE
ORDER BY v.data;
```

---

## Tabelas Auxiliares

| Tabela | Propósito |
|--------|-----------|
| `hospitais` | Cadastro de hospitais |
| `especialidades` | Lista de especialidades |
| `setores` | UTI, PS, Centro Cirúrgico, etc |
| `periodos` | Diurno, Noturno, etc |
| `tipos_vaga` | Avulso, Fixo, Cobertura |
| `formas_recebimento` | PJ, PF, Cooperativa |
| `campanhas` | Templates de mensagens |
| `envios` | Fila de mensagens a enviar |
| `execucoes_campanhas` | Execuções de campanhas |
| `metricas_campanhas` | KPIs agregados |
| `reports` | Reports automáticos |
| `julia_status` | Status operacional |
| `briefing_config` | Config do Google Docs |
| `briefing_historico` | Histórico de leituras |
| `slack_comandos` | Log de comandos Slack |
| `report_schedule` | Agendamento de reports |
| `notificacoes_gestor` | Fila de notificações |
| `clientes_log` | Auditoria de mudanças |
| `feedbacks_gestor` | Feedbacks sobre conversas |
