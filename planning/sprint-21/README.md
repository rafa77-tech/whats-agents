# Sprint 21: Production Gate - Ponte Externa

**Status:** Completa
**Inicio:** 29/12/2025
**Conclusao:** 29/12/2025
**Duracao:** 1 dia
**Dependencias:** Sprint 20 (External Handoff)

---

## Objetivo

Implementar **controles de producao** para a ponte externa (Sprint 20), garantindo:
- Rollout gradual via canary
- Kill switch especifico
- Protecao contra abuso
- Guardrails para divulgador
- Consistencia de dados
- Documentacao operacional

---

## Epicos

| # | Epico | Descricao | Estimativa |
|---|-------|-----------|------------|
| E01 | Canary Flag | Flag external_handoff + canary_pct + hash deterministico | 1h |
| E02 | Kill Switch | toggle_ponte_externa no Slack | 1h |
| E03 | Rate Limit | Rate limit no endpoint /handoff/confirm | 1h |
| E04 | Guardrails Divulgador | Opt-out + horario comercial | 1.5h |
| E05 | Unique Constraint | UNIQUE parcial por vaga ativa | 30min |
| E06 | Playbook | Documentacao operacional | 30min |

**Total:** ~5.5h

---

## E01: Canary Flag

### Objetivo
Flag `external_handoff` com rollout gradual via `canary_pct`.

### Implementacao

1. Criar registro em `feature_flags`:
```json
{
  "key": "external_handoff",
  "value": {
    "enabled": false,
    "canary_pct": 0
  }
}
```

2. Adicionar funcoes em `app/services/policy/flags.py`:
- `get_external_handoff_flags()`
- `is_external_handoff_enabled(cliente_id: str) -> bool`
  - Se enabled=false: retorna False
  - Se canary_pct < 100: hash(cliente_id) % 100 < canary_pct

3. Aplicar em `criar_ponte_externa()`:
- Se desabilitado: retorna erro amigavel + notifica Slack
- Nao envia msgs, nao cria handoff

### Aceite
- [x] Flag existe no banco
- [x] canary_pct=0 bloqueia todas as pontes
- [x] canary_pct=50 libera ~50% dos clientes
- [x] Mudanca reflete em ate 30s (cache TTL)

---

## E02: Kill Switch Slack

### Objetivo
Tool `toggle_ponte_externa on|off|status` no Slack.

### Implementacao

1. Criar tool em `app/tools/slack/sistema.py`:
```python
TOOL_TOGGLE_PONTE = {
    "name": "toggle_ponte_externa",
    "parameters": {"acao": "on|off|status"},
}

async def handle_toggle_ponte_externa(params, user_id):
    # Escreve flag external_handoff.enabled
    # Emite evento para auditoria
```

2. Registrar no executor

### Aceite
- [x] `toggle_ponte_externa off` para novas pontes imediatamente
- [x] `toggle_ponte_externa status` mostra enabled + canary_pct + updated_by
- [x] `toggle_ponte_externa on` reativa
- [x] Auditoria via business_event

---

## E03: Rate Limit Endpoint

### Objetivo
Rate limit no `/handoff/confirm` para prevenir abuso.

### Implementacao

1. Criar middleware/decorator de rate limit:
- 30 req/min por IP
- 200 req/h por IP
- Storage: Redis

2. Aplicar no endpoint `/handoff/confirm`

3. Retornar HTTP 429 + HTML amigavel se exceder

### Aceite
- [x] Limite por IP funciona
- [x] HTTP 429 com pagina HTML
- [x] Clique legitimo nao e bloqueado
- [x] Persistencia em Redis

---

## E04: Guardrails Divulgador

### Objetivo
Respeitar opt-out e horario comercial para divulgadores.

### 4.1 Opt-out

1. Criar tabela `external_contacts`:
```sql
CREATE TABLE external_contacts (
    telefone TEXT PRIMARY KEY,
    nome TEXT,
    empresa TEXT,
    permission_state TEXT DEFAULT 'active',
    opted_out_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

2. Antes de enviar msg ao divulgador:
- Buscar em external_contacts
- Se opted_out: nao envia, cria handoff_manual_required

### 4.2 Horario Comercial

1. Verificar horario antes de enviar ao divulgador:
- 08:00-20:00 seg-sex
- Se fora: agendar para proximo horario valido

### Aceite
- [x] Divulgador opted_out nao recebe msg
- [x] Mensagem fora do horario e bloqueada (agendamento futuro)
- [x] Slack notificado em casos manual_required

---

## E05: Unique Constraint

### Objetivo
Apenas 1 handoff ativo por vaga.

### Implementacao

Migration:
```sql
CREATE UNIQUE INDEX idx_eh_unique_active_vaga
ON external_handoffs (vaga_id)
WHERE status IN ('pending', 'contacted');
```

### Aceite
- [x] 2 medicos nao conseguem ponte simultanea para mesma vaga
- [x] Apos expiracao/not_confirmed, vaga fica elegivel novamente

---

## E06: Playbook

### Objetivo
Documentacao operacional minima.

### Arquivo: `docs/playbook-handoff.md`

Conteudo:
1. Como pausar ponte externa
2. Como identificar handoffs pendentes
3. Como forcar expiracao
4. Como registrar opt-out divulgador
5. Como reverter confirmacao errada
6. Criterios de escalonamento

### Aceite
- [x] Documento existe
- [x] Linkado em docs/README.md

---

## Ordem de Execucao

```
E01 (Flag) + E05 (Unique) -> E02 (Toggle) -> E03 (Rate Limit) -> E04 (Guardrails) -> E06 (Playbook)
```

---

## Respostas as Perguntas do Checklist

### Rollback seguro
Quando `external_handoff.enabled=false`:
- Handoffs existentes continuam expirando normalmente
- Follow-ups sao pausados (verificar flag antes de enviar)
- Confirmacoes via link/keyword ainda funcionam

### Reversao de confirmacao
Criar endpoint admin ou Slack tool para:
- Reverter handoff confirmed -> not_confirmed
- Reabrir vaga

### Observabilidade
Queries prontas no playbook:
- Pendentes por idade
- Taxa de confirmacao
- Expirados 24h

### Anti-loop keyword
Garantido por:
- Busca handoff por telefone do DIVULGADOR
- Medico nao tem handoff com seu proprio telefone

---

*Sprint criada em 29/12/2025*
