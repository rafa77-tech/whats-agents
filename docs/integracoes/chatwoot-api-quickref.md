# Chatwoot API - Quick Reference

> **Docs oficiais:** https://developers.chatwoot.com/
> **GitHub:** https://github.com/chatwoot/chatwoot

## Visao Geral

Chatwoot e uma plataforma open-source de atendimento ao cliente com suporte a multiplos canais.

**Base URL:** `https://seu-chatwoot.com/api/v1`

---

## Autenticacao

Todas as requisicoes precisam do header `api_access_token`:

```
Header: api_access_token: <seu_token>
Content-Type: application/json
```

**Onde obter o token:**
1. Login no Chatwoot
2. Profile Settings → Access Token
3. Copiar o token

---

## Endpoints Principais

### Conversations

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Listar | `GET` | `/accounts/{account_id}/conversations` |
| Criar | `POST` | `/accounts/{account_id}/conversations` |
| Detalhes | `GET` | `/accounts/{account_id}/conversations/{id}` |
| Atualizar | `PATCH` | `/accounts/{account_id}/conversations/{id}` |
| Filtrar | `POST` | `/accounts/{account_id}/conversations/filter` |
| Contagem | `GET` | `/accounts/{account_id}/conversations/meta` |

### Messages

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Listar | `GET` | `/accounts/{account_id}/conversations/{conv_id}/messages` |
| Criar | `POST` | `/accounts/{account_id}/conversations/{conv_id}/messages` |
| Deletar | `DELETE` | `/accounts/{account_id}/messages/{id}` |

### Contacts

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Listar | `GET` | `/accounts/{account_id}/contacts` |
| Criar | `POST` | `/accounts/{account_id}/contacts` |
| Detalhes | `GET` | `/accounts/{account_id}/contacts/{id}` |
| Atualizar | `PUT` | `/accounts/{account_id}/contacts/{id}` |
| Deletar | `DELETE` | `/accounts/{account_id}/contacts/{id}` |
| Buscar | `GET` | `/accounts/{account_id}/contacts/search?q=email` |
| Filtrar | `POST` | `/accounts/{account_id}/contacts/filter` |
| Conversas | `GET` | `/accounts/{account_id}/contacts/{id}/conversations` |

### Inboxes

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Listar | `GET` | `/accounts/{account_id}/inboxes` |
| Criar | `POST` | `/accounts/{account_id}/inboxes` |
| Detalhes | `GET` | `/accounts/{account_id}/inboxes/{id}` |
| Atualizar | `PATCH` | `/accounts/{account_id}/inboxes/{id}` |

### Agents

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Listar | `GET` | `/accounts/{account_id}/agents` |
| Adicionar | `POST` | `/accounts/{account_id}/agents` |
| Atualizar | `PATCH` | `/accounts/{account_id}/agents/{id}` |
| Remover | `DELETE` | `/accounts/{account_id}/agents/{id}` |

### Labels

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Listar | `GET` | `/accounts/{account_id}/labels` |
| Criar | `POST` | `/accounts/{account_id}/labels` |

---

## Enviar Mensagem

```bash
curl -X POST https://chatwoot.example.com/api/v1/accounts/1/conversations/123/messages \
  -H "api_access_token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Ola, como posso ajudar?",
    "message_type": "outgoing",
    "private": false
  }'
```

**Parametros:**

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `content` | string | Texto da mensagem |
| `message_type` | string | `outgoing` (para cliente) ou `incoming` |
| `private` | boolean | `true` = nota interna (nao visivel ao cliente) |
| `content_attributes` | object | Metadados adicionais |

---

## Criar Contato

```bash
curl -X POST https://chatwoot.example.com/api/v1/accounts/1/contacts \
  -H "api_access_token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Carlos Silva",
    "email": "carlos@email.com",
    "phone_number": "+5511999999999",
    "identifier": "5511999999999",
    "custom_attributes": {
      "crm": "123456",
      "especialidade": "cardiologia"
    }
  }'
```

---

## Buscar Contato por Telefone

```bash
curl "https://chatwoot.example.com/api/v1/accounts/1/contacts/search?q=5511999999999" \
  -H "api_access_token: seu_token"
```

---

## Atualizar Status da Conversa

```bash
curl -X PATCH https://chatwoot.example.com/api/v1/accounts/1/conversations/123 \
  -H "api_access_token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved"
  }'
```

**Status disponiveis:**
- `open` - Aberta
- `resolved` - Resolvida
- `pending` - Pendente
- `snoozed` - Adiada

---

## Atribuir Conversa a Agente

```bash
curl -X POST https://chatwoot.example.com/api/v1/accounts/1/conversations/123/assignments \
  -H "api_access_token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{
    "assignee_id": 5
  }'
```

---

## Adicionar Label a Conversa

```bash
curl -X POST https://chatwoot.example.com/api/v1/accounts/1/conversations/123/labels \
  -H "api_access_token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{
    "labels": ["humano", "urgente"]
  }'
```

---

## Listar Mensagens de uma Conversa

```bash
curl "https://chatwoot.example.com/api/v1/accounts/1/conversations/123/messages" \
  -H "api_access_token: seu_token"
```

---

## Paginacao

A maioria dos endpoints de listagem suporta paginacao:

```bash
curl "https://chatwoot.example.com/api/v1/accounts/1/contacts?page=2" \
  -H "api_access_token: seu_token"
```

**Page size padrao:** 15 itens

---

## Env Vars

```bash
# Chatwoot
CHATWOOT_BASE_URL=https://seu-chatwoot.com
CHATWOOT_API_KEY=seu_api_access_token
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1
```
