# E02: Intent Fingerprint + intent_log

**Status:** Pendente
**Estimativa:** 1 dia
**Dependências:** Nenhuma

---

## Objetivo

Criar dedupe semântico por **intenção de mensagem**, não apenas por conteúdo.

## Problema

```
Hoje (content_hash):
  Campanha A: "Oi, tudo bem? Vi seu perfil..."     → hash: abc123
  Campanha B: "Dr, tudo certo? Pintou uma vaga..." → hash: def456

  Textos diferentes → passa no dedupe → médico recebe 2 abordagens

Depois (intent_fingerprint):
  Campanha A: intent_type=discovery_first_touch → fingerprint: xyz789
  Campanha B: intent_type=discovery_first_touch → fingerprint: xyz789 (mesmo!)

  Mesma intenção → dedupe bloqueia → médico recebe só 1
```

## Tipos de Intent

| Intent Type | reference_id | Janela | Semântica |
|-------------|--------------|--------|-----------|
| `discovery_first_touch` | campaign_id | 7 dias | 1 discovery por campanha |
| `discovery_followup` | campaign_id | 3 dias | 1 followup por campanha |
| `offer_active` | vaga_id | 1 dia | 1 oferta por vaga |
| `offer_reminder` | vaga_id | 2 dias | 1 reminder por vaga |
| `reactivation_nudge` | None | 7 dias | 1 reativação global |
| `reactivation_value_prop` | None | 7 dias | 1 value prop global |
| `followup_silence` | conversation_id | 3 dias | 1 por conversa |
| `followup_pending_docs` | conversation_id | 2 dias | 1 por conversa |
| `shift_reminder` | vaga_id | 1 dia | 1 por plantão |
| `handoff_confirmation` | vaga_id | 1 dia | 1 por plantão |

## Checklist de Implementação

### Migração SQL

- [ ] Criar tabela `intent_log`:
  - [ ] `fingerprint TEXT PRIMARY KEY`
  - [ ] `cliente_id UUID NOT NULL REFERENCES clientes(id)`
  - [ ] `intent_type TEXT NOT NULL`
  - [ ] `reference_id UUID`
  - [ ] `created_at TIMESTAMPTZ DEFAULT NOW()`
  - [ ] `expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days'`

- [ ] Criar índices:
  - [ ] `idx_intent_log_cliente`
  - [ ] `idx_intent_log_expires`
  - [ ] `idx_intent_log_type`

- [ ] Criar RPC `inserir_intent_se_novo`:
  - [ ] Usar `ON CONFLICT DO NOTHING`
  - [ ] Retornar `(fingerprint, inserted BOOLEAN)`
  - [ ] Sem exceção para duplicata

### Python

- [ ] Criar `app/services/intent_dedupe.py`:
  - [ ] Enum `IntentType`
  - [ ] Dict `INTENT_WINDOWS` (intent → dias)
  - [ ] Dict `INTENT_REFERENCE_FIELD` (intent → campo)
  - [ ] Função `gerar_intent_fingerprint()`
  - [ ] Função `verificar_intent()` → `(pode_enviar, fingerprint, motivo)`
  - [ ] Função `obter_reference_id()`

### Testes

- [ ] `test_primeira_insercao_permite`
- [ ] `test_segunda_insercao_bloqueia`
- [ ] `test_janelas_diferentes_fingerprints_diferentes`
- [ ] `test_reference_id_diferente_fingerprint_diferente`
- [ ] `test_intent_type_diferente_permite`

### Integração

- [ ] Integrar em `send_outbound_message()` (feito em E03)
- [ ] Evento `OUTBOUND_DEDUPED` com `reason_code="intent_duplicate"`

### Cleanup

- [ ] Configurar job diário: `DELETE FROM intent_log WHERE expires_at < NOW()`
- [ ] Adicionar ao scheduler existente

## Arquivos a Criar/Modificar

| Arquivo | Ação |
|---------|------|
| `supabase/migrations/YYYYMMDD_intent_log.sql` | Criar |
| `app/services/intent_dedupe.py` | Criar |
| `tests/unit/test_intent_dedupe.py` | Criar |
| `app/workers/scheduler.py` | Modificar (cleanup job) |

## Definition of Done

- [ ] Migração aplicada em staging
- [ ] RPC `inserir_intent_se_novo` funcionando
- [ ] Serviço `intent_dedupe.py` completo
- [ ] Todos os testes passando
- [ ] Job de cleanup configurado
- [ ] Code review aprovado

## Notas de Implementação

### Cuidado: Enum vs String

```python
# INTENT_WINDOWS usa strings, não enum
INTENT_WINDOWS: dict[str, int] = {
    "discovery_first_touch": 7,  # String, não IntentType.DISCOVERY_FIRST
    ...
}

# Normalizar intent_type sempre
intent_str = str(intent_type)
window = INTENT_WINDOWS.get(intent_str, DEFAULT_WINDOW)
```

### Fingerprint determinístico

```python
def gerar_intent_fingerprint(...):
    # day_bucket garante janela temporal
    day_bucket = datetime.utcnow().toordinal() // window_days

    raw = f"{cliente_id}:{intent_type}:{reference_id or 'none'}:{day_bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
```

### RPC sem exceção

```sql
-- Retorna inserted=TRUE se inseriu, FALSE se já existia
INSERT INTO intent_log ...
ON CONFLICT (fingerprint) DO NOTHING;

GET DIAGNOSTICS v_inserted = ROW_COUNT;
RETURN QUERY SELECT p_fingerprint, v_inserted > 0;
```
