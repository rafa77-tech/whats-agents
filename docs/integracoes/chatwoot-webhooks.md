# Chatwoot - Webhooks

> **Docs oficiais:** https://developers.chatwoot.com/

## Configuracao

1. Chatwoot Dashboard → Settings → Integrations → Webhooks
2. Adicionar URL do webhook
3. Selecionar eventos

---

## Eventos Disponiveis

| Evento | Descricao |
|--------|-----------|
| `conversation_created` | Nova conversa criada |
| `conversation_status_changed` | Status mudou (open/resolved/pending) |
| `conversation_updated` | Conversa atualizada |
| `message_created` | Nova mensagem (enviada ou recebida) |
| `message_updated` | Mensagem atualizada |
| `webwidget_triggered` | Widget web acionado |

---

## Payload: message_created

```json
{
  "event": "message_created",
  "id": 12345,
  "content": "Texto da mensagem",
  "created_at": "2024-01-01T12:00:00.000Z",
  "message_type": "incoming",
  "content_type": "text",
  "private": false,
  "source_id": null,
  "sender": {
    "id": 100,
    "name": "Dr. Carlos",
    "email": "carlos@email.com",
    "phone_number": "+5511999999999",
    "type": "contact"
  },
  "conversation": {
    "id": 50,
    "inbox_id": 1,
    "status": "open",
    "assignee_id": null,
    "labels": []
  },
  "inbox": {
    "id": 1,
    "name": "WhatsApp Julia"
  },
  "account": {
    "id": 1,
    "name": "Revoluna"
  }
}
```

### Campos Importantes

| Campo | Descricao |
|-------|-----------|
| `message_type` | `incoming` (do cliente) ou `outgoing` (do agente) |
| `private` | `true` = nota interna |
| `sender.type` | `contact` ou `user` (agente) |
| `conversation.id` | ID da conversa |
| `conversation.status` | `open`, `resolved`, `pending`, `snoozed` |
| `conversation.labels` | Labels aplicadas |

---

## Payload: conversation_status_changed

```json
{
  "event": "conversation_status_changed",
  "id": 50,
  "status": "resolved",
  "previous_status": "open",
  "assignee_id": 5,
  "inbox_id": 1,
  "labels": ["concluido"],
  "meta": {
    "sender": {
      "id": 100,
      "name": "Dr. Carlos",
      "phone_number": "+5511999999999"
    }
  }
}
```

---

## Payload: conversation_created

```json
{
  "event": "conversation_created",
  "id": 50,
  "inbox_id": 1,
  "status": "open",
  "messages": [],
  "meta": {
    "sender": {
      "id": 100,
      "name": "Dr. Carlos",
      "phone_number": "+5511999999999"
    }
  },
  "account": {
    "id": 1,
    "name": "Revoluna"
  }
}
```

---

## Distinguir Remetente

```python
payload = await request.json()

message_type = payload.get("message_type")
sender_type = payload.get("sender", {}).get("type")

if message_type == "incoming" and sender_type == "contact":
    # Mensagem do CLIENTE (medico)
    pass
elif message_type == "outgoing" and sender_type == "user":
    # Mensagem do AGENTE (Julia ou humano)
    pass
```

---

## Verificar se e Nota Interna

```python
if payload.get("private"):
    # Nota interna - nao visivel ao cliente
    # Geralmente usada para comunicacao entre agentes
    return {"status": "ignored", "reason": "private_note"}
```

---

## Detectar Handoff (Label)

```python
labels = payload.get("conversation", {}).get("labels", [])

if "humano" in labels:
    # Conversa marcada para atendimento humano
    # Julia deve parar de responder
    pass
```

---

## Verificar Inbox

```python
inbox_id = payload.get("inbox", {}).get("id")
inbox_name = payload.get("inbox", {}).get("name")

# Filtrar apenas inbox da Julia
if inbox_id != settings.CHATWOOT_INBOX_ID:
    return {"status": "ignored", "reason": "wrong_inbox"}
```

---

## Response Esperada

Retornar HTTP 200 para confirmar recebimento:

```python
return {"status": "ok"}
```

---

## Seguranca

Chatwoot nao envia assinatura no webhook por padrao. Recomendacoes:

1. Usar URL secreta/aleatoria
2. Verificar IP de origem se possivel
3. Validar estrutura do payload

---

## Env Vars

```bash
CHATWOOT_WEBHOOK_URL=https://seu-dominio.com/webhooks/chatwoot
CHATWOOT_INBOX_ID=1
```
