# Slack - Logica e Regras de Negocio

> Documentacao completa da integracao Slack do Agente Julia

---

## Visao Geral

A integracao Slack do Agente Julia possui **dois componentes principais**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SLACK                                           │
├────────────────────────────────┬────────────────────────────────────────────┤
│     SISTEMA DE NOTIFICACOES    │          AGENTE CONVERSACIONAL             │
│                                │                                             │
│  • Alertas de handoff          │  • Comandos em linguagem natural           │
│  • Plantoes reservados         │  • Gestao de medicos via chat              │
│  • Confirmacao de plantao      │  • Consultas e acoes operacionais          │
│  • Erros do sistema            │  • Interface principal do gestor           │
│  • Reports diarios             │                                             │
│                                │                                             │
│  Webhook unidirecional         │  Webhook bidirecional + LLM                │
└────────────────────────────────┴────────────────────────────────────────────┘
```

---

## 1. Configuracao

### Variaveis de Ambiente

| Variavel | Tipo | Obrigatoria | Descricao |
|----------|------|-------------|-----------|
| `SLACK_WEBHOOK_URL` | URL | Sim (notificacoes) | Webhook para enviar mensagens ao canal |
| `SLACK_CHANNEL` | String | Nao | Canal destino (default: `#julia-gestao`) |
| `SLACK_BOT_TOKEN` | xoxb-* | Sim (comandos) | Token do bot para API do Slack |
| `SLACK_SIGNING_SECRET` | String | Sim | Secret para validar assinaturas HMAC |

### Exemplo .env

```bash
# Notificacoes (webhook simples)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/xxx

# Canal destino
SLACK_CHANNEL=#julia-gestao

# Bot (para comandos interativos)
SLACK_BOT_TOKEN=xoxb-xxx-xxx-xxx
SLACK_SIGNING_SECRET=xxx
```

---

## 2. Arquitetura de Componentes

### Estrutura de Arquivos

```
app/
├── services/
│   ├── slack.py                    # Notificacoes via webhook
│   ├── slack_comandos.py           # Processador de comandos
│   └── slack/
│       ├── __init__.py             # Exports publicos
│       ├── agent.py                # Orquestrador do agente (AgenteSlack)
│       ├── session.py              # Gerenciador de sessao (SessionManager)
│       ├── tool_executor.py        # Executor de tools (ToolExecutor)
│       ├── prompts.py              # System prompts
│       └── formatter/
│           ├── primitives.py       # bold(), code(), lista()
│           ├── converters.py       # formatar_telefone(), formatar_data()
│           └── templates.py        # template_metricas(), template_medico()
│
├── tools/slack/
│   ├── __init__.py                 # SLACK_TOOLS + TOOLS_CRITICAS
│   ├── metricas.py                 # buscar_metricas, comparar_periodos
│   ├── medicos.py                  # buscar_medico, bloquear, desbloquear
│   ├── mensagens.py                # enviar_mensagem, buscar_historico
│   ├── vagas.py                    # buscar_vagas, reservar_vaga
│   ├── sistema.py                  # status, pausar, retomar, toggles
│   ├── briefing.py                 # processar_briefing, sincronizar
│   └── grupos.py                   # aprovar_vaga, rejeitar_vaga, aliases
│
└── api/routes/
    └── webhook.py                  # POST /webhook/slack
```

---

## 3. Sistema de Notificacoes

### Tipos de Notificacao

| Tipo | Funcao | Cor | Quando Dispara |
|------|--------|-----|----------------|
| Plantao reservado | `notificar_plantao_reservado()` | Verde (#00ff00) | Medico confirma vaga |
| Handoff necessario | `notificar_handoff()` | Dinamica* | Trigger de handoff |
| Handoff resolvido | `notificar_handoff_resolvido()` | Verde (#4CAF50) | Gestor resolve handoff |
| Confirmacao plantao | `notificar_confirmacao_plantao()` | N/A (Block Kit) | D+1 apos plantao |
| Erro sistema | `notificar_erro()` | Vermelho (#ff0000) | Erro critico capturado |

*Cores de handoff por tipo:
- `pedido_humano`: Azul (#2196F3)
- `juridico`: Vermelho (#F44336)
- `sentimento_negativo`: Laranja (#FF9800)
- `baixa_confianca`: Roxo (#9C27B0)
- `manual`: Verde (#4CAF50)

### Formato de Mensagens

#### Plantao Reservado

```json
{
    "text": "Plantao reservado!",
    "attachments": [{
        "color": "#00ff00",
        "title": "Novo plantao fechado pela Julia",
        "fields": [
            {"title": "Medico", "value": "Dr. Carlos Silva", "short": true},
            {"title": "Hospital", "value": "Hospital ABC", "short": true},
            {"title": "Data", "value": "15/12/2024", "short": true},
            {"title": "Periodo", "value": "Noturno", "short": true},
            {"title": "Valor", "value": "R$ 2.500", "short": true}
        ],
        "footer": "Agente Julia",
        "ts": 1702567890
    }]
}
```

#### Handoff Necessario

```json
{
    "text": "Handoff necessario!",
    "attachments": [{
        "color": "#2196F3",
        "title": "Handoff necessario!",
        "fields": [
            {"title": "Medico", "value": "Dr. Carlos", "short": true},
            {"title": "Telefone", "value": "11999887766", "short": true},
            {"title": "Motivo", "value": "Pediu para falar com humano", "short": false},
            {"title": "Tipo", "value": "pedido_humano", "short": true}
        ],
        "actions": [{
            "type": "button",
            "text": "Abrir no Chatwoot",
            "url": "https://chatwoot.../conversations/123"
        }],
        "footer": "Conversa ID: abc123",
        "ts": 1702567890
    }]
}
```

#### Confirmacao de Plantao (Block Kit com botoes)

```json
{
    "text": "Confirmacao: plantao 15/12 - Hospital ABC",
    "blocks": [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Confirmacao de Plantao"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": "*Hospital:*\nHospital ABC"},
                {"type": "mrkdwn", "text": "*Data:*\n15/12/2024"},
                {"type": "mrkdwn", "text": "*Horario:*\n19:00 - 07:00"},
                {"type": "mrkdwn", "text": "*Medico:*\nDr. Carlos"}
            ]
        },
        {
            "type": "actions",
            "block_id": "confirmacao_<vaga_id>",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Realizado"},
                    "style": "primary",
                    "action_id": "confirmar_realizado",
                    "value": "<vaga_id>"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Nao ocorreu"},
                    "style": "danger",
                    "action_id": "confirmar_nao_ocorreu",
                    "value": "<vaga_id>"
                }
            ]
        }
    ]
}
```

---

## 4. Agente Conversacional

### Fluxo de Processamento

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GESTOR ENVIA MENSAGEM NO SLACK                                             │
│  Ex: "@julia quantos responderam hoje?"                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEBHOOK /webhook/slack                                                      │
│  1. Verificar assinatura HMAC-SHA256                                        │
│  2. Verificar timestamp (< 5 min)                                           │
│  3. Parsear payload JSON                                                    │
│  4. Se url_verification: retornar challenge                                 │
│  5. Se event_callback: agendar processamento em background                  │
│  6. Retornar 200 OK imediatamente                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SESSAO (SessionManager)                                                    │
│  • Buscar sessao existente (user_id + channel_id)                           │
│  • Se expirada (> 30 min): criar nova                                       │
│  • Carregar historico de mensagens (max 20)                                 │
│  • Carregar contexto (resultados anteriores)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VERIFICAR ACAO PENDENTE                                                    │
│  Se tem acao aguardando confirmacao:                                        │
│  • "sim", "ok", "manda" → Executar acao                                     │
│  • "nao", "cancela" → Cancelar acao                                         │
│  • Outro → Continuar conversa normal                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VERIFICAR BRIEFING PENDENTE                                                │
│  Se tem briefing aguardando aprovacao:                                      │
│  • Processar resposta do gestor                                             │
│  • Aprovar/rejeitar/ajustar plano                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CHAMAR LLM (Claude Haiku)                                                  │
│  • System prompt com contexto atual                                         │
│  • Historico da sessao                                                      │
│  • Tools disponiveis (27 tools)                                             │
│  • max_tokens: 1024                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PROCESSAR RESPOSTA                                                         │
│  Se LLM retornou tool_use:                                                  │
│  • Verificar se tool eh critica                                             │
│    ├─ SIM: Guardar acao pendente + retornar preview                         │
│    └─ NAO: Executar tool diretamente                                        │
│  • Salvar resultado no contexto                                             │
│  • Chamar LLM novamente para formatar resposta                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SALVAR SESSAO                                                              │
│  • Adicionar mensagem ao historico                                          │
│  • Limitar a 20 ultimas mensagens                                           │
│  • Atualizar expires_at (+30 min)                                           │
│  • Upsert no banco                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENVIAR RESPOSTA PARA SLACK                                                 │
│  "Hoje tiveram 12 respostas de 45 envios (27%)"                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Persona no Slack

A Julia no Slack mantem a mesma persona, adaptada para contexto de gestao:

| Aspecto | Valor |
|---------|-------|
| Papel | Colega de trabalho (nao assistente formal) |
| Tom | Informal: "vc", "pra", "ta", "blz" |
| Concisao | Respostas curtas e diretas |
| Emojis | Moderacao (1-2 por conversa) |
| Contexto | Como se estivesse ao lado do gestor no escritorio |

### System Prompt

```
Voce eh a Julia, escalista virtual da Revoluna. O gestor esta conversando
com voce pelo Slack para gerenciar medicos e plantoes.

## Sua Personalidade
- Voce eh uma colega de trabalho, nao um assistente formal
- Use portugues informal: "vc", "pra", "ta", "blz"
- Seja concisa - respostas curtas e diretas
- Use emoji com moderacao (1-2 por conversa no maximo)

## Regras Importantes

1. **Acoes Criticas** - Para acoes que modificam dados, SEMPRE:
   - Mostre um preview claro do que vai fazer
   - Peca confirmacao explicita
   - So execute apos o gestor confirmar

2. **Acoes de Leitura** - Para consultas, execute direto

3. **Dados Reais** - NUNCA invente dados

4. **Contexto** - Use o historico da conversa
```

---

## 5. Gerenciamento de Sessao

### Regras de Sessao

| Regra | Valor | Descricao |
|-------|-------|-----------|
| Identificador | `user_id` + `channel_id` | Unica por usuario por canal |
| TTL | 30 minutos | Sliding window (renova a cada interacao) |
| Historico max | 20 mensagens | Ultimas 20 sao mantidas |
| Persistencia | Tabela `slack_sessoes` | PostgreSQL via Supabase |

### Tabela: slack_sessoes

```sql
CREATE TABLE slack_sessoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    mensagens JSONB DEFAULT '[]',        -- Historico de conversa
    contexto JSONB DEFAULT '{}',         -- Resultados anteriores
    acao_pendente JSONB,                 -- Tool aguardando confirmacao
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '30 minutes',

    UNIQUE(user_id, channel_id)
);

CREATE INDEX idx_slack_sessoes_user_channel ON slack_sessoes(user_id, channel_id);
CREATE INDEX idx_slack_sessoes_expires ON slack_sessoes(expires_at);
```

### Ciclo de Vida

```
1. PRIMEIRA MENSAGEM DO GESTOR
   • Buscar sessao por user_id + channel_id
   • Nao existe → Criar nova sessao vazia

2. MENSAGEM SUBSEQUENTE (< 30 min)
   • Buscar sessao existente
   • Carregar mensagens e contexto
   • Renovar expires_at (+30 min)

3. MENSAGEM APOS 30 MIN
   • Buscar sessao existente
   • expires_at < now() → Criar nova sessao
   • Historico anterior eh perdido

4. SALVAR SESSAO
   • Limitar mensagens a 20 ultimas
   • Salvar contexto atualizado
   • Atualizar updated_at e expires_at
```

### Contexto da Sessao

O contexto armazena resultados de tools anteriores para referencia:

```json
{
    "ultimo_buscar_metricas": {
        "success": true,
        "metricas": {"enviadas": 45, "respostas": 12}
    },
    "ultimo_listar_medicos": {
        "success": true,
        "medicos": [{"nome": "Dr. Carlos", "telefone": "11999887766"}]
    },
    "briefing_aprovado": {
        "id": "abc123",
        "doc_nome": "Briefing Semana 50"
    }
}
```

---

## 6. Tools Disponiveis

### Catalogo Completo (27 tools)

#### Metricas (2)

| Tool | Descricao | Critica |
|------|-----------|---------|
| `buscar_metricas` | Busca metricas do periodo (hoje, semana, mes) | Nao |
| `comparar_periodos` | Compara dois periodos | Nao |

#### Medicos (4)

| Tool | Descricao | Critica |
|------|-----------|---------|
| `buscar_medico` | Busca por telefone ou nome | Nao |
| `listar_medicos` | Lista medicos com filtros | Nao |
| `bloquear_medico` | Bloqueia medico | **Sim** |
| `desbloquear_medico` | Desbloqueia medico | **Sim** |

#### Mensagens (2)

| Tool | Descricao | Critica |
|------|-----------|---------|
| `enviar_mensagem` | Envia WhatsApp para medico | **Sim** |
| `buscar_historico` | Busca conversa anterior | Nao |

#### Vagas (2)

| Tool | Descricao | Critica |
|------|-----------|---------|
| `buscar_vagas` | Lista vagas disponiveis | Nao |
| `reservar_vaga` | Reserva vaga para medico | **Sim** |

#### Sistema (6)

| Tool | Descricao | Critica |
|------|-----------|---------|
| `status_sistema` | Status atual da Julia | Nao |
| `buscar_handoffs` | Handoffs pendentes | Nao |
| `pausar_julia` | Pausa envios automaticos | **Sim** |
| `retomar_julia` | Retoma envios automaticos | **Sim** |
| `toggle_campanhas` | Liga/desliga campanhas | **Sim** |
| `toggle_ponte_externa` | Liga/desliga ponte externa | **Sim** |

#### Briefing (2)

| Tool | Descricao | Critica |
|------|-----------|---------|
| `processar_briefing` | Le/analisa briefing Google Docs | Nao |
| `sincronizar_briefing` | Forca sync imediato | **Sim** |

#### Grupos WhatsApp (9)

| Tool | Descricao | Critica |
|------|-----------|---------|
| `listar_vagas_revisao` | Vagas aguardando aprovacao | Nao |
| `aprovar_vaga_grupo` | Aprova vaga extraida | **Sim** |
| `rejeitar_vaga_grupo` | Rejeita vaga extraida | **Sim** |
| `detalhes_vaga_grupo` | Detalhe completo da vaga | Nao |
| `estatisticas_grupos` | Stats de captura | Nao |
| `adicionar_alias_hospital` | Add alias de hospital | **Sim** |
| `buscar_hospital` | Busca hospital | Nao |
| `metricas_pipeline_grupos` | Metricas do pipeline | Nao |
| `status_fila_grupos` | Status da fila | Nao |

### Tools Criticas

Tools que modificam dados requerem confirmacao explicita:

```python
TOOLS_CRITICAS = {
    "enviar_mensagem",
    "bloquear_medico",
    "desbloquear_medico",
    "reservar_vaga",
    "pausar_julia",
    "retomar_julia",
    "toggle_campanhas",
    "toggle_ponte_externa",
    "aprovar_vaga_grupo",
    "rejeitar_vaga_grupo",
    "adicionar_alias_hospital",
}
```

---

## 7. Sistema de Confirmacao

### Fluxo de Confirmacao

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GESTOR: "@julia manda msg pro 11999887766 oferecendo vaga de cardio"       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LLM ESCOLHE TOOL: enviar_mensagem                                          │
│  Tool esta em TOOLS_CRITICAS → NAO executar ainda                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  GUARDAR ACAO PENDENTE                                                      │
│  session.acao_pendente = {                                                  │
│      "tool_name": "enviar_mensagem",                                        │
│      "tool_input": {"telefone": "11999887766", "tipo": "oferta"},           │
│      "tool_id": "abc123"                                                    │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  JULIA RESPONDE COM PREVIEW                                                 │
│  "Vou mandar msg pro `11 99988-7766` (*oferta*).                            │
│                                                                              │
│  Posso enviar?"                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  GESTOR RESPONDE                                                            │
│  • "sim" / "ok" / "manda" / "pode" → EXECUTA                                │
│  • "nao" / "cancela" / "deixa" → CANCELA                                    │
│  • Outro texto → Continua conversa (mantem acao pendente)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Palavras de Confirmacao

```python
# Palavras que CONFIRMAM a acao
confirmacoes = [
    "sim", "s", "yes", "y", "ok", "pode",
    "manda", "envia", "blz", "beleza", "confirma", "confirmo"
]

# Palavras que CANCELAM a acao
cancelamentos = [
    "nao", "n", "no", "cancela", "para", "nope", "deixa"
]
```

### Previews por Tipo de Acao

| Tool | Preview Gerado |
|------|----------------|
| `enviar_mensagem` | "Vou mandar msg pro `11 99988-7766` (*oferta*). Posso enviar?" |
| `bloquear_medico` | "Vou bloquear o `11 99988-7766` (motivo: reclamou). Confirma?" |
| `desbloquear_medico` | "Vou desbloquear o `11 99988-7766`. Confirma?" |
| `reservar_vaga` | "Vou reservar a vaga do dia *15/12* pro `11 99988-7766`. Confirma?" |
| `pausar_julia` | "Vou *pausar* os envios automaticos. Confirma?" |
| `retomar_julia` | "Vou *retomar* os envios automaticos. Confirma?" |

---

## 8. Seguranca

### Validacao de Webhook

```python
def _verificar_assinatura_slack(body: bytes, timestamp: str, signature: str) -> bool:
    """
    Valida requisicao usando HMAC-SHA256.

    1. Verificar timestamp (< 5 min) - previne replay attacks
    2. Calcular: sig_basestring = "v0:{timestamp}:{body}"
    3. Calcular: hmac = HMAC-SHA256(SIGNING_SECRET, sig_basestring)
    4. Comparar com assinatura recebida usando compare_digest()
    """
```

### Protecoes Implementadas

| Protecao | Descricao | Status |
|----------|-----------|--------|
| HMAC-SHA256 | Valida origem do request | ✅ |
| Timestamp | Previne replay attacks (5 min) | ✅ |
| Bot filter | Ignora mensagens de bots | ✅ |
| Tool confirmation | Acoes criticas requerem confirmacao | ✅ |

### Vulnerabilidades Conhecidas

| Risco | Severidade | Status | Mitigacao |
|-------|------------|--------|-----------|
| Prompt injection | Alta | Pendente | Sanitizar input |
| Sem rate limiting | Media | Pendente | Implementar 10 msg/min |
| Sem timeout de tool | Media | Pendente | Implementar 30s timeout |
| Token em logs | Media | Pendente | Mascarar em logs |

---

## 9. Banco de Dados

### Tabelas Relacionadas

#### slack_sessoes

Armazena sessoes de conversa do agente.

```sql
-- Ver secao 5 para schema completo
```

#### slack_comandos

Historico de comandos para auditoria.

```sql
CREATE TABLE slack_comandos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comando TEXT NOT NULL,              -- Comando parseado
    argumentos TEXT[] DEFAULT NULL,     -- Args extraidos
    texto_original TEXT NOT NULL,       -- Texto completo
    user_id TEXT NOT NULL,
    user_name TEXT,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    message_ts TEXT,                    -- Timestamp do Slack
    resposta TEXT,                      -- Resposta gerada
    respondido BOOLEAN DEFAULT FALSE,
    respondido_em TIMESTAMPTZ,
    erro TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_slack_comandos_user ON slack_comandos(user_id);
CREATE INDEX idx_slack_comandos_data ON slack_comandos(created_at DESC);
```

---

## 10. Exemplos de Uso

### Consultar Metricas

```
Gestor: @julia como foi o dia?
Julia:  Dia bom!
        • Enviadas: 45
        • Respostas: 12 (27%)
        • Interessados: 8
        • Opt-outs: 1
```

### Enviar Mensagem

```
Gestor: @julia manda uma discovery pro 11999887766
Julia:  Vou mandar msg pro `11 99988-7766` (*discovery*).

        Posso enviar?

Gestor: pode
Julia:  Enviado pro Dr. Carlos!
```

### Bloquear Medico

```
Gestor: @julia bloqueia o 11988776655, ele foi muito grosso
Julia:  Vou bloquear o `11 98877-6655` (motivo: foi muito grosso). Confirma?

Gestor: sim
Julia:  Dr. Joao bloqueado.
```

### Ver Status do Sistema

```
Gestor: @julia como vc ta?
Julia:  To bem!

        *Status:* Online
        *Campanhas:* Ativas
        *Hoje:* 45 enviadas, 12 respostas
        *Handoffs:* 2 pendentes
```

### Aprovar Vaga de Grupo

```
Gestor: @julia tem vaga pra aprovar?
Julia:  Tem 3 vagas aguardando:

        1. Hospital ABC - Cardio - 15/12 - R$ 2.500
        2. Hospital XYZ - Anestesia - 16/12 - R$ 3.000
        3. Clinica 123 - Clinica - 17/12 - R$ 1.800

Gestor: aprova a primeira
Julia:  Vou aprovar a vaga do Hospital ABC (15/12 - R$ 2.500). Confirma?

Gestor: ok
Julia:  Vaga aprovada e disponivel para ofertas!
```

---

## 11. Troubleshooting

### Webhook nao recebe eventos

| Causa | Solucao |
|-------|---------|
| Signing secret errado | Verificar SLACK_SIGNING_SECRET |
| URL incorreta | Verificar Event Subscriptions no Slack App |
| Firewall bloqueando | Liberar IPs do Slack |
| SSL invalido | Usar certificado valido |

### Bot nao responde

| Causa | Solucao |
|-------|---------|
| Bot token errado | Verificar SLACK_BOT_TOKEN |
| Sem permissoes | Adicionar scopes: chat:write, app_mentions:read |
| Canal privado | Adicionar bot ao canal |
| Mensagem de bot | Sistema ignora mensagens de bots (comportamento esperado) |

### Sessao perdida

| Causa | Solucao |
|-------|---------|
| Timeout 30 min | Comportamento esperado, iniciar nova conversa |
| Banco indisponivel | Verificar conexao Supabase |
| Erro de upsert | Verificar constraint unique(user_id, channel_id) |

### Tool nao executa

| Causa | Solucao |
|-------|---------|
| Tool critica | Aguardar confirmacao do gestor |
| LLM nao reconheceu | Reformular comando mais explicito |
| Erro de execucao | Verificar logs para erro especifico |

---

## 12. Metricas e Observabilidade

### Logs Estruturados

```python
# Padroes de log
logger.info(f"Sessao carregada para {user_id}")
logger.info(f"Executando tool: {tool_name} com params {tool_input}")
logger.error(f"Erro na API Anthropic: {e}")
logger.warning("SLACK_SIGNING_SECRET nao configurado")
```

### Metricas Recomendadas

| Metrica | Tipo | Descricao |
|---------|------|-----------|
| `slack.mensagens.recebidas` | Counter | Total de mensagens recebidas |
| `slack.mensagens.processadas` | Counter | Total processadas com sucesso |
| `slack.tools.executadas` | Counter | Por tool_name |
| `slack.sessoes.ativas` | Gauge | Sessoes nao expiradas |
| `slack.latencia.llm` | Histogram | Tempo de resposta do LLM |
| `slack.latencia.tool` | Histogram | Tempo de execucao de tool |

---

## 13. Checklist de Manutencao

### Diario

- [ ] Verificar logs de erro do webhook
- [ ] Monitorar latencia de respostas
- [ ] Verificar sessoes ativas

### Semanal

- [ ] Revisar comandos mais usados (tabela slack_comandos)
- [ ] Limpar sessoes expiradas (job de cleanup)
- [ ] Verificar metricas de uso de LLM

### Mensal

- [ ] Revisar e atualizar prompts
- [ ] Analisar erros recorrentes
- [ ] Atualizar documentacao

---

## Arquivos Relacionados

| Arquivo | Descricao |
|---------|-----------|
| `app/services/slack.py` | Notificacoes via webhook |
| `app/services/slack/agent.py` | Orquestrador do agente |
| `app/services/slack/session.py` | Gerenciador de sessao |
| `app/services/slack/tool_executor.py` | Executor de tools |
| `app/services/slack/prompts.py` | System prompts |
| `app/tools/slack/__init__.py` | Catalogo de tools |
| `app/api/routes/webhook.py` | Endpoints de webhook |
| `tests/test_agente_slack.py` | Testes do agente |
