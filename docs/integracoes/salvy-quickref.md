# Salvy API - Quick Reference

> **Docs:** https://docs.salvy.com.br/api-reference/virtual-phone-accounts/introduction

## Auth

```
Authorization: Bearer <SALVY_API_TOKEN>
Base URL: https://api.salvy.com.br/api/v2
```

---

## Endpoints

| Operacao | Metodo | Endpoint |
|----------|--------|----------|
| Criar numero | `POST` | `/virtual-phone-accounts` |
| Listar numeros | `GET` | `/virtual-phone-accounts` |
| Buscar numero | `GET` | `/virtual-phone-accounts/{id}` |
| Cancelar numero | `DELETE` | `/virtual-phone-accounts/{id}` |
| Listar DDDs | `GET` | `/virtual-phone-accounts/area-codes` |

---

## Criar Numero

```bash
curl -X POST https://api.salvy.com.br/api/v2/virtual-phone-accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"areaCode": 11, "name": "julia-001"}'
```

**Response:**
```json
{
  "id": "uuid",
  "phoneNumber": "+5511999999999",
  "status": "active",
  "createdAt": "2025-12-30T12:00:00Z"
}
```

---

## Cancelar Numero

```bash
curl -X DELETE https://api.salvy.com.br/api/v2/virtual-phone-accounts/{id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"reason": "whatsapp-ban"}'
```

**Reasons:** `unnecessary`, `whatsapp-ban`, `technical-issues`, `company-canceled`

**Response:** `204 No Content`

---

## Listar DDDs

```bash
curl https://api.salvy.com.br/api/v2/virtual-phone-accounts/area-codes?available=true \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "areaCodes": [
    {"areaCode": 11, "available": true},
    {"areaCode": 21, "available": true}
  ]
}
```

---

## Status Codes

| Codigo | Significado |
|--------|-------------|
| `200` | Sucesso |
| `204` | Sucesso (sem conteudo) |
| `401` | Token invalido |
| `404` | Nao encontrado |
| `422` | Erro validacao |

---

## Status do Numero

| Status | Descricao |
|--------|-----------|
| `active` | Ativo e funcional |
| `pending` | Aguardando ativacao |
| `blocked` | Bloqueado pela operadora |
| `canceled` | Cancelado |

---

## Env Vars

```bash
SALVY_API_TOKEN=seu_token
SALVY_WEBHOOK_SECRET=whsec_xxx
SALVY_DEFAULT_DDD=11
```
