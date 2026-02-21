# Meta WhatsApp Cloud API — Quick Reference

> Sprint 66 — Referência técnica para integração com a API oficial da Meta.

## Índice

1. [Setup WABA](#1-setup-waba)
2. [Endpoints](#2-endpoints)
3. [Payloads de Envio](#3-payloads-de-envio)
4. [Payloads de Webhook](#4-payloads-de-webhook)
5. [Template Specification](#5-template-specification)
6. [Pricing](#6-pricing)
7. [Messaging Tiers](#7-messaging-tiers)
8. [Template Pacing](#8-template-pacing)
9. [Quality Rating](#9-quality-rating)
10. [MM Lite API](#10-mm-lite-api)
11. [WhatsApp Flows](#11-whatsapp-flows)
12. [Códigos de Erro](#12-codigos-de-erro)
13. [Rate Limits](#13-rate-limits)

---

## 1. Setup WABA

### Passo a passo

1. **Criar Meta Business Account** em [business.facebook.com](https://business.facebook.com)
2. **Business Verification** — submeter documentos (pode levar dias/semanas)
3. **Criar Meta App** em [developers.facebook.com](https://developers.facebook.com) → Add Product → WhatsApp
4. **Registrar número** — adicionar phone number à WABA (precisa verificar via SMS/voz)
5. **Criar System User** — Meta Business Suite → Settings → Users → System Users → Generate Token
6. **Configurar Webhook** — App Dashboard → WhatsApp → Configuration → Webhook URL

### Tokens

| Tipo | Duração | Uso |
|------|---------|-----|
| User Access Token | 1h (short-lived) | Testes |
| System User Token | Permanente | Produção (recomendado) |
| Business Integration Token | 60 dias | Alternativa |

### IDs importantes

| ID | Onde encontrar | Exemplo |
|----|----------------|---------|
| `phone_number_id` | App Dashboard → WhatsApp → API Setup | `123456789012345` |
| `waba_id` | Business Manager → WhatsApp Accounts | `987654321098765` |
| `meta_app_id` | App Dashboard → Settings → Basic | `111222333444555` |
| `meta_business_id` | Business Manager → Business Info | `666777888999000` |

### Webhook Configuration

- **URL:** `https://api.revoluna.com/webhooks/meta`
- **Verify Token:** definido em `META_WEBHOOK_VERIFY_TOKEN`
- **Subscribe to:** `messages`, `message_template_status_update`

---

## 2. Endpoints

**Base URL:** `https://graph.facebook.com/v21.0`

| Operação | Método | Endpoint |
|----------|--------|----------|
| Enviar mensagem | POST | `/{phone_number_id}/messages` |
| Upload media | POST | `/{phone_number_id}/media` |
| Download media | GET | `/{media_id}` |
| Get phone info | GET | `/{phone_number_id}` |
| Get WABA info | GET | `/{waba_id}` |
| List templates | GET | `/{waba_id}/message_templates` |
| Create template | POST | `/{waba_id}/message_templates` |
| Update template | POST | `/{waba_id}/message_templates/{template_id}` |
| Delete template | DELETE | `/{waba_id}/message_templates?name={name}` |
| Business profile | GET/POST | `/{phone_number_id}/whatsapp_business_profile` |

### Autenticação

```
Authorization: Bearer {SYSTEM_USER_ACCESS_TOKEN}
Content-Type: application/json
```

---

## 3. Payloads de Envio

### 3.1 Texto

```json
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "5511999999999",
  "type": "text",
  "text": {
    "preview_url": false,
    "body": "Oi Dr Carlos! Tudo bem?"
  }
}
```

### 3.2 Template

```json
{
  "messaging_product": "whatsapp",
  "to": "5511999999999",
  "type": "template",
  "template": {
    "name": "julia_discovery_v1",
    "language": {
      "code": "pt_BR"
    },
    "components": [
      {
        "type": "body",
        "parameters": [
          { "type": "text", "text": "Carlos" },
          { "type": "text", "text": "cardiologia" }
        ]
      },
      {
        "type": "button",
        "sub_type": "quick_reply",
        "index": "0",
        "parameters": [
          { "type": "payload", "payload": "SIM" }
        ]
      }
    ]
  }
}
```

### 3.3 Interactive — Reply Buttons

```json
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "5511999999999",
  "type": "interactive",
  "interactive": {
    "type": "button",
    "body": {
      "text": "Tem interesse nessa vaga?"
    },
    "action": {
      "buttons": [
        {
          "type": "reply",
          "reply": { "id": "INTERESSE_SIM", "title": "Tenho interesse" }
        },
        {
          "type": "reply",
          "reply": { "id": "INTERESSE_NAO", "title": "Agora não" }
        }
      ]
    }
  }
}
```

**Limites:** max 3 botões, título max 20 chars, id max 256 chars.

### 3.4 Interactive — List Message

```json
{
  "messaging_product": "whatsapp",
  "to": "5511999999999",
  "type": "interactive",
  "interactive": {
    "type": "list",
    "header": { "type": "text", "text": "Vagas disponíveis" },
    "body": { "text": "Escolha uma vaga:" },
    "action": {
      "button": "Ver vagas",
      "sections": [
        {
          "title": "Cardiologia",
          "rows": [
            { "id": "VAGA_1", "title": "São Luiz - Noturno", "description": "19h-7h, R$ 2.500" },
            { "id": "VAGA_2", "title": "Albert Einstein", "description": "7h-19h, R$ 3.000" }
          ]
        }
      ]
    }
  }
}
```

**Limites:** max 10 itens, max 10 seções, título row max 24 chars, descrição row max 72 chars.

### 3.5 Media (imagem, vídeo, documento, áudio)

```json
{
  "messaging_product": "whatsapp",
  "to": "5511999999999",
  "type": "image",
  "image": {
    "link": "https://example.com/foto.jpg",
    "caption": "Escala do mês"
  }
}
```

**Tipos suportados:** `image`, `video`, `document`, `audio`, `sticker`.

Para `audio` e `sticker`, não há campo `caption`.

### 3.6 Reaction

```json
{
  "messaging_product": "whatsapp",
  "to": "5511999999999",
  "type": "reaction",
  "reaction": {
    "message_id": "wamid.XXXXXXXXXXXX==",
    "emoji": "👍"
  }
}
```

### 3.7 Mark as Read

```json
{
  "messaging_product": "whatsapp",
  "status": "read",
  "message_id": "wamid.XXXXXXXXXXXX=="
}
```

### Response (sucesso)

```json
{
  "messaging_product": "whatsapp",
  "contacts": [{ "input": "5511999999999", "wa_id": "5511999999999" }],
  "messages": [{ "id": "wamid.XXXXXXXXXXXX==" }]
}
```

---

## 4. Payloads de Webhook

### 4.1 Mensagem recebida (texto)

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WABA_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "5511888888888",
          "phone_number_id": "PHONE_NUMBER_ID"
        },
        "contacts": [{
          "profile": { "name": "Dr Carlos" },
          "wa_id": "5511999999999"
        }],
        "messages": [{
          "from": "5511999999999",
          "id": "wamid.XXXXXXXXXXXX==",
          "timestamp": "1700000000",
          "type": "text",
          "text": { "body": "Oi, quero saber mais" }
        }]
      },
      "field": "messages"
    }]
  }]
}
```

### 4.2 Mensagem recebida (imagem)

```json
{
  "messages": [{
    "from": "5511999999999",
    "id": "wamid.XXXXXXXXXXXX==",
    "timestamp": "1700000000",
    "type": "image",
    "image": {
      "id": "MEDIA_ID",
      "mime_type": "image/jpeg",
      "sha256": "HASH",
      "caption": "Meu CRM"
    }
  }]
}
```

### 4.3 Mensagem recebida (áudio)

```json
{
  "messages": [{
    "type": "audio",
    "audio": {
      "id": "MEDIA_ID",
      "mime_type": "audio/ogg; codecs=opus"
    }
  }]
}
```

### 4.4 Interactive reply (button)

```json
{
  "messages": [{
    "type": "interactive",
    "interactive": {
      "type": "button_reply",
      "button_reply": {
        "id": "INTERESSE_SIM",
        "title": "Tenho interesse"
      }
    }
  }]
}
```

### 4.5 Interactive reply (list)

```json
{
  "messages": [{
    "type": "interactive",
    "interactive": {
      "type": "list_reply",
      "list_reply": {
        "id": "VAGA_1",
        "title": "São Luiz - Noturno",
        "description": "19h-7h, R$ 2.500"
      }
    }
  }]
}
```

### 4.6 Status updates

```json
{
  "entry": [{
    "changes": [{
      "value": {
        "statuses": [{
          "id": "wamid.XXXXXXXXXXXX==",
          "status": "delivered",
          "timestamp": "1700000000",
          "recipient_id": "5511999999999",
          "conversation": {
            "id": "CONV_ID",
            "origin": { "type": "business_initiated" },
            "expiration_timestamp": "1700086400"
          },
          "pricing": {
            "billable": true,
            "pricing_model": "CBP",
            "category": "marketing"
          }
        }]
      },
      "field": "messages"
    }]
  }]
}
```

**Status possíveis:** `sent`, `delivered`, `read`, `failed`.

**Status `failed`:**

```json
{
  "statuses": [{
    "status": "failed",
    "errors": [{
      "code": 131026,
      "title": "Message Undeliverable",
      "message": "Message could not be delivered"
    }]
  }]
}
```

### 4.7 Template status update

```json
{
  "entry": [{
    "changes": [{
      "value": {
        "event": "APPROVED",
        "message_template_id": 123456,
        "message_template_name": "julia_discovery_v1",
        "message_template_language": "pt_BR"
      },
      "field": "message_template_status_update"
    }]
  }]
}
```

**Eventos:** `APPROVED`, `REJECTED`, `PENDING_DELETION`, `DISABLED`, `PAUSED`, `IN_APPEAL`.

### 4.8 Webhook Verification (GET)

```
GET /webhooks/meta?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=CHALLENGE
```

Resposta: retornar `hub.challenge` como plain text com HTTP 200.

### 4.9 Signature Validation (POST)

Header: `X-Hub-Signature-256: sha256=HASH`

Calcular HMAC-SHA256 do body com `META_APP_SECRET` e comparar.

---

## 5. Template Specification

### Categorias

| Categoria | Uso | Preço |
|-----------|-----|-------|
| MARKETING | Prospecção, ofertas, reativação | Mais caro |
| UTILITY | Confirmações, lembretes, followup | Intermediário |
| AUTHENTICATION | OTP, verificação | Mais barato |

### Estrutura do template

```json
{
  "name": "julia_discovery_v1",
  "language": "pt_BR",
  "category": "MARKETING",
  "components": [
    {
      "type": "HEADER",
      "format": "TEXT",
      "text": "Revoluna — Escalas Médicas"
    },
    {
      "type": "BODY",
      "text": "Oi Dr {{1}}! Sou a Julia da Revoluna. Posso te contar mais?",
      "example": { "body_text": [["Carlos"]] }
    },
    {
      "type": "FOOTER",
      "text": "Revoluna - Staffing Médico"
    },
    {
      "type": "BUTTONS",
      "buttons": [
        { "type": "QUICK_REPLY", "text": "Sim" },
        { "type": "QUICK_REPLY", "text": "Agora não" }
      ]
    }
  ]
}
```

### Variáveis

- Formato: `{{1}}`, `{{2}}`, ..., `{{N}}`
- Sequenciais e começam em 1
- Máximo: 1 variável no header, ilimitadas no body
- Cada variável precisa de `example` na submissão

### Regras de aprovação

- Sem conteúdo abusivo, ameaçador ou discriminatório
- Sem URLs encurtadas (bit.ly, etc)
- Body entre 1 e 1024 caracteres
- Footer até 60 caracteres
- Header texto até 60 caracteres
- Botão quick_reply texto até 20 caracteres (max 3 botões)
- Botão CTA (URL/phone) texto até 20 caracteres (max 2 botões)
- Aprovação tipicamente leva 24-48h

---

## 6. Pricing

### Modelo CBP (Conversation-Based Pricing)

- **Janela 24h:** Após o usuário enviar mensagem, o business pode responder gratuitamente por 24h (free-form, sem template)
- **Business-initiated:** Fora da janela, precisa de template aprovado → abre conversa paga de 24h
- **User-initiated:** Dentro da janela, respostas são gratuitas
- **Free tier:** 1.000 conversas user-initiated gratuitas por mês (por WABA)

### Preços por categoria (Brasil, aproximados)

| Categoria | Preço/conversa (BRL) |
|-----------|---------------------|
| Marketing | ~R$ 0,50 |
| Utility | ~R$ 0,15 |
| Authentication | ~R$ 0,15 |
| Service (user-initiated) | Grátis (primeiras 1K/mês) |

> Preços sujeitos a mudanças. Consultar [Meta Pricing](https://developers.facebook.com/docs/whatsapp/pricing).

---

## 7. Messaging Tiers

### Progressão

| Tier | Limite (24h) | Como alcançar |
|------|-------------|---------------|
| Tier 0 | 250 conversas | Default (business não verificado) |
| Tier 1 | 1.000 conversas | Business verificado |
| Tier 2 | 10.000 conversas | Enviar 2x o tier atual em 7 dias |
| Tier 3 | 100.000 conversas | Enviar 2x o tier atual em 7 dias |
| Unlimited | Sem limite | Enviar 2x o tier atual em 7 dias |

### Regras de escalação

- Para subir de tier: enviar **2x o limite atual** em um período de 7 dias
- Quality rating deve ser **Medium** ou **High**
- Se quality cai para **Low**, tier pode ser reduzido
- A partir de Oct 2025: limites aplicados no nível do **business portfolio**, não por phone number

---

## 8. Template Pacing

Quando um novo template é criado, a Meta testa gradualmente antes de liberar 100%:

1. **Fase 1:** Template enviado para uma amostra pequena de usuários
2. **Fase 2:** Meta coleta feedback (blocks, reports)
3. **Fase 3:** Se feedback positivo → libera para 100%
4. **Se feedback negativo:** Template pode ser pausado ou desativado

### Impacto prático

- Templates novos podem ter delivery menor nas primeiras horas
- Templates com alto block rate podem ser pausados automaticamente
- Boa prática: testar com amostra pequena antes de campanha grande

---

## 9. Quality Rating

### Níveis

| Rating | Cor | Significado |
|--------|-----|-------------|
| High | 🟢 Verde | Boa qualidade, sem restrições |
| Medium | 🟡 Amarelo | Atenção, pode degradar |
| Low | 🔴 Vermelho | Risco de restrição, tier pode baixar |

### Fatores que afetam

- **Bloqueios:** Usuários bloqueando o número
- **Reports:** Usuários reportando como spam
- **Template quality:** Feedback negativo em templates
- **Response rate:** Taxa de resposta dos usuários

### Como manter quality alta

1. Respeitar opt-out imediatamente
2. Não enviar para listas compradas
3. Templates relevantes e personalizados
4. Frequência adequada (não bombardear)
5. Horário comercial respeitado

### API de quality

```
GET /{phone_number_id}?fields=quality_rating,messaging_limit
```

Response:
```json
{
  "quality_rating": "GREEN",
  "messaging_limit": {
    "tier": "TIER_10K",
    "current_limit": 10000
  }
}
```

---

## 10. MM Lite API

**MM Lite (Marketing Messages Lite)** é uma feature da Meta que melhora delivery de templates marketing:

- **+9% de delivery rate** comparado com envio padrão
- Disponível apenas para templates da categoria MARKETING
- Requer onboarding específico com a Meta
- Endpoint dedicado (mesmo base URL, parâmetro adicional)

### Como funciona

MM Lite permite que o business envie marketing templates com prioridade otimizada. A Meta decide o melhor horário para entregar, maximizando open rate.

### Requisitos

- WABA verificada
- Tier 2+ (10K+ conversas)
- Quality rating Green
- Templates marketing aprovados

> **Status para Julia:** Implementação futura (Sprint 68). Requer contato com representante Meta.

---

## 11. WhatsApp Flows

**WhatsApp Flows** permite criar formulários e fluxos interativos dentro do WhatsApp:

- Telas com inputs (texto, dropdown, date picker)
- Fluxos multi-step (ex: cadastro de documentos)
- Integração com backend via data endpoint
- Resposta estruturada (JSON)

### Casos de uso para Julia

- Coleta de documentos (CRM, RG, dados bancários)
- Pesquisa de satisfação pós-plantão
- Briefing de vaga detalhado

### Estrutura de um Flow

```json
{
  "name": "coleta_documentos",
  "categories": ["OTHER"],
  "screens": [
    {
      "id": "TELA_1",
      "title": "Seus Dados",
      "data": {},
      "layout": {
        "type": "SingleColumnLayout",
        "children": [
          { "type": "TextInput", "name": "crm", "label": "CRM" },
          { "type": "TextInput", "name": "rg", "label": "RG" }
        ]
      }
    }
  ]
}
```

> **Status para Julia:** Implementação futura (Sprint 68). Útil para coleta de documentos.

---

## 12. Códigos de Erro

### Erros comuns de envio

| Código | Título | Causa | Solução |
|--------|--------|-------|---------|
| 131026 | Message Undeliverable | Fora da janela 24h sem template | Usar template aprovado |
| 131047 | Re-engagement Message | Mais de 24h sem resposta | Enviar template |
| 131049 | Rate Limit Hit | Muitas requisições/segundo | Reduzir throughput |
| 131051 | Spam Rate Limit Hit | Muitos templates rejeitados | Melhorar quality |
| 131053 | Media Upload Error | Erro ao processar mídia | Verificar URL/formato |
| 131056 | Pair Rate Limit | Muitas msgs para mesmo número | Aguardar cooldown |
| 130429 | Throughput Limit | Excedeu 80/1000 MPS | Throttle requests |
| 132000 | Template Not Found | Template não existe/aprovado | Verificar nome e status |
| 132001 | Template Text Too Long | Corpo excede 1024 chars | Reduzir texto |
| 132012 | Template Parameter Format Mismatch | Variáveis incorretas | Verificar mapeamento |
| 133010 | Phone Number Not Registered | Número não está no WhatsApp | Verificar número |

### Erros de autenticação

| Código | Causa | Solução |
|--------|-------|---------|
| 190 | Access token expirado | Renovar token |
| 10 | Permissão negada | Verificar scopes do token |
| 100 | Parâmetro inválido | Verificar payload |
| 4 | Too many calls | Rate limit da Graph API |

### Erro de webhook

| Código | Causa | Solução |
|--------|-------|---------|
| 400 | Payload malformado | Verificar JSON |
| 403 | Verify token incorreto | Corrigir META_WEBHOOK_VERIFY_TOKEN |

---

## 13. Rate Limits

### Throughput (MPS — Messages Per Second)

| Nível | MPS | Requisito |
|-------|-----|-----------|
| Default | 80 | Qualquer WABA |
| Upgraded | 1.000 | Tier Unlimited + quality Medium+ + 100K msgs em 24h |

### Requisição Graph API

| Tipo | Limite | Janela |
|------|--------|--------|
| Envio de mensagens | 80 MPS (default) | Por segundo |
| Template CRUD | 600/hora | Por hora |
| Media upload | 500/hora | Por hora |
| Outros endpoints | 200/hora | Por hora |

### Webhooks recebidos (estimativa)

Cada mensagem enviada pode gerar até **3 webhooks** (sent → delivered → read).

A 80 MPS de envio: até **240 webhooks/segundo**.
A 1000 MPS: até **3000 webhooks/segundo**.

### Boas práticas

1. **Retornar 200 imediatamente** no webhook, processar em background
2. **Manter latência < 250ms** no endpoint de webhook
3. **Implementar retry com backoff** para erros 429
4. **Monitorar throughput** e escalar conforme necessário
5. **Webhook retry:** Meta retenta por até 7 dias em caso de falha

---

## Referências

- [Meta Cloud API Docs](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Graph API Reference](https://developers.facebook.com/docs/graph-api/reference)
- [Template Guidelines](https://developers.facebook.com/docs/whatsapp/message-templates/guidelines)
- [Pricing](https://developers.facebook.com/docs/whatsapp/pricing)
- [Webhooks Reference](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [Error Codes](https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes)
