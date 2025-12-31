# Salvy Webhooks - SMS Received

> **Docs:** https://docs.salvy.com.br/api-reference/webhooks/sms-received

## Configuracao

1. Dashboard Salvy > Settings > Webhooks
2. Registrar URL: `https://seu-dominio.com/webhooks/salvy/sms`
3. Selecionar evento: `sms.received`

---

## Evento: sms.received

Emitido quando SMS chega no numero virtual.

**Headers Svix:**
```
svix-id: msg_xxxxx
svix-timestamp: 1234567890
svix-signature: v1,xxxxx
```

**Payload:**
```json
{
  "type": "sms.received",
  "timestamp": "2025-12-30T12:00:00Z",
  "data": {
    "id": "uuid-do-sms",
    "virtualPhoneAccountId": "uuid-do-numero",
    "receivedAt": "2025-12-30T12:00:00Z",
    "originPhoneNumber": "32665",
    "destinationPhoneNumber": "+5511999999999",
    "message": "Seu codigo WhatsApp e 123-456",
    "detections": {
      "whatsapp": {
        "verificationCode": "123456"
      },
      "google": {
        "verificationCode": null
      }
    }
  }
}
```

---

## Campos Importantes

| Campo | Descricao |
|-------|-----------|
| `data.destinationPhoneNumber` | Numero virtual que recebeu (E.164) |
| `data.originPhoneNumber` | Remetente (`32665` = WhatsApp) |
| `data.message` | Conteudo do SMS |
| `data.detections.whatsapp.verificationCode` | **Codigo extraido automaticamente!** |

---

## Deteccao Automatica

A Salvy detecta automaticamente codigos de verificacao:

```python
# Usar deteccao automatica (preferencial)
whatsapp_code = payload["data"]["detections"]["whatsapp"]["verificationCode"]

if whatsapp_code:
    # Codigo ja extraido! Ex: "123456"
    usar_codigo(whatsapp_code)
```

**Remetentes conhecidos WhatsApp:**
- `32665` (short code)
- `WhatsApp`

---

## Verificacao Svix

A Salvy usa **Svix** para webhooks. Verificar assinatura em producao:

```bash
pip install svix
```

```python
from svix.webhooks import Webhook

wh = Webhook(settings.SALVY_WEBHOOK_SECRET)

try:
    payload = wh.verify(request_body, {
        "svix-id": headers["svix-id"],
        "svix-timestamp": headers["svix-timestamp"],
        "svix-signature": headers["svix-signature"],
    })
    # Payload verificado!
except Exception as e:
    # Assinatura invalida
    raise HTTPException(401, "Invalid signature")
```

---

## Resposta Esperada

Responder com **HTTP 2xx** para confirmar recebimento:

```python
return {"status": "ok"}
```

Se retornar erro, Svix fara retry automatico.

---

## Teste Local

Usar ferramenta de simulacao:
https://www.standardwebhooks.com/simulate/svix

---

## Fluxo Completo

```
1. WhatsApp envia SMS com codigo
2. Salvy recebe no numero virtual
3. Salvy detecta codigo automaticamente
4. Webhook POST para sua URL
5. Seu sistema extrai detections.whatsapp.verificationCode
6. Usar codigo no Evolution API
```
