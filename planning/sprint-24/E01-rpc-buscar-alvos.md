# E01: RPC buscar_alvos_campanha

**Status:** Pendente
**Estimativa:** 1 dia
**Dependências:** Nenhuma

---

## Objetivo

Criar função no banco que retorna médicos **já filtrados por elegibilidade operacional**, não apenas demográfica.

## Problema

```
Hoje:
  segmentacao.buscar_segmento() → SELECT * FROM clientes
                                → Filtros simples
                                → Retorna 10k "na ordem do banco"
                                → Guardrails bloqueiam 30-50%
                                → Métricas desonestas

Depois:
  buscar_alvos_campanha() → JOIN com doctor_state
                          → Já exclui inelegíveis
                          → Ordem determinística
                          → 95%+ sendable
                          → Funil honesto
```

## Checklist de Implementação

### Migração SQL

- [ ] Criar função `buscar_alvos_campanha` com parâmetros:
  - [ ] `p_filtros JSONB` - filtros demográficos
  - [ ] `p_dias_sem_contato INT DEFAULT 14`
  - [ ] `p_excluir_cooling BOOLEAN DEFAULT TRUE`
  - [ ] `p_excluir_em_atendimento BOOLEAN DEFAULT TRUE`
  - [ ] `p_contact_cap INT DEFAULT 5`
  - [ ] `p_limite INT DEFAULT 1000`

- [ ] Implementar filtros operacionais:
  - [ ] `COALESCE(ds.contact_count_7d, 0) < p_contact_cap`
  - [ ] `ds.last_outbound_at < NOW() - interval`
  - [ ] `ds.next_allowed_at IS NULL OR < NOW()`
  - [ ] `NOT EXISTS (conversations.controlled_by = 'human')`
  - [ ] `ds.last_inbound_at IS NULL OR < NOW() - 30min`

- [ ] Determinismo:
  - [ ] `ORDER BY ds.last_outbound_at ASC NULLS FIRST, c.id ASC`

### Python

- [ ] Criar `buscar_alvos_campanha()` em `app/services/segmentacao.py`
- [ ] Chamar via `supabase.rpc()`
- [ ] Retornar lista tipada

### Testes

- [ ] `test_medico_sem_doctor_state_incluido`
- [ ] `test_medico_contact_cap_excedido_excluido`
- [ ] `test_medico_conversa_humana_excluido`
- [ ] `test_medico_inbound_recente_excluido`
- [ ] `test_ordem_deterministica`
- [ ] `test_filtros_demograficos_funcionam`

### Integração

- [ ] Atualizar rotas de campanha para usar nova função
- [ ] Adicionar log: "target set qualificado: X elegíveis de Y total"

## Arquivos a Criar/Modificar

| Arquivo | Ação |
|---------|------|
| `supabase/migrations/YYYYMMDD_buscar_alvos_campanha.sql` | Criar |
| `app/services/segmentacao.py` | Modificar |
| `tests/unit/test_segmentacao_qualificada.py` | Criar |
| `app/api/routes/campanhas.py` | Modificar |

## Definition of Done

- [ ] Migração aplicada em staging
- [ ] Todos os testes passando
- [ ] Rotas de campanha usando nova função
- [ ] Log de target set qualificado visível
- [ ] Code review aprovado

## Notas de Implementação

### Bug a evitar: JOIN duplicando linhas

Usar `NOT EXISTS` ao invés de `LEFT JOIN` para conversas:

```sql
-- ERRADO: pode duplicar se médico tem múltiplas conversas
LEFT JOIN conversations cv ON cv.cliente_id = c.id

-- CERTO: verifica existência sem duplicar
AND NOT EXISTS (
    SELECT 1 FROM conversations cv
    WHERE cv.cliente_id = c.id
      AND cv.status = 'active'
      AND cv.controlled_by = 'human'
)
```

### Performance

- Adicionar `EXPLAIN ANALYZE` em staging com volume real
- Considerar índice parcial se necessário:
  ```sql
  CREATE INDEX idx_doctor_state_elegivel
  ON doctor_state(last_outbound_at)
  WHERE contact_count_7d < 5
    AND (next_allowed_at IS NULL OR next_allowed_at < NOW());
  ```
