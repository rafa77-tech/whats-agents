# Migracao de Status 'fechada' para 'realizada'

## Contexto

O status 'fechada' era usado ambiguamente para "medico aceitou".
Na Sprint 17 introduzimos 'realizada' para "plantao executado".

## Estado Atual (Sprint 17)

- 'fechada' nao e mais gerado automaticamente
- Registros antigos permanecem como 'fechada'
- 'fechada' esta excluido do funil de metricas
- Funcao `marcar_vaga_realizada()` aceita tanto 'reservada' quanto 'fechada'

### Dados de Referencia

```sql
-- Verificar quantos registros tem 'fechada' (executar antes de migrar)
SELECT COUNT(*) as total_fechada FROM vagas WHERE status = 'fechada';

-- Distribuicao atual de status
SELECT status, COUNT(*) FROM vagas GROUP BY status ORDER BY COUNT(*) DESC;
```

Data de snapshot: 2024-12-27
Total 'fechada' no snapshot: 0 (nenhum registro legado)

## Criterios para Migracao

So migrar quando:

1. Sistema de business_events estiver 100% rollout
2. Funil estiver estabilizado por 2+ semanas
3. Tiver forma de validar (ex: dados financeiros, escala confirmada)
4. Nao houver processos dependentes do status 'fechada'

## Estrategia de Migracao

### Opcao A: Com Evidencia (Pagamento Confirmado)

```sql
-- Vagas 'fechada' com pagamento confirmado → 'realizada'
UPDATE vagas v
SET status = 'realizada',
    realizada_em = COALESCE(v.updated_at, v.data),
    realizada_por = 'migration_batch'
FROM pagamentos p
WHERE p.vaga_id = v.id
  AND p.status = 'pago'
  AND v.status = 'fechada';
```

### Opcao B: Com Evidencia (Data Passada)

```sql
-- Vagas 'fechada' com data de plantao ja passada → 'realizada'
UPDATE vagas
SET status = 'realizada',
    realizada_em = data + interval '12 hours',  -- assume meio do dia
    realizada_por = 'migration_batch'
WHERE status = 'fechada'
  AND data < CURRENT_DATE - interval '1 day';
```

### Opcao C: Sem Evidencia (Manter)

```sql
-- Opcao: Manter como 'fechada' (fora do funil)
-- Nada a fazer, apenas documentar

-- Ou renomear para distinguir:
-- UPDATE vagas SET status = 'fechada_legacy' WHERE status = 'fechada';
```

## Checklist Pre-Migracao

- [ ] Backup completo da tabela vagas
- [ ] Contagem de registros 'fechada': ___
- [ ] Funil business_events estavel por 2+ semanas
- [ ] Validacao de dados com financeiro/operacoes
- [ ] Comunicacao com stakeholders

## Metricas de Acompanhamento

Antes de migrar, verificar:

| Metrica | Valor |
|---------|-------|
| Total de vagas 'fechada' | |
| Com pagamento associado | |
| Sem pagamento | |
| Data > 30 dias | |
| Data recente | |

## Plano de Rollback

Se algo der errado apos migracao:

```sql
-- Reverter migracao (requer log de quais foram migradas)
UPDATE vagas
SET status = 'fechada',
    realizada_em = NULL,
    realizada_por = NULL
WHERE realizada_por = 'migration_batch';
```

## Historico de Decisoes

| Data | Decisao | Motivo |
|------|---------|--------|
| 2024-12-27 | Congelar 'fechada', nao migrar | Risco de quebrar codigo legado |
| 2024-12-27 | Adicionar 'realizada' | Necessario para funil de business events |
| TBD | Migrar registros | Quando criterios forem atendidos |

---

**Documento criado em:** Sprint 17 - E01.4
**Responsavel:** Equipe de Desenvolvimento
**Revisao prevista:** Apos 2 semanas de funil estavel
