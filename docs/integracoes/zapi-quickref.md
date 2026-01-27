# Z-API Quick Reference

Documentação de referência rápida para integração com Z-API.

**Documentação oficial:** https://developer.z-api.io/

## Autenticação

Toda requisição para a Z-API requer:

| Header | Descrição |
|--------|-----------|
| `Client-Token` | Token de segurança da conta |
| `Content-Type` | `application/json` |

**URL Base:**
```
https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}
```

---

## Webhooks

### Visão Geral

A Z-API usa webhooks para notificar eventos em tempo real. **HTTPS é obrigatório** - webhooks HTTP não são aceitos.

### Webhooks Disponíveis

| Webhook | Endpoint de Configuração | Descrição |
|---------|-------------------------|-----------|
| Mensagem Recebida | `update-webhook-received` | Mensagens de entrada |
| Mensagem Enviada | `update-webhook-delivery` | Confirmação de envio |
| Status de Mensagem | `update-webhook-message-status` | Entregue, lido, etc |
| Presença no Chat | `update-webhook-chat-presence` | Digitando, online, etc |
| Desconexão | `update-webhook-disconnected` | Perda de conexão |
| Status da Conexão | `update-webhook-status` | Mudanças de conexão |

### Configuração de Webhook

**Método:** `PUT`

**URL:** `https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}/{endpoint}`

**Body:**
```json
{
  "value": "https://seu-servidor.com/webhook"
}
```

**Exemplo:**
```bash
curl -X PUT \
  "https://api.z-api.io/instances/INSTANCE_ID/token/TOKEN/update-webhook-received" \
  -H "Client-Token: SEU_CLIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "https://seu-servidor.com/webhooks/zapi"}'
```

---

## Payloads de Webhook

### 1. Mensagem Recebida (ReceivedCallback)

```json
{
  "type": "ReceivedCallback",
  "instanceId": "instance.id",
  "messageId": "A20DA9C0183A2D35A260F53F5D2B9244",
  "phone": "5511999999999",
  "fromMe": false,
  "momment": 1580163342,
  "status": "RECEIVED",
  "chatName": "Nome do Contato",
  "senderName": "Nome do Remetente",
  "senderPhoto": "https://...",
  "isGroup": false,
  "isNewsletter": false,
  "forwarded": false,
  "text": {
    "message": "Olá, tudo bem?"
  }
}
```

**Campos principais:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `type` | string | Sempre `ReceivedCallback` |
| `instanceId` | string | ID da instância |
| `messageId` | string | ID único da mensagem |
| `phone` | string | Telefone do remetente |
| `fromMe` | boolean | Se foi enviada por nós |
| `momment` | integer | Timestamp Unix |
| `status` | string | PENDING, SENT, RECEIVED, READ, PLAYED |
| `isGroup` | boolean | Se é mensagem de grupo |
| `text.message` | string | Conteúdo da mensagem de texto |

**Tipos de mídia:**

- `text.message` - Texto
- `image.imageUrl`, `image.caption` - Imagem
- `audio.audioUrl`, `audio.ptt` - Áudio (ptt=true = mensagem de voz)
- `video.videoUrl`, `video.caption` - Vídeo
- `document.documentUrl`, `document.fileName` - Documento
- `sticker.stickerUrl` - Figurinha
- `location.latitude`, `location.longitude` - Localização
- `contact.displayName`, `contact.vcard` - Contato
- `reaction.value`, `reaction.referencedMessage` - Reação

### 2. Mensagem Enviada (DeliveryCallback)

```json
{
  "type": "DeliveryCallback",
  "instanceId": "instance.id",
  "phone": "5511999999999",
  "zaapId": "A20DA9C0183A2D35A260F53F5D2B9244",
  "messageId": "A20DA9C0183A2D35A260F53F5D2B9244"
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `type` | string | Sempre `DeliveryCallback` |
| `phone` | string | Telefone do destinatário |
| `messageId` | string | ID da mensagem enviada |
| `zaapId` | string | ID da mensagem na conversa |

### 3. Status de Mensagem (MessageStatusCallback)

```json
{
  "type": "MessageStatusCallback",
  "instanceId": "instance.id",
  "messageId": "A20DA9C0183A2D35A260F53F5D2B9244",
  "phone": "5511999999999",
  "status": "READ",
  "momment": 1580163342
}
```

**Status possíveis:**

| Status | Descrição |
|--------|-----------|
| `PENDING` | Aguardando envio |
| `SENT` | Enviada para WhatsApp |
| `RECEIVED` | Entregue ao destinatário |
| `READ` | Lida pelo destinatário |
| `PLAYED` | Áudio/vídeo reproduzido |
| `DELETED` | Mensagem apagada |

### 4. Presença no Chat (PresenceChatCallback)

```json
{
  "type": "PresenceChatCallback",
  "instanceId": "instance.id",
  "phone": "5511999999999",
  "status": "COMPOSING",
  "lastSeen": null
}
```

**Status de presença:**

| Status | Descrição |
|--------|-----------|
| `AVAILABLE` | Usuário está no chat |
| `UNAVAILABLE` | Usuário saiu do chat |
| `COMPOSING` | Usuário está digitando |
| `PAUSED` | Parou de digitar (multi-device beta) |
| `RECORDING` | Gravando áudio (multi-device beta) |

### 5. Desconexão (DisconnectedCallback)

```json
{
  "type": "DisconnectedCallback",
  "instanceId": "instance.id",
  "momment": 1580163342,
  "error": "Device has been disconnected",
  "disconnected": true
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `type` | string | Sempre `DisconnectedCallback` |
| `error` | string | Motivo da desconexão |
| `disconnected` | boolean | Sempre `true` |
| `momment` | integer | Timestamp da desconexão |

---

## Endpoints de Envio

### Enviar Texto

**POST** `/send-text`

```json
{
  "phone": "5511999999999",
  "message": "Olá, tudo bem?"
}
```

### Enviar Imagem

**POST** `/send-image`

```json
{
  "phone": "5511999999999",
  "image": "https://url-da-imagem.com/foto.jpg",
  "caption": "Legenda opcional"
}
```

### Enviar Áudio

**POST** `/send-audio`

```json
{
  "phone": "5511999999999",
  "audio": "https://url-do-audio.com/audio.mp3"
}
```

### Enviar Documento

**POST** `/send-document/pdf`

```json
{
  "phone": "5511999999999",
  "document": "https://url-do-doc.com/arquivo.pdf"
}
```

### Enviar Vídeo

**POST** `/send-video`

```json
{
  "phone": "5511999999999",
  "video": "https://url-do-video.com/video.mp4",
  "caption": "Legenda opcional"
}
```

---

## Endpoints de Status

### Verificar Status da Conexão

**GET** `/status`

**Resposta:**
```json
{
  "connected": true,
  "smartphoneConnected": true
}
```

### Desconectar

**GET** `/disconnect`

### Reiniciar

**GET** `/restart`

### Obter QR Code

**GET** `/qr-code`

---

## Notificações de Grupo

O webhook de recebimento também captura eventos de grupo via campo `notification`:

| Tipo | Descrição |
|------|-----------|
| `GROUP_PARTICIPANT_ADD` | Participante adicionado |
| `GROUP_PARTICIPANT_REMOVE` | Participante removido |
| `GROUP_PARTICIPANT_LEAVE` | Participante saiu |
| `GROUP_PARTICIPANT_PROMOTE` | Promovido a admin |
| `GROUP_PARTICIPANT_DEMOTE` | Rebaixado de admin |
| `MEMBERSHIP_APPROVAL_REQUEST` | Solicitação de entrada |

---

## Diferenças Evolution vs Z-API

| Aspecto | Evolution API | Z-API |
|---------|--------------|-------|
| Hospedagem | Self-hosted | SaaS (cloud) |
| Custo | Gratuito | Pago |
| Campo de evento | `event` | `type` |
| Formato telefone | `@s.whatsapp.net` | Número limpo |
| Webhook único | Não | Não (um por tipo) |
| HTTPS obrigatório | Não | Sim |

---

## Integração no Projeto Julia

### Chip Z-API

Campos específicos na tabela `chips`:

| Campo | Descrição |
|-------|-----------|
| `zapi_instance_id` | ID da instância Z-API |
| `zapi_token` | Token da instância |
| `zapi_client_token` | Token de segurança da conta |
| `provider` | `z-api` |

### Webhook Endpoint

```
POST /webhooks/zapi
```

Recebe todos os eventos Z-API e roteia internamente por tipo.

### Configuração no Painel Z-API

Use esta URL para todos os webhooks:
```
https://whats-agents-production.up.railway.app/webhooks/zapi
```

---

## Troubleshooting

### Webhook não recebe eventos

1. Verificar se URL é HTTPS
2. Verificar se `Client-Token` está correto
3. Verificar se instância está conectada (`GET /status`)

### Mensagens não enviadas

1. Verificar status da conexão
2. Verificar formato do telefone (apenas números, com código do país)
3. Verificar se número existe no WhatsApp

### Desconexão frequente

1. Verificar se celular está com internet estável
2. Verificar se WhatsApp Web não está aberto em outro lugar
3. Considerar usar WhatsApp Business para maior estabilidade
