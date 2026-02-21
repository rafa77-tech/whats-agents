# EPIC 03: Webhook Meta + Pipeline Integration

## Status: Implementado

## Contexto

Receber eventos da Meta (mensagens, status, template updates) e processar no pipeline existente da Julia. Segue o padrao do `webhook_zapi.py` com conversao Meta → Evolution para manter compatibilidade com o pipeline.

## Escopo

- **Incluido**: Webhook verification (GET), message reception (POST), signature validation, payload conversion Meta→Evolution, status updates, template status
- **Excluido**: Template management CRUD (epic 04), window tracking (epic 05)

---

## Tarefa 03.1: Webhook endpoint

### Arquivo: `app/api/routes/webhook_meta.py` (477 linhas)

#### GET /webhooks/meta — Verificacao Hub

Meta envia GET com `hub.mode`, `hub.verify_token`, `hub.challenge`.
- Token correto → responde com challenge (200)
- Token errado ou mode errado → 403

#### POST /webhooks/meta — Processamento

1. Validar `X-Hub-Signature-256` (HMAC SHA256 com `META_APP_SECRET`)
2. Extrair `entry[].changes[].value` do payload
3. Rotear por field:
   - `messages` → `_processar_mensagem_recebida()`
   - `statuses` → `_processar_status_mensagem()`
   - `message_template_status_update` → `_processar_template_status()`
4. Buscar chip por `_obter_chip_por_meta_phone_number_id(metadata.phone_number_id)`
5. Retornar 200 imediatamente

#### Funcoes auxiliares

| Funcao | Descricao |
|--------|-----------|
| `_validar_signature(request, body)` | HMAC SHA256 com `hmac.compare_digest` (timing-safe). Sem `META_APP_SECRET` → aceita tudo (dev mode) |
| `_obter_chip_por_meta_phone_number_id(phone_number_id)` | Query na tabela chips |
| `_processar_mensagem_recebida(message, contacts, chip)` | Converte para formato Evolution + pipeline |
| `_extrair_texto_mensagem(message)` | Extrai texto de qualquer tipo de mensagem |
| `_converter_meta_para_formato_evolution(message, contacts, chip)` | Conversao completa Meta → Evolution |
| `_processar_no_pipeline(dados_evolution, chip)` | Envia para pipeline Julia existente |
| `_processar_status_mensagem(status, chip)` | Atualiza delivery_status |
| `_processar_template_status(update)` | Atualiza status do template no banco |

#### Conversao Meta → Evolution

| Campo Meta | Campo Evolution |
|-----------|-----------------|
| `message.from` | `key.remoteJid` (+ `@s.whatsapp.net`) |
| `message.id` | `key.id` |
| `message.text.body` | `message.conversation` |
| `message.image.caption` | `message.conversation` + `message.imageMessage` |
| `message.audio` | `message.audioMessage` |
| `message.document` | `message.documentMessage` |
| `message.video` | `message.videoMessage` |
| `message.interactive.button_reply.title` | `message.conversation` |
| `message.interactive.list_reply.title` | `message.conversation` |
| `contacts[0].profile.name` | `pushName` |
| `message.timestamp` | `messageTimestamp` |

Campos extras adicionados:
- `_provider: "meta"`
- `_meta_chip_id: chip["id"]`
- `_meta_telefone: chip["telefone"]`

#### Extrair texto por tipo

| Tipo | Fonte |
|------|-------|
| text | `text.body` |
| image | `image.caption` ou `[imagem]` |
| audio | `[audio]` |
| video | `video.caption` ou `[video]` |
| document | `document.filename` ou `[documento]` |
| reaction | `reaction.emoji` |
| interactive (button_reply) | `button_reply.title` |
| interactive (list_reply) | `list_reply.title` |
| outros | `[{type}]` |

### Registro em main.py

```python
from app.api.routes.webhook_meta import router as webhook_meta_router
app.include_router(webhook_meta_router, prefix="/webhooks/meta", tags=["Webhook Meta"])
```

---

## Tarefa 03.2: Delivery Status — Meta Normalization

### Arquivo: `app/services/delivery_status.py`

Adicionado mapeamento Meta ao `_normalizar_status()`:

| Status Meta | Status Normalizado |
|------------|-------------------|
| `SENT` | `sent` |
| `ACCEPTED` | `sent` |
| `DELIVERED` | `delivered` |
| `READ` | `read` |
| `FAILED` | `failed` |

Status Evolution e Z-API continuam inalterados.

---

## Testes

### `tests/api/routes/test_webhook_meta.py` (24 testes)

| Classe | Testes |
|--------|--------|
| TestVerificacaoWebhook | token_correto, token_errado, mode_errado |
| TestSignatureValidation | valida, invalida, sem_header, sem_prefixo_sha256, sem_app_secret_aceita |
| TestConversaoMetaEvolution | texto, imagem, audio, documento, video, button_reply, list_reply, sem_contacts, metadados_meta |
| TestExtrairTextoMensagem | texto, imagem_com_caption, imagem_sem_caption, audio, reaction, tipo_desconhecido |
| TestDeliveryStatusMeta | SENT, ACCEPTED, DELIVERED, READ, FAILED, evolution_delivery_ack, zapi_played |

---

## Definition of Done

- [x] GET verification funcional (challenge/403)
- [x] POST com signature validation (HMAC SHA256)
- [x] Conversao Meta→Evolution para text, image, audio, document, video, interactive
- [x] Status updates processados (sent, delivered, read, failed)
- [x] Template status updates processados
- [x] Router registrado em main.py
- [x] 24 testes unitarios passando
- [x] Dev mode: sem META_APP_SECRET aceita tudo

## Gaps Identificados

- [ ] Webhook nao processa mensagens tipo `sticker`, `location`, `contacts` (retorna `[{type}]`)
- [ ] Nao ha testes de integracao com pipeline Julia real
- [ ] `_obter_chip_por_meta_phone_number_id` nao tem cache (query a cada webhook)
