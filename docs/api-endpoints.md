# API e Endpoints

> Referencia completa de todos os endpoints da API

---

## Base URL

```
Desenvolvimento: http://localhost:8000
Producao: https://api.julia.revoluna.com (futuro)
```

---

## Health & Monitoramento

### GET /health

Health check basico (liveness probe).

**Resposta:**
```json
{
    "status": "ok",
    "timestamp": "2025-12-07T10:30:00Z",
    "version": "1.0.0"
}
```

### GET /health/ready

Readiness probe - verifica dependencias.

**Resposta:**
```json
{
    "status": "ok",
    "checks": {
        "supabase": "ok",
        "redis": "ok",
        "evolution": "ok"
    }
}
```

### GET /health/rate

Status do rate limiting.

**Resposta:**
```json
{
    "status": "ok",
    "limits": {
        "por_hora": 20,
        "por_dia": 100
    },
    "usage": {
        "hora_atual": 5,
        "dia_atual": 23
    }
}
```

### GET /health/circuit

Status dos circuit breakers.

**Resposta:**
```json
{
    "circuits": {
        "claude": {"state": "closed", "failures": 0},
        "evolution": {"state": "closed", "failures": 0},
        "supabase": {"state": "closed", "failures": 0}
    }
}
```

---

## Webhook

### POST /webhook/evolution

Recebe webhooks da Evolution API (mensagens WhatsApp).

**Headers:**
```
Content-Type: application/json
```

**Payload (exemplo):**
```json
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
            "conversation": "Oi, tudo bem?"
        },
        "messageTimestamp": "1701950400"
    }
}
```

**Resposta:**
```json
{"status": "ok"}
```

**Processamento:**
1. Retorna 200 imediatamente
2. Processa em background
3. Envia resposta via Evolution API

---

## Jobs (Tarefas Agendadas)

Endpoints chamados pelo scheduler ou manualmente.

### POST /jobs/processar-mensagens-agendadas

Processa fila de mensagens agendadas.

**Schedule:** `* * * * *` (cada minuto)

**Resposta:**
```json
{
    "status": "ok",
    "message": "Mensagens agendadas processadas",
    "processadas": 5
}
```

### POST /jobs/processar-campanhas-agendadas

Inicia campanhas que atingiram horario agendado.

**Schedule:** `* * * * *` (cada minuto)

**Resposta:**
```json
{
    "status": "ok",
    "message": "2 campanha(s) iniciada(s)"
}
```

### POST /jobs/verificar-alertas

Verifica condicoes de alerta e notifica.

**Schedule:** `*/15 * * * *` (cada 15 minutos)

**Resposta:**
```json
{
    "status": "ok",
    "message": "Alertas verificados",
    "alertas_enviados": 1
}
```

### POST /jobs/processar-followups

Processa follow-ups pendentes (48h, 5d, 15d).

**Schedule:** `0 10 * * *` (diario as 10h)

**Resposta:**
```json
{
    "status": "ok",
    "stats": {
        "48h": 5,
        "5d": 2,
        "15d": 1
    }
}
```

### POST /jobs/processar-pausas-expiradas

Reativa conversas pausadas ha mais de 60 dias.

**Schedule:** `0 6 * * *` (diario as 6h)

**Resposta:**
```json
{
    "status": "ok",
    "stats": {"reativadas": 3}
}
```

### POST /jobs/avaliar-conversas-pendentes

Avalia qualidade de conversas encerradas.

**Schedule:** `0 2 * * *` (diario as 2h)

**Resposta:**
```json
{
    "status": "ok",
    "message": "Conversas pendentes avaliadas",
    "avaliadas": 15
}
```

### POST /jobs/relatorio-diario

Gera e envia relatorio diario para Slack.

**Schedule:** `0 8 * * *` (diario as 8h)

**Resposta:**
```json
{
    "status": "ok",
    "message": "Relatorio diario enviado",
    "relatorio": {...}
}
```

### POST /jobs/report-periodo

Gera report de periodo especifico.

**Query params:**
- `tipo`: `manha` | `almoco` | `tarde` | `fim_dia`

**Schedule:**
- manha: `0 10 * * *`
- almoco: `0 13 * * *`
- tarde: `0 17 * * *`
- fim_dia: `0 20 * * *`

**Resposta:**
```json
{
    "status": "ok",
    "periodo": "manha",
    "metricas": {
        "mensagens_enviadas": 45,
        "respostas_recebidas": 12,
        "taxa_resposta": 26.7
    }
}
```

### POST /jobs/report-semanal

Gera report semanal consolidado.

**Schedule:** `0 9 * * 1` (segunda as 9h)

**Resposta:**
```json
{
    "status": "ok",
    "semana": "2025-W49",
    "metricas": {...}
}
```

### POST /jobs/atualizar-prompt-feedback

Atualiza prompt baseado em feedback do gestor.

**Schedule:** `0 2 * * 0` (domingo as 2h)

**Resposta:**
```json
{
    "status": "ok",
    "message": "Prompt atualizado com feedback"
}
```

### POST /jobs/sincronizar-briefing

Sincroniza briefing do Google Docs.

**Schedule:** `0 * * * *` (cada hora)

**Resposta:**
```json
{
    "status": "ok",
    "result": {
        "success": true,
        "changed": true,
        "hash": "abc123"
    }
}
```

---

## Metricas

### GET /metricas/resumo

Retorna resumo de metricas dos ultimos 7 dias.

**Resposta:**
```json
{
    "periodo": {
        "inicio": "2025-12-01",
        "fim": "2025-12-07"
    },
    "conversas": {
        "total": 150,
        "ativas": 23,
        "encerradas": 127
    },
    "mensagens": {
        "enviadas": 450,
        "recebidas": 380
    },
    "taxa_resposta": 32.5,
    "tempo_medio_resposta_segundos": 45,
    "handoffs": 5,
    "opt_outs": 2,
    "deteccao_bot": 0.8
}
```

---

## Admin

### GET /admin/conversas

Lista conversas para revisao.

**Query params:**
- `status`: `active` | `completed` | `escalated`
- `controlled_by`: `ai` | `human`
- `limit`: numero (default: 50)
- `offset`: numero (default: 0)

**Resposta:**
```json
{
    "conversas": [
        {
            "id": "uuid",
            "cliente": {
                "nome": "Dr. Carlos Silva",
                "telefone": "5511999999999"
            },
            "status": "active",
            "controlled_by": "ai",
            "message_count": 8,
            "last_message_at": "2025-12-07T10:30:00Z"
        }
    ],
    "total": 150,
    "limit": 50,
    "offset": 0
}
```

---

## Campanhas

### POST /campanhas

Cria nova campanha de outreach.

**Body:**
```json
{
    "nome": "Anestesistas ABC",
    "tipo": "oferta_plantao",
    "segmento": {
        "especialidade": ["anestesiologia"],
        "estado": ["SP"],
        "status": ["novo", "respondeu"]
    },
    "mensagem_template": "Oi {nome}! Temos vagas em {cidade}..."
}
```

**Resposta:**
```json
{
    "id": 1,
    "nome": "Anestesistas ABC",
    "status": "rascunho",
    "total_alvos": 150
}
```

---

## Piloto

### GET /piloto/status

Status do programa piloto.

**Resposta:**
```json
{
    "ativo": true,
    "medicos_piloto": 50,
    "metricas": {
        "mensagens_enviadas": 120,
        "taxa_resposta": 35.0,
        "conversoes": 5
    }
}
```

---

## Chatwoot

### POST /chatwoot/webhook

Recebe webhooks do Chatwoot (handoff humano).

**Payload:**
```json
{
    "event": "message_created",
    "conversation": {
        "id": 123,
        "status": "open"
    },
    "message": {
        "content": "Resposta do gestor",
        "sender_type": "user"
    }
}
```

---

## Testes

### GET /test/db/connection

Testa conexao com Supabase.

**Resposta:**
```json
{
    "status": "ok",
    "latency_ms": 45
}
```

### GET /test/db/vagas/count

Conta vagas no banco.

**Resposta:**
```json
{
    "count": 4973
}
```

### GET /test/whatsapp/status

Status da instancia WhatsApp.

**Resposta:**
```json
{
    "instance": "julia",
    "status": "connected",
    "phone": "5511999999999"
}
```

### POST /test/llm/resposta

Testa geracao de resposta do LLM.

**Body:**
```json
{
    "mensagem": "Oi, tem vaga de anestesia?"
}
```

**Resposta:**
```json
{
    "resposta": "Oi! Sim, temos vagas...",
    "tokens_usados": 150,
    "latency_ms": 800
}
```

---

## Codigos de Erro

| Codigo | Descricao |
|--------|-----------|
| 200 | Sucesso |
| 400 | Request invalido |
| 401 | Nao autorizado |
| 404 | Recurso nao encontrado |
| 429 | Rate limit excedido |
| 500 | Erro interno |
| 503 | Servico indisponivel (circuit open) |

---

## Rate Limits da API

| Endpoint | Limite |
|----------|--------|
| /webhook/* | Sem limite (Evolution controla) |
| /jobs/* | 1 req/min por job |
| /admin/* | 100 req/min |
| /metricas/* | 10 req/min |
| /test/* | 10 req/min |
