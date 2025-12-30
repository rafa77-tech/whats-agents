# Smoke Test Pós-Deploy

## Pré-requisitos

- [ ] Deploy no Railway concluído
- [ ] Health check básico respondendo
- [ ] Redis conectado
- [ ] Supabase conectado

---

## 5 Testes Obrigatórios

### 1. Deep Health Check

```bash
curl -s https://SEU-APP.railway.app/health/deep | jq .
```

**Esperado:**
```json
{
  "status": "healthy",
  "checks": {
    "environment": {"status": "ok"},
    "project_ref": {"status": "ok"},
    "redis": {"status": "ok"},
    "supabase": {"status": "ok"},
    "tables": {"status": "ok", "missing": []},
    "views": {"status": "ok", "missing": []},
    "schema_version": {"status": "ok"}
  },
  "deploy_safe": true
}
```

**Se falhar:** Verificar variáveis de ambiente e markers no banco.

---

### 2. Reconciliation Job (Dry Run)

```bash
curl -X POST "https://SEU-APP.railway.app/jobs/reconcile-touches?limite=1&horas=1" \
  -H "Authorization: Bearer SEU_JWT_TOKEN" | jq .
```

**Esperado:**
```json
{
  "status": "completed",
  "candidates_found": 0,
  "processed": 0
}
```

**Se falhar:** Verificar se view `campaign_sends` existe.

---

### 3. Redis Write/Read

```bash
# O health/deep já valida Redis, mas para teste adicional:
curl -s https://SEU-APP.railway.app/health/rate-limit | jq .
```

**Esperado:** Retorna estatísticas de rate limit (mesmo que zeradas).

---

### 4. Teste Fora do Horário

Simular inbound fora do horário comercial:

```bash
# Horário comercial: 08:00-20:00
# Se estiver fora desse horário, qualquer inbound deve ir para mensagens_fora_horario

# Via SQL no Supabase (após receber mensagem de teste):
SELECT * FROM mensagens_fora_horario ORDER BY created_at DESC LIMIT 1;
```

**Esperado:** Mensagem persistida se fora do horário.

---

### 5. Outbound Unitário (Sem Campanha)

Testar envio de 1 mensagem para número de teste:

```bash
# Via endpoint admin (se existir) ou diretamente via Evolution API

# Depois verificar no banco:
SELECT 
    cliente_id,
    outcome,
    provider_message_id,
    outcome_at
FROM fila_mensagens 
WHERE cliente_id = 'ID_DO_TESTE'
ORDER BY created_at DESC LIMIT 1;
```

**Esperado:**
- `outcome` = 'SENT' ou 'DELIVERED'
- `provider_message_id` preenchido

---

## Checklist Final

```
[ ] /health/deep retorna 200 com todos checks ok
[ ] /jobs/reconcile-touches executa sem erro
[ ] Rate limit stats retorna (Redis ok)
[ ] Mensagem fora do horário persiste (se aplicável)
[ ] Outbound unitário funciona com outcome correto
[ ] Logs no Railway sem erros críticos
```

---

## Após Smoke Test Passar

1. Ativar Julia:
   ```sql
   INSERT INTO julia_status (status, motivo, alterado_via)
   VALUES ('ativo', 'Smoke test passou - ativando', 'manual');
   ```

2. Apontar webhook Evolution para Railway URL

3. Monitorar primeiras interações reais

---

## Se Algo Falhar

1. **NÃO apontar webhook Evolution**
2. Verificar logs no Railway
3. Corrigir problema
4. Re-executar smoke test
5. Só então ativar
