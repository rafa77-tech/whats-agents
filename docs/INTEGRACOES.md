# Integracoes Externas

> Detalhes de cada integracao com servicos externos

---

## Visao Geral

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AGENTE JULIA                                      │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────────┐
        │                         │                             │
        ▼                         ▼                             ▼
┌───────────────┐       ┌─────────────────┐           ┌─────────────────┐
│  Evolution    │       │    Anthropic    │           │    Supabase     │
│   API         │       │    (Claude)     │           │   (Postgres)    │
│  WhatsApp     │       │      LLM        │           │    + pgvector   │
└───────────────┘       └─────────────────┘           └─────────────────┘
        │                         │                             │
        │                         │                             │
        ▼                         ▼                             ▼
┌───────────────┐       ┌─────────────────┐           ┌─────────────────┐
│   Chatwoot    │       │     Redis       │           │  Google Docs    │
│  Supervisao   │       │  Cache/Filas    │           │   Briefing      │
└───────────────┘       └─────────────────┘           └─────────────────┘
        │
        ▼
┌───────────────┐
│    Slack      │
│ Notificacoes  │
└───────────────┘
```

---

## 1. Evolution API (WhatsApp)

### O que e

Evolution API e uma solucao open-source para conectar ao WhatsApp Web. Permite enviar e receber mensagens programaticamente.

### Configuracao

```bash
# .env
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=sua_api_key
EVOLUTION_INSTANCE=julia
```

### Docker Compose

```yaml
evolution-api:
  image: atendai/evolution-api:latest
  ports:
    - "8080:8080"
  volumes:
    - evolution_data:/evolution/instances
  environment:
    - AUTHENTICATION_API_KEY=sua_api_key
```

### Endpoints Utilizados

| Endpoint | Metodo | Uso |
|----------|--------|-----|
| `/instance/create` | POST | Criar instancia |
| `/instance/qrcode/{instance}` | GET | Obter QR code |
| `/webhook/set/{instance}` | POST | Configurar webhook |
| `/message/sendText/{instance}` | POST | Enviar mensagem |
| `/instance/connectionState/{instance}` | GET | Verificar conexao |

### Servico: EvolutionService

```python
# app/services/evolution.py

class EvolutionService:
    async def send_message(self, phone: str, text: str) -> dict:
        """Envia mensagem de texto"""

    async def check_connection(self) -> dict:
        """Verifica status da conexao"""

    async def get_qrcode(self) -> str:
        """Obtem QR code para conectar"""
```

### Webhook de Entrada

```python
# POST /webhook/evolution

# Payload recebido:
{
    "event": "messages.upsert",
    "instance": "julia",
    "data": {
        "key": {
            "remoteJid": "5511999999999@s.whatsapp.net",
            "fromMe": false,
            "id": "ABC123"
        },
        "message": {
            "conversation": "Oi, vi a vaga de anestesia"
        },
        "messageTimestamp": 1733580000
    }
}
```

### Rate Limiting

| Limite | Valor | Configuracao |
|--------|-------|--------------|
| Por hora | 20 msgs | MAX_MSGS_POR_HORA |
| Por dia | 100 msgs | MAX_MSGS_POR_DIA |
| Intervalo | 45-180s | Delay aleatorio |

### Tratamento de Erros

```python
# Erros comuns:
# - 401: API key invalida
# - 404: Instancia nao encontrada
# - 500: WhatsApp desconectado

# Circuit breaker ativo para proteger
```

---

## 2. Anthropic (Claude LLM)

### O que e

API da Anthropic para acessar modelos Claude. Usamos Haiku (80%) e Sonnet (20%) em estrategia hibrida.

### Configuracao

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1024
```

### Modelos Utilizados

| Modelo | Uso | Custo |
|--------|-----|-------|
| claude-3-5-haiku | Respostas simples (80%) | $0.25/1M input |
| claude-sonnet-4 | Negociacao complexa (20%) | $3/1M input |

### Servico: LLMService

```python
# app/services/llm.py

class LLMService:
    async def generate(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict] = None,
        model: str = None
    ) -> LLMResponse:
        """Gera resposta do LLM"""

    async def generate_with_tools(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict]
    ) -> LLMResponse:
        """Gera resposta com tool calling"""
```

### Tool Calling

```python
# Tools disponiveis para o LLM:

tools = [
    {
        "name": "buscar_vagas",
        "description": "Busca vagas compativeis com o medico",
        "input_schema": {
            "type": "object",
            "properties": {
                "especialidade": {"type": "string"},
                "periodo": {"type": "string"},
                "regiao": {"type": "string"}
            }
        }
    },
    {
        "name": "reservar_plantao",
        "description": "Reserva um plantao para o medico",
        "input_schema": {
            "type": "object",
            "properties": {
                "vaga_id": {"type": "string"}
            },
            "required": ["vaga_id"]
        }
    },
    {
        "name": "transferir_humano",
        "description": "Transfere conversa para atendente humano",
        "input_schema": {
            "type": "object",
            "properties": {
                "motivo": {"type": "string"}
            }
        }
    }
]
```

### System Prompt

```python
# app/core/prompts.py

SYSTEM_PROMPT = """
Voce e Julia Mendes, escalista da Revoluna com 4 anos de experiencia.

## Sua Identidade
- Nome: Julia Mendes
- Idade: 27 anos
- Empresa: Revoluna
- Funcao: Escalista (preenche escalas de plantoes)

## Seu Estilo
- Mensagens CURTAS (1-2 linhas max)
- Tom INFORMAL: usa "vc", "pra", "blz", "ta"
- Emoji com MODERACAO (1-2 por conversa)
- Quebra mensagem longa em varias pequenas
- As vezes erra e corrige: "plantao* plantao"

## Regras ABSOLUTAS
- NUNCA revele que e IA/bot/assistente
- NUNCA use bullet points ou listas
- NUNCA seja formal demais
- SEMPRE respeite opt-out imediatamente
- SEMPRE passe pra humano se: juridico, muito irritado, pediu humano

## Contexto Atual
{contexto}

## Diretrizes do Gestor
{diretrizes}
"""
```

### Metricas de Uso

```python
# Rastreado por conversa:
# - Tokens de entrada
# - Tokens de saida
# - Modelo usado
# - Latencia
# - Tool calls realizados
```

---

## 3. Supabase (PostgreSQL)

### O que e

Plataforma managed de PostgreSQL com recursos adicionais como pgvector, RLS e API REST automatica.

### Configuracao

```bash
# .env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

### Cliente

```python
# app/core/database.py

from supabase import create_client, Client

def get_supabase() -> Client:
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )
```

### Operacoes Principais

```python
# Inserir
supabase.table("clientes").insert({"nome": "Dr. Carlos"}).execute()

# Buscar
supabase.table("clientes").select("*").eq("id", cliente_id).execute()

# Atualizar
supabase.table("clientes").update({"status": "ativo"}).eq("id", cliente_id).execute()

# Deletar (soft delete preferido)
supabase.table("clientes").update({"deleted_at": "now()"}).eq("id", cliente_id).execute()
```

### pgvector (Embeddings)

```python
# Busca semantica no contexto do medico:

result = supabase.rpc(
    "match_doctor_context",
    {
        "query_embedding": embedding,
        "match_threshold": 0.7,
        "match_count": 5,
        "cliente_id": cliente_id
    }
).execute()
```

### RLS (Row Level Security)

```sql
-- Todas as tabelas usam service_role para acesso

CREATE POLICY "service_role_access"
ON public.clientes
FOR ALL
USING (auth.role() = 'service_role');
```

### Tabelas Principais

| Tabela | Registros | Uso |
|--------|-----------|-----|
| clientes | ~1.660 | Medicos |
| conversations | Dinamico | Conversas |
| interacoes | Dinamico | Mensagens |
| vagas | Dinamico | Plantoes |
| hospitais | 85 | Hospitais |
| especialidades | 56 | Especialidades |

---

## 4. Redis

### O que e

Cache em memoria usado para rate limiting, filas de mensagens e cache de dados frequentes.

### Configuracao

```bash
# .env
REDIS_URL=redis://localhost:6379/0
```

### Docker Compose

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
```

### Servico: RedisService

```python
# app/services/redis.py

class RedisService:
    async def get(self, key: str) -> str | None:
        """Busca valor"""

    async def set(self, key: str, value: str, ex: int = None):
        """Define valor com TTL opcional"""

    async def incr(self, key: str) -> int:
        """Incrementa contador"""

    async def expire(self, key: str, seconds: int):
        """Define expiracao"""
```

### Usos no Sistema

| Uso | Chave | TTL |
|-----|-------|-----|
| Rate limit hora | `rate:{phone}:hour` | 1 hora |
| Rate limit dia | `rate:{phone}:day` | 24 horas |
| Cache contexto | `context:{cliente_id}` | 5 min |
| Circuit breaker | `circuit:{service}` | Variavel |

### Rate Limiter

```python
# app/services/rate_limiter.py

class RateLimiter:
    async def check_limit(self, phone: str) -> tuple[bool, dict]:
        """
        Retorna:
        - (True, info) se pode enviar
        - (False, info) se limite atingido
        """

    async def register_send(self, phone: str):
        """Registra envio para contagem"""
```

---

## 5. Chatwoot

### O que e

Plataforma open-source de atendimento ao cliente. Usada para supervisao humana e handoff.

### Configuracao

```bash
# .env
CHATWOOT_URL=http://localhost:3000
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1
```

### Docker Compose

```yaml
chatwoot:
  image: chatwoot/chatwoot:latest
  ports:
    - "3000:3000"
  environment:
    - SECRET_KEY_BASE=xxx
    - POSTGRES_HOST=postgres
  depends_on:
    - postgres
```

### Servico: ChatwootService

```python
# app/services/chatwoot.py

class ChatwootService:
    async def create_conversation(
        self,
        contact_id: str,
        inbox_id: str
    ) -> dict:
        """Cria conversa no Chatwoot"""

    async def send_message(
        self,
        conversation_id: str,
        content: str,
        private: bool = False
    ) -> dict:
        """Envia mensagem (publica ou nota interna)"""

    async def sync_message(
        self,
        conversation_id: str,
        message: dict
    ):
        """Sincroniza mensagem do WhatsApp"""
```

### Fluxo de Handoff

```
1. Trigger detectado (Julia)
   ↓
2. UPDATE conversations SET controlled_by='human'
   ↓
3. Notifica no Chatwoot (nota interna)
   ↓
4. Julia para de responder
   ↓
5. Humano assume via Chatwoot
   ↓
6. Mensagens sincronizadas bidirecionalmente
```

### Labels Especiais

| Label | Acao |
|-------|------|
| `humano` | Forca handoff |
| `vip` | Tratamento especial |
| `urgente` | Prioridade alta |
| `resolvido` | Encerra conversa |

---

## 6. Slack

### O que e

Plataforma de comunicacao. Usada para notificar gestor sobre eventos importantes.

### Configuracao

```bash
# .env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
SLACK_CHANNEL=#julia-gestao
```

### Servico: SlackService

```python
# app/services/slack.py

class SlackService:
    async def send_notification(
        self,
        message: str,
        channel: str = None,
        blocks: list = None
    ):
        """Envia notificacao para Slack"""

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "warning"
    ):
        """Envia alerta formatado"""
```

### Tipos de Notificacao

| Evento | Canal | Urgencia |
|--------|-------|----------|
| Handoff solicitado | #julia-gestao | Alta |
| Opt-out recebido | #julia-gestao | Media |
| Circuit breaker aberto | #julia-alertas | Critica |
| Rate limit atingido | #julia-alertas | Alta |
| Vaga reservada | #julia-vendas | Normal |
| Report diario | #julia-gestao | Normal |

### Formato de Mensagem

```python
# Handoff
blocks = [
    {
        "type": "header",
        "text": {"type": "plain_text", "text": "🚨 Handoff Solicitado"}
    },
    {
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*Medico:* Dr. Carlos"},
            {"type": "mrkdwn", "text": f"*Motivo:* Pediu humano"},
            {"type": "mrkdwn", "text": f"*Conversa:* <url|Ver no Chatwoot>"}
        ]
    }
]
```

---

## 7. Google Docs (Briefing)

### O que e

Documento Google Docs onde o gestor escreve diretrizes para Julia. Sincronizado a cada hora.

### Configuracao

```bash
# .env
GOOGLE_DOCS_CREDENTIALS_PATH=./credentials/google_docs.json
GOOGLE_BRIEFING_DOC_ID=1abc...xyz
```

### Credenciais

```json
// credentials/google_docs.json
{
  "type": "service_account",
  "project_id": "julia-briefing",
  "private_key_id": "xxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "julia@julia-briefing.iam.gserviceaccount.com"
}
```

### Servico: BriefingService

```python
# app/services/briefing.py

class BriefingService:
    async def sync_from_google_docs(self) -> BriefingSyncResult:
        """
        Sincroniza briefing do Google Docs:
        1. Busca documento
        2. Compara hash com ultimo sync
        3. Se mudou, parseia secoes
        4. Atualiza tabela diretrizes
        """

    async def get_current_diretrizes(self) -> list[Diretriz]:
        """Retorna diretrizes ativas"""
```

### Estrutura do Documento

```markdown
# Briefing Julia - Semana 01/12

## Foco da Semana
- Priorizar anestesiologistas do ABC
- Meta: 10 vagas fechadas

## Vagas Prioritarias
- Hospital Brasil: precisa de 3 anestesistas para sabado
- Sao Luiz: urgente para domingo

## Medicos VIP
- Dr. Carlos Silva (CRM 123456) - sempre priorizar
- Dra. Ana Costa (CRM 654321) - ofertas especiais

## Medicos Bloqueados
- Dr. Joao Santos - reclamou muito, nao contatar

## Tom a Usar
- Mais direto essa semana, menos floreiro
- Mencionar urgencia das vagas

## Margem de Negociacao
- Ate 15% acima do valor base
- Para VIPs, ate 20%
```

### Secoes Parseadas

| Secao | Tipo Diretriz | Prioridade |
|-------|---------------|------------|
| Foco da Semana | foco | 10 |
| Vagas Prioritarias | vaga_prioritaria | 9 |
| Medicos VIP | vip | 8 |
| Medicos Bloqueados | bloqueado | 10 |
| Tom a Usar | tom | 7 |
| Margem de Negociacao | negociacao | 6 |

### Sincronizacao

```python
# Job agendado: a cada hora

async def job_sync_briefing():
    service = BriefingService()
    result = await service.sync_from_google_docs()

    if result.changed:
        logger.info(f"Briefing atualizado: {result.sections_updated} secoes")
        # Notifica gestor no Slack
```

---

## 8. Resumo de Dependencias

### Servicos Externos

| Servico | Criticidade | Fallback |
|---------|-------------|----------|
| Evolution API | Alta | Queue + retry |
| Anthropic | Alta | Circuit breaker |
| Supabase | Alta | Nenhum (core) |
| Redis | Media | Fallback in-memory |
| Chatwoot | Baixa | Continua sem sync |
| Slack | Baixa | Log local |
| Google Docs | Baixa | Usa diretrizes em cache |

### Circuit Breakers

```python
# Configuracao por servico:

CIRCUIT_CONFIG = {
    "evolution": {
        "failure_threshold": 3,
        "recovery_timeout": 60,
        "half_open_requests": 1
    },
    "anthropic": {
        "failure_threshold": 5,
        "recovery_timeout": 30,
        "half_open_requests": 2
    },
    "chatwoot": {
        "failure_threshold": 5,
        "recovery_timeout": 120,
        "half_open_requests": 1
    }
}
```

### Health Checks

```python
# GET /health/integrations

{
    "evolution": {
        "status": "healthy",
        "connected": true,
        "latency_ms": 45
    },
    "supabase": {
        "status": "healthy",
        "tables": 32,
        "latency_ms": 23
    },
    "redis": {
        "status": "healthy",
        "memory_mb": 12,
        "latency_ms": 1
    },
    "anthropic": {
        "status": "healthy",
        "circuit": "closed",
        "latency_ms": 850
    }
}
```

---

## 9. Troubleshooting

### Evolution API

| Problema | Causa Provavel | Solucao |
|----------|----------------|---------|
| 401 Unauthorized | API key errada | Verificar EVOLUTION_API_KEY |
| WhatsApp desconectado | Sessao expirou | Escanear QR code novamente |
| Mensagem nao enviada | Rate limit | Aguardar ou verificar contadores |

### Anthropic

| Problema | Causa Provavel | Solucao |
|----------|----------------|---------|
| 401 | API key invalida | Verificar ANTHROPIC_API_KEY |
| 429 | Rate limit API | Aguardar ou upgrade plano |
| Timeout | Modelo lento | Verificar latencia, usar Haiku |

### Supabase

| Problema | Causa Provavel | Solucao |
|----------|----------------|---------|
| 401 | Service key errada | Usar service_role key, nao anon |
| RLS blocking | Politica incorreta | Verificar RLS policies |
| Connection refused | Projeto pausado | Verificar status no dashboard |

### Redis

| Problema | Causa Provavel | Solucao |
|----------|----------------|---------|
| Connection refused | Redis nao rodando | `docker compose up redis` |
| Memory full | Muitos dados | Verificar politica de eviction |

### Google Docs

| Problema | Causa Provavel | Solucao |
|----------|----------------|---------|
| 403 Forbidden | Sem permissao | Compartilhar doc com service account |
| 404 Not Found | Doc ID errado | Verificar GOOGLE_BRIEFING_DOC_ID |
| Credenciais invalidas | JSON incorreto | Regenerar credenciais |
