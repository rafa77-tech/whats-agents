# Arquitetura Técnica - Agente Júlia

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ARQUITETURA GERAL                                 │
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌───────────┐ │
│  │   Médicos   │────▶│  WhatsApp   │────▶│  Evolution  │────▶│  FastAPI  │ │
│  │             │◀────│             │◀────│    API      │◀────│           │ │
│  └─────────────┘     └─────────────┘     └─────────────┘     └─────┬─────┘ │
│                                                                     │       │
│                      ┌──────────────────────────────────────────────┤       │
│                      │                                              │       │
│                      ▼                                              ▼       │
│               ┌─────────────┐                              ┌─────────────┐  │
│               │  Chatwoot   │                              │    Agente   │  │
│               │ (Supervisão │                              │    Júlia    │  │
│               │   Humana)   │                              │  (Claude)   │  │
│               └─────────────┘                              └──────┬──────┘  │
│                      │                                            │         │
│                      │         ┌──────────────────────────────────┤         │
│                      │         │                                  │         │
│                      ▼         ▼                                  ▼         │
│               ┌─────────────────────┐                    ┌─────────────┐    │
│               │      Supabase       │                    │    Slack    │    │
│               │  (PostgreSQL)       │                    │  (Gestor)   │    │
│               └─────────────────────┘                    └─────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Componentes

### 1. Evolution API (WhatsApp Gateway)

Interface com WhatsApp Business.

**Endpoints principais:**
```
POST /message/sendText/{instance}      # Enviar texto
POST /chat/sendPresence/{instance}     # Mostrar digitando
POST /chat/markMessageAsRead/{instance} # Marcar como lido
```

**Webhook events:**
- `messages.upsert` - Nova mensagem recebida
- `connection.update` - Status da conexão

**Configuração:**
```bash
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=sua_chave
EVOLUTION_INSTANCE=julia
```

---

### 2. FastAPI (Servidor Principal)

Orquestra todo o fluxo da aplicação.

**Endpoints:**
```
# Webhooks
POST /webhook/evolution     # Mensagens do WhatsApp
POST /webhook/chatwoot      # Eventos do Chatwoot

# API de Gestão
POST /api/enviar            # Envio manual
GET  /api/health            # Health check
GET  /api/stats             # Estatísticas
```

**Fluxo de mensagem recebida:**
1. Webhook Evolution recebe mensagem
2. Extrai telefone e conteúdo
3. Marca como lida (background)
4. Processa mensagem (background):
   - Mostra presença online
   - Mostra "digitando"
   - Chama agente Júlia
   - Se resposta: envia via Evolution
   - Sincroniza com Chatwoot

---

### 3. Agente Júlia (Core)

Cérebro da operação - decide o que responder.

**Fluxo de processamento:**
```
processar_mensagem(telefone, mensagem)
        │
        ▼
┌──────────────┐
│ Busca/cria   │
│ médico       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Busca/cria   │
│ conversa     │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌─────────────────┐
│ controlled_  │─NO─▶│ Salvar msg,     │
│ by = 'ai'?   │     │ retornar None   │
└──────┬───────┘     └─────────────────┘
       │ YES
       ▼
┌──────────────┐
│ Carrega      │
│ contexto:    │
│ • Dados méd. │
│ • Histórico  │
│ • Memória    │
│ • Vagas      │
│ • Diretrizes │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Chama LLM    │
│ (Claude)     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Processa     │
│ tool calls   │
└──────┬───────┘
       │
       ▼
   Retorna resposta
```

**Tools disponíveis para o agente:**
| Tool | Descrição |
|------|-----------|
| `buscar_vagas` | Consulta vagas compatíveis |
| `reservar_plantao` | Reserva vaga + notifica gestor |
| `atualizar_perfil` | Atualiza dados do médico |
| `salvar_memoria` | Salva fato em doctor_context |
| `notificar_gestor` | Cria notificação Slack/WhatsApp |
| `transferir_para_humano` | Handoff para humano |

---

### 4. Chatwoot (Supervisão)

Interface para humanos acompanharem e intervirem.

**Funcionalidades:**
- Visualiza todas as conversas em tempo real
- Vê mensagens da Júlia e do médico
- Pode assumir conversa (label "humano")
- Pode devolver para IA (remove label)
- Adiciona notas internas

**Controle via Labels:**
| Label | Ação |
|-------|------|
| Adicionar "humano" | `controlled_by='human'`, Júlia para |
| Remover "humano" | `controlled_by='ai'`, Júlia volta |

**Webhook events:**
- `conversation_updated` - Detecta mudança de labels
- `message_created` - Detecta msg do humano

---

### 5. Worker de Cadência

Dispara mensagens de prospecção respeitando rate limits.

**Rate Limits:**
```
max_por_hora: 20
max_por_dia: 100
intervalo_min: 45 segundos
intervalo_max: 180 segundos
horário: 08:00 - 20:00
dias: Segunda a Sexta
```

**Tipos de envio:**
| Tipo | Quando |
|------|--------|
| `abertura` | Primeiro contato |
| `follow_up_1` | 48h sem resposta |
| `follow_up_2` | 5 dias sem resposta |
| `follow_up_3` | 15 dias (última tentativa) |
| `oferta_vaga` | Vaga compatível com perfil |
| `reativacao` | Médico inativo há 30+ dias |

---

### 6. Sistema de Notificações

Alerta gestor sobre eventos importantes.

**Tipos:**
| Tipo | Descrição |
|------|-----------|
| `plantao_fechado` | Júlia fechou um plantão |
| `medico_cadastrado` | Novo médico cadastrado |
| `intervencao_necessaria` | Júlia precisa de ajuda |
| `erro` | Algo deu errado |

**Canais:** Slack (webhook), WhatsApp (gestor)

---

## Fluxo Principal: Mensagem Recebida

```
Médico envia "Oi, tô procurando plantão"
        │
        ▼
┌─────────────┐
│  WhatsApp   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Evolution   │──webhook──▶ POST /webhook/evolution
│ API         │
└─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  FastAPI    │
                    │  extrai:    │
                    │  • telefone │
                    │  • conteudo │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   ┌───────────┐   ┌───────────┐   ┌───────────┐
   │ Marca     │   │ Presença  │   │ Processa  │
   │ como lida │   │ online    │   │ mensagem  │
   └───────────┘   └───────────┘   └─────┬─────┘
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │ Agente      │
                                  │ Júlia       │
                                  └──────┬──────┘
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │ Envia via   │
                                  │ Evolution   │
                                  └──────┬──────┘
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │ Sync        │
                                  │ Chatwoot    │
                                  └─────────────┘

Médico recebe: "Oi! Tudo bem? Que bom que tá procurando!
               Qual sua especialidade?"
```

---

## Estrutura de Pastas (Proposta)

```
/whatsapp-api
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI + webhooks
│   ├── agent.py             # Core do agente Júlia
│   ├── database.py          # Supabase client + queries
│   ├── tools.py             # Tools do agente
│   ├── evolution.py         # Cliente Evolution API
│   ├── chatwoot.py          # Integração Chatwoot
│   └── notifications.py     # Sistema de notificações
│
├── config/
│   ├── __init__.py
│   ├── settings.py          # Variáveis de ambiente
│   └── prompts.py           # System prompt da Júlia
│
├── workers/
│   ├── __init__.py
│   ├── cadencia.py          # Worker de cadência
│   ├── briefing.py          # Leitor de Google Docs
│   └── reports.py           # Gerador de reports
│
├── scripts/
│   ├── importar_medicos.py  # Importa lista de médicos
│   └── popular_fila.py      # Popula fila de prospecção
│
├── tests/
│   ├── test_agent.py
│   ├── test_tools.py
│   └── test_persona.py      # Testes de persona
│
├── docs/                    # Documentação
├── deprecated/              # Código antigo
│
├── pyproject.toml
├── docker-compose.yml
└── Dockerfile
```

---

## Variáveis de Ambiente

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# LLM
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514

# Evolution API
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=xxx
EVOLUTION_INSTANCE=julia

# Chatwoot
CHATWOOT_URL=http://localhost:3000
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# Notificações
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
GESTOR_WHATSAPP=5511999999999

# Google Docs
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-sa.json
BRIEFING_DOC_ID=1abc...xyz

# Cadência
MAX_MSGS_POR_HORA=20
MAX_MSGS_POR_DIA=100
INTERVALO_MIN_SEG=45
INTERVALO_MAX_SEG=180
HORARIO_INICIO=08:00
HORARIO_FIM=20:00

# App
NOME_EMPRESA=Revoluna
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

---

## Busca Semântica (RAG)

O agente usa RAG para memória de longo prazo sobre cada médico.

**Fluxo:**
1. Mensagem do médico chega
2. Gera embedding da mensagem
3. Busca chunks similares em `doctor_context`:
```sql
SELECT content FROM doctor_context
WHERE cliente_id = $1
ORDER BY embedding <-> $2
LIMIT 5
```
4. Inclui chunks no contexto do prompt

**Tabelas envolvidas:**
- `clientes.embedding` - Embedding do contexto consolidado
- `doctor_context` - Chunks de memória por médico

---

## Segurança

1. **API Keys** - Nunca no código, sempre em env vars
2. **RLS** - Habilitado em todas as tabelas sensíveis
3. **Rate Limiting** - Para evitar ban e abuso
4. **Logs de Auditoria** - Todas as ações críticas logadas
5. **Opt-out** - Respeitado imediatamente
6. **LGPD** - Dados sensíveis protegidos, consentimento

---

## Escalabilidade

| Componente | Estratégia |
|------------|------------|
| FastAPI | Múltiplos workers (uvicorn --workers) |
| Workers | Múltiplas instâncias com lock distribuído |
| WhatsApp | Pool de instâncias (whatsapp_instances) |
| Banco | Supabase managed (escala automático) |
| LLM | Rate limiting por cliente |

---

## Monitoramento

| Métrica | Fonte |
|---------|-------|
| Conversas ativas | `GET /api/stats` |
| Vagas abertas | `GET /api/stats` |
| Taxa de resposta | `metricas_campanhas` |
| Handoffs | Tabela `handoffs` |
| Erros | `notificacoes_gestor` |
| Health | `GET /api/health` |
