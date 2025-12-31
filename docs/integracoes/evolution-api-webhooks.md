# Evolution API - Webhooks

> **Docs oficiais:** https://doc.evolution-api.com/v2/en/configuration/webhooks

## Configurar Webhook

```bash
curl -X POST http://localhost:8080/webhook/set/minha-instancia \
  -H "apikey: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://seu-dominio.com/webhooks/evolution",
    "enabled": true,
    "webhook_by_events": false,
    "webhook_base64": false,
    "events": [
      "MESSAGES_UPSERT",
      "CONNECTION_UPDATE",
      "QRCODE_UPDATED"
    ]
  }'
```

---

## Eventos Disponiveis

### Conexao e Autenticacao

| Evento | Descricao |
|--------|-----------|
| `APPLICATION_STARTUP` | Aplicacao inicializada |
| `QRCODE_UPDATED` | QR Code gerado/atualizado (base64) |
| `CONNECTION_UPDATE` | Status da conexao mudou |
| `NEW_TOKEN` | Token JWT renovado |

### Mensagens

| Evento | Descricao |
|--------|-----------|
| `MESSAGES_SET` | Carga inicial de mensagens (1x) |
| `MESSAGES_UPSERT` | Nova mensagem (enviada ou recebida) |
| `MESSAGES_UPDATE` | Mensagem atualizada (status, edicao) |
| `MESSAGES_DELETE` | Mensagem deletada |
| `SEND_MESSAGE` | Mensagem enviada pela API |

### Contatos e Presenca

| Evento | Descricao |
|--------|-----------|
| `CONTACTS_SET` | Carga inicial de contatos |
| `CONTACTS_UPSERT` | Novo contato |
| `CONTACTS_UPDATE` | Contato atualizado |
| `PRESENCE_UPDATE` | Online/offline/digitando/gravando |

### Chats

| Evento | Descricao |
|--------|-----------|
| `CHATS_SET` | Carga inicial de chats |
| `CHATS_UPSERT` | Novo chat |
| `CHATS_UPDATE` | Chat atualizado |
| `CHATS_DELETE` | Chat deletado |

### Grupos

| Evento | Descricao |
|--------|-----------|
| `GROUPS_UPSERT` | Novo grupo |
| `GROUPS_UPDATE` | Grupo atualizado |
| `GROUP_PARTICIPANTS_UPDATE` | Participante add/remove/promote/demote |

---

## Payload: MESSAGES_UPSERT

```json
{
  "event": "messages.upsert",
  "instance": "minha-instancia",
  "data": {
    "key": {
      "remoteJid": "5511999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "ABC123..."
    },
    "pushName": "Nome do Contato",
    "message": {
      "conversation": "Texto da mensagem"
    },
    "messageType": "conversation",
    "messageTimestamp": 1704067200
  }
}
```

### Campos Importantes

| Campo | Descricao |
|-------|-----------|
| `data.key.remoteJid` | Telefone + sufixo (@s.whatsapp.net ou @g.us) |
| `data.key.fromMe` | `true` = enviada, `false` = recebida |
| `data.key.id` | ID unico da mensagem |
| `data.pushName` | Nome do contato no WhatsApp |
| `data.message` | Conteudo (varia por tipo) |
| `data.messageType` | Tipo: `conversation`, `imageMessage`, `audioMessage`, etc |
| `data.messageTimestamp` | Unix timestamp |

### Tipos de Mensagem

| messageType | Campo do conteudo |
|-------------|-------------------|
| `conversation` | `message.conversation` |
| `extendedTextMessage` | `message.extendedTextMessage.text` |
| `imageMessage` | `message.imageMessage` |
| `audioMessage` | `message.audioMessage` |
| `videoMessage` | `message.videoMessage` |
| `documentMessage` | `message.documentMessage` |
| `stickerMessage` | `message.stickerMessage` |
| `locationMessage` | `message.locationMessage` |
| `contactMessage` | `message.contactMessage` |

---

## Payload: CONNECTION_UPDATE

```json
{
  "event": "connection.update",
  "instance": "minha-instancia",
  "data": {
    "state": "open",
    "statusReason": 200
  }
}
```

**States:**
- `open` - Conectado
- `close` - Desconectado
- `connecting` - Conectando

---

## Payload: QRCODE_UPDATED

```json
{
  "event": "qrcode.updated",
  "instance": "minha-instancia",
  "data": {
    "qrcode": {
      "pairingCode": null,
      "code": "2@abc123...",
      "base64": "data:image/png;base64,..."
    }
  }
}
```

---

## Webhook By Events

Quando `webhook_by_events: true`, a URL recebe o nome do evento:

| Evento | URL Final |
|--------|-----------|
| `MESSAGES_UPSERT` | `https://seu-dominio.com/webhook/messages-upsert` |
| `CONNECTION_UPDATE` | `https://seu-dominio.com/webhook/connection-update` |
| `QRCODE_UPDATED` | `https://seu-dominio.com/webhook/qrcode-updated` |

---

## Distinguir Mensagem Enviada vs Recebida

```python
payload = await request.json()
data = payload.get("data", {})
key = data.get("key", {})

if key.get("fromMe"):
    # Mensagem ENVIADA pelo chip
    pass
else:
    # Mensagem RECEBIDA de outro usuario
    pass
```

---

## Ignorar Grupos e Broadcasts

```python
remote_jid = key.get("remoteJid", "")

# Ignorar grupos
if "@g.us" in remote_jid:
    return {"status": "ignored", "reason": "group"}

# Ignorar broadcasts
if "@broadcast" in remote_jid:
    return {"status": "ignored", "reason": "broadcast"}

# Extrair telefone
telefone = remote_jid.split("@")[0]  # "5511999999999"
```

---

## Variaveis de Ambiente (Global)

```bash
WEBHOOK_GLOBAL_URL=https://seu-dominio.com/webhooks/evolution
WEBHOOK_GLOBAL_ENABLED=true
WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=false
WEBHOOK_EVENTS_MESSAGES_UPSERT=true
WEBHOOK_EVENTS_CONNECTION_UPDATE=true
WEBHOOK_EVENTS_QRCODE_UPDATED=true
```
