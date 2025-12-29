# Playbook: Ponte Médico-Divulgador

Documentação operacional para gerenciamento da ponte externa (external handoff).

**Sprint:** 21 - Production Gate

---

## 1. Pausar Ponte Externa

### Via Slack
```
toggle_ponte_externa off
```

### Efeitos
- Novas pontes: bloqueadas
- Follow-ups: pausados
- Confirmações existentes: continuam funcionando
- Handoffs pendentes: continuam expirando normalmente

### Verificar Status
```
toggle_ponte_externa status
```

---

## 2. Identificar Handoffs Pendentes

### Query Rápida (Pendentes)
```sql
SELECT
    id,
    divulgador_nome,
    divulgador_telefone,
    status,
    followup_count,
    created_at,
    reserved_until,
    EXTRACT(EPOCH FROM (reserved_until - now()))/3600 as horas_restantes
FROM external_handoffs
WHERE status IN ('pending', 'contacted')
ORDER BY created_at ASC;
```

### Query: Pendentes há mais de 24h
```sql
SELECT
    id,
    divulgador_nome,
    status,
    followup_count,
    created_at,
    EXTRACT(EPOCH FROM (now() - created_at))/3600 as horas_idade
FROM external_handoffs
WHERE status IN ('pending', 'contacted')
  AND created_at < now() - interval '24 hours'
ORDER BY created_at ASC;
```

### Query: Taxa de Confirmação
```sql
SELECT
    status,
    COUNT(*) as quantidade,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER() * 100, 1) as percentual
FROM external_handoffs
WHERE created_at > now() - interval '7 days'
GROUP BY status
ORDER BY quantidade DESC;
```

---

## 3. Forçar Expiração

### Expirar Handoff Específico
```sql
UPDATE external_handoffs
SET
    status = 'expired',
    expired_at = now(),
    updated_at = now()
WHERE id = '<handoff_id>'
  AND status IN ('pending', 'contacted');

-- Liberar vaga associada
UPDATE vagas
SET status = 'aberta'
WHERE id = (SELECT vaga_id FROM external_handoffs WHERE id = '<handoff_id>');
```

### Expirar Todos Pendentes há mais de 72h
```sql
WITH expired AS (
    UPDATE external_handoffs
    SET
        status = 'expired',
        expired_at = now(),
        updated_at = now()
    WHERE status IN ('pending', 'contacted')
      AND reserved_until < now() - interval '24 hours'
    RETURNING id, vaga_id
)
UPDATE vagas
SET status = 'aberta'
WHERE id IN (SELECT vaga_id FROM expired);
```

---

## 4. Registrar Opt-out Divulgador

### Via SQL
```sql
INSERT INTO external_contacts (telefone, nome, empresa, permission_state, opted_out_at, opted_out_reason)
VALUES (
    '+5511999998888',
    'Nome do Divulgador',
    'Empresa XYZ',
    'opted_out',
    now(),
    'Solicitou remoção via WhatsApp'
)
ON CONFLICT (telefone) DO UPDATE SET
    permission_state = 'opted_out',
    opted_out_at = now(),
    opted_out_reason = EXCLUDED.opted_out_reason,
    updated_at = now();
```

### Verificar Opt-outs
```sql
SELECT telefone, nome, empresa, opted_out_at, opted_out_reason
FROM external_contacts
WHERE permission_state = 'opted_out'
ORDER BY opted_out_at DESC;
```

### Reverter Opt-out (se solicitado)
```sql
UPDATE external_contacts
SET
    permission_state = 'active',
    opted_out_at = NULL,
    opted_out_reason = NULL,
    updated_at = now()
WHERE telefone = '+5511999998888';
```

---

## 5. Reverter Confirmação Errada

### Reverter Confirmed -> Pendente
```sql
-- 1. Reverter handoff
UPDATE external_handoffs
SET
    status = 'contacted',
    confirmed_at = NULL,
    confirmed_by = NULL,
    updated_at = now()
WHERE id = '<handoff_id>';

-- 2. Reabrir vaga
UPDATE vagas
SET status = 'aberta'
WHERE id = (SELECT vaga_id FROM external_handoffs WHERE id = '<handoff_id>');
```

### Reverter Not Confirmed -> Pendente
```sql
UPDATE external_handoffs
SET
    status = 'contacted',
    not_confirmed_at = NULL,
    confirmed_by = NULL,
    updated_at = now()
WHERE id = '<handoff_id>';
```

**IMPORTANTE:** Após reverter, notificar o divulgador manualmente que o status foi revertido.

---

## 6. Critérios de Escalonamento

### Nível 1 - Ops (Auto-resolução)
- Handoff pendente há mais de 24h com 0 follow-ups
- Divulgador não responde após 3 follow-ups
- Taxa de confirmação abaixo de 20% em 7 dias

### Nível 2 - Gestão (Intervenção)
- Reclamação de divulgador sobre excesso de mensagens
- Divulgador solicita remoção permanente (opt-out)
- Erro técnico impedindo confirmações

### Nível 3 - Produto (Decisão)
- Mudança nas regras de horário comercial
- Ajuste nos limites de rate limiting
- Alteração no fluxo de follow-ups

---

## 7. Monitoramento

### Queries para Dashboard

#### Handoffs por Status (últimos 7 dias)
```sql
SELECT
    DATE(created_at) as data,
    status,
    COUNT(*) as quantidade
FROM external_handoffs
WHERE created_at > now() - interval '7 days'
GROUP BY DATE(created_at), status
ORDER BY data DESC, status;
```

#### Tempo Médio até Confirmação
```sql
SELECT
    DATE(created_at) as data,
    ROUND(AVG(EXTRACT(EPOCH FROM (confirmed_at - created_at))/3600), 1) as horas_media
FROM external_handoffs
WHERE status = 'confirmed'
  AND confirmed_at IS NOT NULL
  AND created_at > now() - interval '7 days'
GROUP BY DATE(created_at)
ORDER BY data DESC;
```

#### Follow-ups por Handoff
```sql
SELECT
    followup_count,
    COUNT(*) as quantidade,
    status
FROM external_handoffs
WHERE created_at > now() - interval '7 days'
GROUP BY followup_count, status
ORDER BY followup_count, status;
```

---

## 8. Checklist de Incidente

1. [ ] Identificar scope do problema
2. [ ] Pausar ponte se necessário (`toggle_ponte_externa off`)
3. [ ] Notificar equipe no Slack
4. [ ] Coletar logs relevantes
5. [ ] Aplicar fix ou workaround
6. [ ] Verificar normalização
7. [ ] Retomar ponte se pausada (`toggle_ponte_externa on`)
8. [ ] Documentar incidente

---

*Última atualização: Sprint 21 (29/12/2025)*
