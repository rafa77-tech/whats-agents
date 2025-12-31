# Evolution API - Quick Reference

> **Docs oficiais:** https://doc.evolution-api.com/v2/
> **GitHub:** https://github.com/EvolutionAPI/evolution-api

## Visao Geral

Evolution API e uma API open-source para integracao com WhatsApp usando a biblioteca Baileys.

**Base URL local:** `http://localhost:8080`

---

## Autenticacao

```
Header: apikey: <sua_api_key>
Content-Type: application/json
```

---

## Endpoints Principais

### Instancias

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Criar instancia | `POST` | `/instance/create` |
| Listar instancias | `GET` | `/instance/fetchInstances` |
| Conectar (QR Code) | `GET` | `/instance/connect/{instance}` |
| Status conexao | `GET` | `/instance/connectionState/{instance}` |
| Reiniciar | `PUT` | `/instance/restart/{instance}` |
| Logout | `DELETE` | `/instance/logout/{instance}` |
| Deletar | `DELETE` | `/instance/delete/{instance}` |

### Mensagens

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Enviar texto | `POST` | `/message/sendText/{instance}` |
| Enviar midia | `POST` | `/message/sendMedia/{instance}` |
| Enviar audio | `POST` | `/message/sendWhatsAppAudio/{instance}` |
| Enviar localizacao | `POST` | `/message/sendLocation/{instance}` |
| Enviar contato | `POST` | `/message/sendContact/{instance}` |
| Enviar reacao | `POST` | `/message/sendReaction/{instance}` |
| Enviar poll | `POST` | `/message/sendPoll/{instance}` |
| Enviar lista | `POST` | `/message/sendList/{instance}` |
| Enviar botoes | `POST` | `/message/sendButtons/{instance}` |

### Webhook

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Configurar webhook | `POST` | `/webhook/set/{instance}` |
| Buscar webhook | `GET` | `/webhook/find/{instance}` |

---

## Enviar Texto

```bash
curl -X POST http://localhost:8080/message/sendText/minha-instancia \
  -H "apikey: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5511999999999",
    "text": "Ola, tudo bem?",
    "delay": 1200,
    "linkPreview": true
  }'
```

**Parametros:**

| Campo | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| `number` | string | Sim | Telefone com DDI (5511999999999) |
| `text` | string | Sim | Conteudo da mensagem |
| `delay` | number | Nao | Delay em ms antes de enviar |
| `linkPreview` | boolean | Nao | Mostrar preview de links |
| `mentionsEveryOne` | boolean | Nao | Mencionar todos (grupos) |
| `mentioned` | array | Nao | Lista de numeros para mencionar |
| `quoted` | object | Nao | Mensagem para responder |

---

## Enviar Midia

```bash
curl -X POST http://localhost:8080/message/sendMedia/minha-instancia \
  -H "apikey: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5511999999999",
    "mediatype": "image",
    "mimetype": "image/jpeg",
    "caption": "Legenda da imagem",
    "media": "https://exemplo.com/imagem.jpg"
  }'
```

**Mediatypes:** `image`, `video`, `audio`, `document`

---

## Criar Instancia

```bash
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "minha-instancia",
    "integration": "WHATSAPP-BAILEYS",
    "qrcode": true
  }'
```

---

## Conectar (QR Code)

```bash
curl http://localhost:8080/instance/connect/minha-instancia \
  -H "apikey: sua_api_key"
```

**Response:**
```json
{
  "pairingCode": null,
  "code": "2@abc123...",
  "base64": "data:image/png;base64,..."
}
```

---

## Status da Conexao

```bash
curl http://localhost:8080/instance/connectionState/minha-instancia \
  -H "apikey: sua_api_key"
```

**Response:**
```json
{
  "instance": {
    "instanceName": "minha-instancia",
    "state": "open"
  }
}
```

**States:** `open` (conectado), `close` (desconectado), `connecting`

---

## Formatos de Numero

| Tipo | Formato | Exemplo |
|------|---------|---------|
| Individual | DDI + DDD + numero | `5511999999999` |
| Grupo | ID do grupo | `120363123456789@g.us` |

---

## Env Vars

```bash
# Evolution API
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=sua_api_key
```
