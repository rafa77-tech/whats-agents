# Supervisor Channel e SSE Real-Time

**Sprint 54 - Phase 4**

Sistema de comunicação em tempo real entre supervisor humano e agente Julia, com atualizações automáticas via Server-Sent Events (SSE).

---

## Visão Geral

O sistema de Supervisor Channel e SSE permite que supervisores humanos interajam com a Julia em tempo real durante conversas com médicos, sem interferir diretamente na conversa principal.

### Componentes Principais

| Componente | Propósito | Endpoint Base |
|------------|-----------|---------------|
| **Supervisor Channel** | Chat privado supervisor-Julia | `/supervisor/channel` |
| **SSE Real-Time** | Stream de atualizações automáticas | `/dashboard/sse` |

### Casos de Uso

1. **Consulta ao agente**: Supervisor pergunta à Julia sobre contexto, histórico ou intenções
2. **Instrução com preview**: Supervisor instrui Julia a enviar mensagem específica ao médico (com aprovação prévia)
3. **Monitoramento em tempo real**: Dashboard recebe notificações automáticas de novas mensagens e mudanças de estado

---

## Supervisor Channel

Canal de comunicação privado onde o supervisor conversa com a Julia sobre uma conversa específica com um médico.

### Características

- **Contexto completo**: Julia tem acesso a histórico, memórias e perfil do médico
- **Linguagem profissional**: Julia responde ao supervisor de forma direta, sem abreviações
- **Não interfere na conversa**: Mensagens do channel não vão para o médico (exceto instruções confirmadas)
- **Histórico persistente**: Todas as mensagens são salvas na tabela `supervisor_channel`

### Tabela: supervisor_channel

```sql
CREATE TABLE supervisor_channel (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,  -- 'supervisor' | 'julia'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_supervisor_channel_conversation
    ON supervisor_channel(conversation_id, created_at);
```

**Campos metadata:**
- `type`: Tipo de mensagem (`question`, `response`, `instruction`, `instruction_confirmed`)
- `status`: Status de instrução (`pending`, `confirmed`, `rejected`)
- `preview`: Preview da mensagem gerada (para instruções)
- `instruction_id`: ID da instrução relacionada

---

## Endpoints: Supervisor Channel

### 1. GET /supervisor/channel/{conversation_id}/history

Retorna histórico completo do channel.

**Query Parameters:**
- `limit` (opcional): Número máximo de mensagens (padrão: 50)

**Response:**
```json
{
  "messages": [
    {
      "id": "uuid",
      "role": "supervisor",
      "content": "Qual a especialidade desse médico?",
      "metadata": {
        "type": "question"
      },
      "created_at": "2026-02-10T14:30:00Z"
    },
    {
      "id": "uuid",
      "role": "julia",
      "content": "Ele é cardiologista, CRM 123456-SP. Conversamos pela primeira vez há 3 dias.",
      "metadata": {
        "type": "response"
      },
      "created_at": "2026-02-10T14:30:15Z"
    }
  ]
}
```

**Comportamento:**
- Mensagens retornadas em ordem cronológica (mais antigas primeiro)
- Inclui todas as mensagens do supervisor e da Julia
- Não inclui mensagens da conversa principal com o médico

---

### 2. POST /supervisor/channel/{conversation_id}/message

Envia pergunta do supervisor e recebe resposta da Julia.

**Request Body:**
```json
{
  "content": "O médico parece interessado?"
}
```

**Response:**
```json
{
  "supervisor_message": "O médico parece interessado?",
  "julia_response": "Sim, ele perguntou sobre valores e disponibilidade. Estou aguardando confirmação de documentos.",
  "message_id": "uuid"
}
```

**Comportamento:**
1. Salva mensagem do supervisor
2. Monta contexto completo (conversa, histórico, memórias)
3. Gera resposta usando Claude Sonnet (alta qualidade)
4. Salva resposta da Julia
5. Retorna resposta imediatamente

**System Prompt (Julia para Supervisor):**
- Tom profissional e direto
- Sem abreviações de WhatsApp
- Analisa a conversa e fornece insights
- Não fala como se estivesse conversando com o médico

---

### 3. POST /supervisor/channel/{conversation_id}/instruct

Cria instrução com preview da mensagem.

**Request Body:**
```json
{
  "instruction": "Pergunte se ele pode começar na próxima semana"
}
```

**Response:**
```json
{
  "id": "uuid",
  "instruction": "Pergunte se ele pode começar na próxima semana",
  "preview_message": "Oi Dr! Consegue começar na proxima semana já? Temos vagas abertas",
  "status": "pending"
}
```

**Comportamento:**
1. Recebe instrução do supervisor
2. Monta contexto da conversa
3. Gera preview usando Claude Sonnet
4. Salva instrução com status `pending`
5. **NÃO envia ao médico** até confirmação

**System Prompt (Julia para Médico):**
- Tom da Julia: informal, curto, usa "vc", "pra", "blz"
- Mensagem de 1-3 linhas
- Segue fielmente a instrução do supervisor
- Faz sentido no contexto da conversa

---

### 4. POST /supervisor/channel/{conversation_id}/instruct/{instruction_id}/confirm

Confirma e envia a mensagem ao médico.

**Response:**
```json
{
  "success": true,
  "message_sent": "Oi Dr! Consegue começar na proxima semana já? Temos vagas abertas",
  "message_id": "uuid"
}
```

**Comportamento:**
1. Busca instrução com status `pending`
2. Busca chip ativo para envio
3. Envia mensagem via WhatsApp (`enviar_via_chip`)
4. Registra interação na tabela `interacoes`
5. Atualiza status da instrução para `confirmed`
6. Salva confirmação no channel
7. Atualiza `last_message_at` da conversa

**Origem da Interação:** `supervisor_instruction`
**Autor:** `Julia (instruida)`

---

### 5. POST /supervisor/channel/{conversation_id}/instruct/{instruction_id}/reject

Rejeita instrução sem enviar mensagem.

**Response:**
```json
{
  "success": true,
  "status": "rejected"
}
```

**Comportamento:**
1. Busca instrução com status `pending`
2. Atualiza status para `rejected`
3. **Não envia** mensagem ao médico
4. Supervisor pode criar nova instrução

---

## SSE (Server-Sent Events)

Stream de eventos em tempo real para atualização automática do dashboard.

### Endpoint

**GET /dashboard/sse/conversations/{conversation_id}**

Abre conexão SSE para receber eventos de uma conversa específica.

---

## Eventos SSE

| Evento | Trigger | Data |
|--------|---------|------|
| `connected` | Conexão estabelecida | `{"conversation_id": "uuid"}` |
| `new_message` | Nova mensagem na conversa | `{"last_message_at": "timestamp"}` |
| `control_change` | Mudança de controle (ai/human) | `{"controlled_by": "ai"}` |
| `pause_change` | Conversa pausada/retomada | `{"pausada_em": "timestamp"}` |
| `channel_message` | Nova mensagem no supervisor channel | `{"role": "julia", "content": "..."}` |
| `error` | Erro no stream | `{"error": "mensagem"}` |
| `: heartbeat` | Heartbeat para manter conexão | Timestamp ISO |

---

## Formato de Eventos SSE

Cada evento segue o padrão Server-Sent Events:

```
event: new_message
data: {"last_message_at": "2026-02-10T14:30:00Z"}

event: control_change
data: {"controlled_by": "human"}

: heartbeat 2026-02-10T14:30:05Z
```

**Estrutura:**
- `event:` Nome do evento
- `data:` Payload JSON
- `: ` Comentário (heartbeat)
- Linha em branco separa eventos

---

## Polling Interval

**Intervalo de polling:** 5 segundos

O servidor faz polling no banco de dados a cada 5 segundos para detectar mudanças:
- `last_message_at` em `conversations`
- `controlled_by` em `conversations`
- `pausada_em` em `conversations`
- `created_at` mais recente em `supervisor_channel`

**Heartbeat:** Enviado a cada 5 segundos para manter conexão ativa.

---

## Integração Client-Side

### JavaScript EventSource (Nativo)

```javascript
const conversationId = "uuid-da-conversa";
const eventSource = new EventSource(
  `/dashboard/sse/conversations/${conversationId}`
);

// Evento de conexão
eventSource.addEventListener("connected", (e) => {
  const data = JSON.parse(e.data);
  console.log("Conectado:", data.conversation_id);
});

// Nova mensagem
eventSource.addEventListener("new_message", (e) => {
  const data = JSON.parse(e.data);
  console.log("Nova mensagem:", data.last_message_at);
  // Recarregar histórico de mensagens
  loadMessages();
});

// Mudança de controle
eventSource.addEventListener("control_change", (e) => {
  const data = JSON.parse(e.data);
  console.log("Controle mudou para:", data.controlled_by);
  // Atualizar UI
  updateControlBadge(data.controlled_by);
});

// Nova mensagem no channel
eventSource.addEventListener("channel_message", (e) => {
  const data = JSON.parse(e.data);
  console.log("Channel:", data.role, data.content);
  // Recarregar channel
  loadChannelMessages();
});

// Erro
eventSource.addEventListener("error", (e) => {
  const data = JSON.parse(e.data);
  console.error("Erro SSE:", data.error);
});

// Reconexão automática em caso de desconexão
eventSource.onerror = (error) => {
  console.error("Conexão SSE perdida, reconectando...");
  // EventSource reconecta automaticamente
};

// Fechar conexão quando componente for desmontado
// useEffect(() => {
//   return () => {
//     eventSource.close();
//   };
// }, []);
```

---

### React Hook Personalizado

```typescript
import { useEffect, useState } from 'react';

interface SSEState {
  connected: boolean;
  lastMessageAt: string | null;
  controlledBy: string | null;
  pausedAt: string | null;
}

export function useConversationSSE(conversationId: string) {
  const [state, setState] = useState<SSEState>({
    connected: false,
    lastMessageAt: null,
    controlledBy: null,
    pausedAt: null,
  });

  useEffect(() => {
    const eventSource = new EventSource(
      `/dashboard/sse/conversations/${conversationId}`
    );

    eventSource.addEventListener('connected', () => {
      setState((prev) => ({ ...prev, connected: true }));
    });

    eventSource.addEventListener('new_message', (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({ ...prev, lastMessageAt: data.last_message_at }));
    });

    eventSource.addEventListener('control_change', (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({ ...prev, controlledBy: data.controlled_by }));
    });

    eventSource.addEventListener('pause_change', (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({ ...prev, pausedAt: data.pausada_em }));
    });

    eventSource.onerror = () => {
      setState((prev) => ({ ...prev, connected: false }));
    };

    return () => {
      eventSource.close();
    };
  }, [conversationId]);

  return state;
}
```

**Uso no componente:**

```tsx
function ConversationPage({ conversationId }: Props) {
  const sse = useConversationSSE(conversationId);

  useEffect(() => {
    if (sse.lastMessageAt) {
      // Recarregar mensagens
      refetchMessages();
    }
  }, [sse.lastMessageAt]);

  return (
    <div>
      {sse.connected ? "🟢 Ao vivo" : "🔴 Desconectado"}
      {/* ... */}
    </div>
  );
}
```

---

## Autenticação

### Supervisor Channel

**Requisito:** Autenticação via token JWT (mesma autenticação do dashboard).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Validação:**
- Token deve ser válido e não expirado
- Usuário deve ter permissão de supervisor
- Conversa deve existir

**Erro 401:** Token inválido ou ausente
**Erro 403:** Usuário sem permissão de supervisor
**Erro 404:** Conversa não encontrada

---

### SSE

**Requisito:** Mesma autenticação do Supervisor Channel.

**Limitação do EventSource:**
- EventSource nativo não permite headers customizados
- Token deve ser passado via query string ou cookie

**Opções de implementação:**

#### Opção 1: Query String (atual)
```javascript
const token = getAuthToken();
const eventSource = new EventSource(
  `/dashboard/sse/conversations/${id}?token=${token}`
);
```

**Validação no servidor:**
```python
@router.get("/conversations/{conversation_id}")
async def stream_conversation(conversation_id: str, token: str):
    verify_jwt_token(token)  # Lança 401 se inválido
    # ...
```

#### Opção 2: Cookie HttpOnly
```javascript
// Cookie já enviado automaticamente
const eventSource = new EventSource(
  `/dashboard/sse/conversations/${id}`
);
```

**Validação no servidor:**
```python
from fastapi import Cookie

@router.get("/conversations/{conversation_id}")
async def stream_conversation(
    conversation_id: str,
    session: str = Cookie(None)
):
    verify_session_cookie(session)
    # ...
```

**Recomendação:** Usar Cookie HttpOnly para maior segurança (evita exposição de token em logs).

---

## Headers de Resposta SSE

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**X-Accel-Buffering: no**
- Desabilita buffering em proxies nginx
- Garante entrega imediata de eventos
- Crítico para funcionamento em produção (Railway, Vercel, etc)

---

## Tratamento de Erros

### Supervisor Channel

| Código | Erro | Motivo |
|--------|------|--------|
| 400 | Bad Request | Conteúdo vazio, instrução já processada |
| 401 | Unauthorized | Token ausente ou inválido |
| 403 | Forbidden | Usuário sem permissão |
| 404 | Not Found | Conversa ou instrução não encontrada |
| 500 | Internal Server Error | Erro no LLM, banco, ou envio WhatsApp |
| 503 | Service Unavailable | Nenhum chip disponível para envio |

**Resposta de erro:**
```json
{
  "detail": "Mensagem de erro detalhada"
}
```

---

### SSE

**Erro emitido via evento:**
```
event: error
data: {"error": "conversation_not_found"}
```

**Desconexão automática:**
- Conversa deletada
- Token expirado
- Erro crítico no servidor

**Reconexão:**
- EventSource reconecta automaticamente após desconexão
- Intervalo de reconexão: 3 segundos (padrão do browser)
- Cliente deve validar estado após reconexão

---

## Troubleshooting

### Problema: SSE não recebe eventos

**Sintomas:**
- Conexão estabelece (`connected` recebido)
- Eventos não chegam quando há mudanças

**Diagnóstico:**
1. Verificar polling interval (5s)
2. Verificar logs do servidor
3. Testar mudança manual no banco:
   ```sql
   UPDATE conversations
   SET last_message_at = NOW()
   WHERE id = 'uuid';
   ```

**Solução:**
- Verificar índices nas tabelas (`conversations`, `supervisor_channel`)
- Aumentar timeout de conexão no proxy/load balancer
- Verificar header `X-Accel-Buffering: no`

---

### Problema: Instrução não envia ao médico

**Sintomas:**
- Preview gerado corretamente
- Confirmação retorna 503 ou 500

**Diagnóstico:**
1. Verificar chips disponíveis:
   ```sql
   SELECT * FROM chips WHERE status = 'active';
   ```
2. Verificar associação chip-conversa:
   ```sql
   SELECT * FROM conversation_chips
   WHERE conversa_id = 'uuid' AND active = true;
   ```
3. Verificar logs do `enviar_via_chip`

**Solução:**
- Ativar pelo menos 1 chip
- Associar chip à conversa
- Verificar conexão Evolution API

---

### Problema: Julia responde em linguagem errada

**Sintomas:**
- Resposta ao supervisor com abreviações ("vc", "blz")
- Preview muito formal ou muito longo

**Diagnóstico:**
1. Verificar qual endpoint foi chamado
2. Verificar system prompt gerado

**Solução:**
- `/message`: Julia responde profissionalmente (supervisor)
- `/instruct`: Julia gera mensagem informal (médico)
- Verificar `_build_supervisor_system_prompt` vs `_build_instruction_system_prompt`

---

### Problema: Conexão SSE cai frequentemente

**Sintomas:**
- Reconexões a cada poucos segundos
- Eventos duplicados

**Diagnóstico:**
1. Verificar timeout do load balancer (nginx, Railway)
2. Verificar heartbeat sendo enviado
3. Verificar logs de erro no servidor

**Solução:**
- Aumentar timeout: mínimo 60s (ideal 120s+)
- Garantir heartbeat a cada 5s
- Verificar `Connection: keep-alive`
- Em produção: usar proxy reverso com suporte SSE

---

### Problema: Preview não reflete instrução

**Sintomas:**
- Instrução: "Pergunte sobre disponibilidade"
- Preview: "Oi! Tudo bem?"

**Diagnóstico:**
1. Verificar se instrução foi passada corretamente
2. Verificar contexto da conversa (histórico vazio?)
3. Verificar resposta do LLM

**Solução:**
- Instruções devem ser específicas e claras
- Julia precisa de contexto mínimo (histórico + memórias)
- Se preview inadequado: rejeitar e criar nova instrução
- Considerar ajustar `_build_instruction_system_prompt`

---

## Monitoramento

### Métricas Recomendadas

| Métrica | Descrição | Threshold |
|---------|-----------|-----------|
| `sse_connections_active` | Conexões SSE ativas | - |
| `sse_events_sent` | Total de eventos enviados | - |
| `channel_messages_count` | Mensagens no channel | - |
| `instruction_confirm_rate` | Taxa de confirmação de instruções | > 70% |
| `instruction_reject_rate` | Taxa de rejeição de instruções | < 30% |
| `sse_disconnect_rate` | Taxa de desconexões SSE | < 5% |
| `channel_response_time_p95` | P95 de resposta do channel | < 3s |

---

### Logs Importantes

```python
# Conexão SSE
logger.info(f"SSE conectado: {conversation_id}")
logger.info(f"SSE desconectado: {conversation_id}")

# Channel messages
logger.info(f"Channel msg: conv={conversation_id}")
logger.info(f"Instrucao criada: conv={conversation_id}, id={instruction_id}")
logger.info(f"Instrucao confirmada e enviada: conv={conversation_id}")
logger.info(f"Instrucao rejeitada: conv={conversation_id}, id={instruction_id}")

# Erros
logger.error(f"SSE init error: {e}")
logger.error(f"SSE poll error: {e}")
logger.error(f"Falha ao enviar instrucao: {result.error}")
```

---

## Considerações de Performance

### Supervisor Channel

- **Latência:** 1-3s (depende do LLM)
- **Concorrência:** Suporta múltiplos supervisores simultâneos
- **Rate Limit:** Não implementado (uso interno)
- **Custo LLM:** Médio (usa Sonnet para qualidade)

**Otimizações:**
- Limitar histórico a 30 mensagens
- Cachear contexto de médico por 1 min
- Usar Haiku para perguntas simples (futura otimização)

---

### SSE

- **Conexões simultâneas:** Limitado por workers do servidor
- **Polling overhead:** 1 query a cada 5s por conexão
- **Bandwidth:** Baixo (eventos pequenos, heartbeat apenas timestamp)
- **Memória:** ~1 MB por conexão ativa

**Otimizações:**
- Usar índices em `conversations(id, last_message_at)`
- Usar índices em `supervisor_channel(conversation_id, created_at)`
- Considerar Redis Pub/Sub para escalar (futura otimização)
- Limitar máximo de conexões por supervisor

**Escalabilidade:**
- 100 conexões SSE: ~100 queries/5s = 20 qps
- 1000 conexões SSE: ~1000 queries/5s = 200 qps
- Para > 500 conexões: migrar para Redis Pub/Sub ou WebSockets

---

## Roadmap

### Melhorias Futuras

**v1 (Atual - Sprint 54):**
- ✅ Supervisor Channel básico
- ✅ SSE com polling
- ✅ Instrução com preview

**v2 (Planejado):**
- [ ] WebSockets para substituir SSE
- [ ] Redis Pub/Sub para escalabilidade
- [ ] Rate limiting no Supervisor Channel
- [ ] Histórico de edições de preview
- [ ] Sugestões de instrução baseadas em contexto

**v3 (Futuro):**
- [ ] Multi-supervisor (vários supervisores na mesma conversa)
- [ ] Templates de instrução
- [ ] Analytics de instruções (quais funcionam melhor)
- [ ] Replay de conversa com timeline

---

## Referências

**Código:**
- `app/api/routes/supervisor_channel.py`
- `app/api/routes/sse.py`
- `app/services/llm.py` (gerar_resposta)
- `app/services/chips/sender.py` (enviar_via_chip)

**Tabelas:**
- `conversations`
- `supervisor_channel`
- `interacoes`
- `clientes`
- `doctor_context`
- `chips`
- `conversation_chips`

**Specs:**
- [Server-Sent Events (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [EventSource API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)

**Sprints Relacionadas:**
- Sprint 54 - Phase 4: Supervisor Channel + SSE
- Sprint 1 - Core do Agente (webhook, LLM)
- Sprint 25 - Julia Warmer (chips)
