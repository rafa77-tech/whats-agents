# Sprint 60 — Qualidade de Dados de Hospitais

## Status: 📋 Planejada

**Inicio:** Pendente
**Estimativa:** 4 semanas

## Objetivo

Eliminar degradacao critica na qualidade de dados de hospitais: 2.703 registros com 68% de duplicatas, lixo de scraping, race conditions na criacao, e dropdown inutilizavel no dashboard.

**Origem:** Analise de qualidade de dados realizada em 2026-02-16.

---

## Diagnostico

| Metrica | Valor Atual |
|---------|-------------|
| Total de registros | 2.703 |
| Nomes unicos | 851 (apenas 31%) |
| Criados automaticamente | 2.618 (97%) |
| Pendentes de revisao | 2.614 (97%) |
| Taxa de duplicacao | ~68% |
| Lixo de scraping | ~200+ registros |

**Causas raiz:**
1. Sem constraint `UNIQUE` em `hospitais.nome` ou `hospitais_alias.alias_normalizado`
2. Race condition: workers paralelos criam o mesmo hospital em milissegundos
3. Scraping salva lixo como hospital: nomes de contatos, empresas, especialidades, fragmentos
4. Dropdown carrega todos os 2.703 registros sem filtro
5. Duplicatas semanticas: "Hospital Tide Setubal" vs "Pronto Socorro Hospital Municipal Tide Setubal"

**Tabelas com FK para `hospitais`:**

| Tabela | Coluna | ON DELETE | Impacto no Merge |
|--------|--------|-----------|------------------|
| `vagas` | hospital_id | NO ACTION | UPDATE obrigatorio |
| `vagas_grupo` | hospital_id | NO ACTION | UPDATE obrigatorio |
| `business_events` | hospital_id | SET NULL | UPDATE recomendado |
| `business_alerts` | hospital_id | SET NULL | UPDATE recomendado |
| `hospitais_alias` | hospital_id | CASCADE | Migra aliases |
| `grupos_whatsapp` | hospital_id | NO ACTION | UPDATE obrigatorio |
| `conhecimento_hospitais` | hospital_id | NO ACTION | UPDATE obrigatorio |
| `diretrizes_contextuais` | hospital_id | NO ACTION | UPDATE obrigatorio |
| `hospitais_bloqueados` | hospital_id | NO ACTION | UPDATE obrigatorio |

---

## Epicos

| # | Epico | Prioridade | Risco | Depende de |
|---|-------|------------|-------|------------|
| 1 | [Gate de Validacao de Nomes](epic-01-validacao-nomes.md) | P0 | Baixo | - |
| 2 | [Race Condition com Lock Atomico](epic-02-race-condition.md) | P0 | Medio | Epico 1 |
| 3 | [Limpeza de Dados Existentes](epic-03-limpeza-dados.md) | P1 | Alto | Epicos 1, 2 |
| 4 | [Fix do Dropdown do Dashboard](epic-04-dropdown-fix.md) | P1 | Baixo | - (paralelo) |
| 5 | [Pagina de Gestao de Hospitais](epic-05-gestao-dashboard.md) | P2 | Medio | Epico 3 |
| 6 | [Monitoramento e Melhorias](epic-06-monitoramento.md) | P2 | Baixo-Medio | Epicos 1-3 |

---

## Criterios de Sucesso

- [ ] Zero registros lixo novos criados por semana
- [ ] Taxa de duplicacao < 5% (de 68%)
- [ ] Total de hospitais reduzido para ~600-700 (de 2.703)
- [ ] Dropdown com busca server-side, max 50 resultados
- [ ] Funcao de merge atomica com auditoria
- [ ] Pagina de gestao de hospitais no dashboard
- [ ] UNIQUE constraint em `hospitais_alias.alias_normalizado`
- [ ] `uv run pytest` limpo apos cada epico
- [ ] `cd dashboard && npm run validate` limpo apos epicos 4 e 5

---

## Riscos

| Risco | Impacto | Probabilidade | Mitigacao |
|-------|---------|---------------|-----------|
| Falsos positivos no validador rejeitam hospitais reais | Medio | Media | Hospital fica com hospital_id=NULL, nao perde dado |
| Advisory locks adicionam latencia | Baixo | Baixa | Lock por alias, escopo estreito (~ms) |
| Merge de hospitais quebra integridade | Alto | Baixa | Funcao atomica, tabela de auditoria, dry-run obrigatorio |
| Cleanup deleta hospital referenciado | Alto | Baixa | Tier 1 so deleta com ZERO FKs, transacao atomica |
| UNIQUE constraint falha por conflitos existentes | Medio | Media | Cleanup do Epico 3 resolve conflitos antes |

---

## Ordem de Execucao

```
Semana 1:  Epico 1 (Validacao) + Epico 4 (Dropdown) — em paralelo
               |
Semana 2:  Epico 2 (Race Condition) + Epico 3A (Funcao Merge)
               |
Semana 3:  Epico 3B+C (Limpeza) + Epico 5 (Dashboard Gestao)
               |
Semana 4:  Epico 6 (Monitoramento + Melhorias)
```

---

## Impacto Esperado

| Metrica | Antes | Depois |
|---------|-------|--------|
| Total de hospitais | 2.703 | ~600-700 |
| Taxa de duplicacao | 68% | < 5% |
| Pendentes de revisao | 2.614 | ~100 (legacy) |
| Registros lixo | ~200+ | 0 |
| Novo lixo/semana | ~10-20 | 0 |
| Dropdown | 2.703 itens (lento) | Busca server-side, top 50 |
| Capacidade de merge | Nenhuma | Completa (dashboard + API) |

---

## Verificacao

### Apos cada epico
```bash
uv run pytest --no-cov                                       # Todos os testes
```

### Apos Epico 3 (Limpeza)
```sql
SELECT COUNT(*), COUNT(DISTINCT nome) FROM hospitais;
-- Verificar que nenhuma vaga aponta para hospital deletado
SELECT COUNT(*) FROM vagas v
LEFT JOIN hospitais h ON v.hospital_id = h.id
WHERE v.hospital_id IS NOT NULL AND h.id IS NULL;
-- Verificar tabela de auditoria
SELECT COUNT(*) FROM hospital_merges;
```

### Apos Epicos 4 e 5 (Dashboard)
```bash
cd dashboard && npm run validate    # typecheck + lint + format + tests
cd dashboard && npm run build       # Build final
```

---

## Rollback

| Epico | Estrategia |
|-------|-----------|
| 1 (Validacao) | Remover gate no hospital_web.py — hospitais voltam a ser criados sem filtro |
| 2 (Lock) | Reverter para INSERT direto — race condition volta, mas funcional |
| 3 (Limpeza) | Tabela `hospital_merges` permite rastrear e reverter merges |
| 4 (Dropdown) | Reverter para load-all — funcional, so lento |
| 5 (Dashboard) | Paginas novas, remover sem impacto |
| 6 (Monitoramento) | Aditivo, remover sem impacto. UNIQUE index: DROP INDEX |
