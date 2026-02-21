# EPIC 02: MetaCloudProvider + Factory

## Status: Implementado

## Contexto

Terceiro provider do pool de chips da Julia, seguindo o padrao exato do `EvolutionProvider` e `ZApiProvider`. Provider fica simples — apenas envia e recebe via Graph API.

## Escopo

- **Incluido**: `MetaCloudProvider` com todos os metodos, factory update, ProviderType enum
- **Excluido**: Logica de janela 24h (epic 05), template management (epic 04), webhook (epic 03)

---

## Tarefa 02.1: Extend ProviderType e MessageResult

### Arquivo: `app/services/whatsapp_providers/base.py`

Adicionado `META = "meta"` ao enum `ProviderType` e campo `meta_message_status: Optional[str] = None` ao `MessageResult`.

### Testes
- `ProviderType.META.value == "meta"` — OK
- `MessageResult` aceita `meta_message_status` — OK
- Testes existentes nao quebram — OK

---

## Tarefa 02.2: MetaCloudProvider

### Arquivo: `app/services/whatsapp_providers/meta_cloud.py` (318 linhas)

Classe `MetaCloudProvider(WhatsAppProvider)` com:

| Metodo | Descricao |
|--------|-----------|
| `__init__(phone_number_id, access_token, waba_id)` | Armazena credenciais, constroi URL base |
| `messages_url` (property) | `https://graph.facebook.com/{version}/{phone_number_id}/messages` |
| `headers` (property) | `Authorization: Bearer {token}`, `Content-Type: application/json` |
| `_post_message(payload)` | POST generico com error handling |
| `_extract_error(response)` | Extrai codigo/mensagem de erro da resposta Meta |
| `send_text(phone, message)` | Envia texto (`messaging_product=whatsapp`, `type=text`) |
| `send_template(phone, template_name, language, components)` | Envia template com components opcionais |
| `send_interactive(phone, interactive)` | Envia buttons/lists interativos |
| `send_media(phone, url, caption, media_type)` | Envia image/video/document/audio via URL |
| `send_reaction(phone, message_id, emoji)` | Envia reacao a mensagem |
| `mark_as_read(message_id)` | Marca mensagem como lida (read receipt) |
| `get_status()` | Sempre `ConnectionStatus(connected=True, state="open")` |
| `is_connected()` | Sempre `True` (API oficial = sempre conectada) |
| `disconnect()` | Sempre `False` (nao faz sentido desconectar API oficial) |

### Error Handling

| Erro | Tratamento |
|------|-----------|
| `httpx.HTTPStatusError` | Extrai error code/message do JSON Meta |
| `httpx.TimeoutException` | Retorna `error="meta_timeout"` |
| `httpx.ConnectError` | Retorna `error="meta_connect_error"` |
| HTTP 401 | `error="meta_error_190"` (token invalido) |
| HTTP 429 | `error="meta_error_4"` (rate limit) |
| HTTP 400 code 131026 | `error="meta_error_131026"` (fora da janela 24h) |

### Testes: `tests/services/test_meta_cloud_provider.py` (25 testes)

| Classe | Testes |
|--------|--------|
| TestProviderSetup | provider_type, messages_url, headers |
| TestSendText | sucesso, erro_400, timeout, connect_error |
| TestSendTemplate | sucesso com components, sem components |
| TestSendInteractive | buttons, list |
| TestSendMedia | 4 tipos parametrizados + audio sem caption |
| TestSendReaction | payload correto |
| TestMarkAsRead | payload correto |
| TestConnectionStatus | always connected, is_connected, disconnect |
| TestErrorHandling | 401 token invalido, 429 rate limit |
| TestMessageResultExtension | meta_message_status field, default None |

---

## Tarefa 02.3: Factory update

### Arquivo: `app/services/whatsapp_providers/__init__.py`

Factory `get_provider()` agora suporta 3 providers:
- `evolution` → `EvolutionProvider`
- `z-api` → `ZApiProvider`
- `meta` → `MetaCloudProvider(phone_number_id, access_token, waba_id)`

Validacao: chip Meta sem `meta_phone_number_id` ou `meta_access_token` → `ValueError`.

---

## Definition of Done

- [x] ProviderType.META adicionado ao enum
- [x] MessageResult com meta_message_status
- [x] MetaCloudProvider com 14 metodos
- [x] Factory suporta 3 providers
- [x] 25 testes unitarios passando
- [x] Error handling para timeout, connect error, HTTP 400/401/429
