# Sprint 61 — Enriquecimento de Hospitais: CNES + Google Places

## Status: 📋 Planejada

**Inicio:** Pendente
**Estimativa:** 1 semana

## Objetivo

Integrar dados reais de hospitais (CNES + Google Places API) no pipeline de criacao automatica e enriquecer os 523 hospitais existentes com endereco, coordenadas, telefone e codigo CNES.

**Origem:** Analise pos-limpeza Sprint 60 — hospitais criados sem dados completos, pipeline dependendo apenas de conhecimento estatico do LLM.

---

## Diagnostico

| Metrica | Valor Atual |
|---------|-------------|
| Hospitais no banco | 523 |
| Com endereco completo | ~50 (estimado) |
| Com coordenadas (lat/lng) | 0 |
| Com codigo CNES | 0 |
| Com telefone | 0 |
| Fonte de dados no pipeline | Apenas Claude Haiku (conhecimento estatico) |
| Taxa de fallback na criacao | ~40% dos novos hospitais |

**Causas raiz:**
1. Pipeline `normalizar_ou_criar_hospital()` nao consulta nenhuma base de dados real
2. `buscar_hospital_web()` usa LLM sem acesso a internet — depende de training data
3. Nao existe tabela CNES no banco para lookup local
4. Google Places API nao esta integrado
5. Colunas de enriquecimento (`cnes_codigo`, `google_place_id`, `telefone`) nao existem na tabela `hospitais`

---

## Epicos

| # | Epico | Prioridade | Risco | Depende de |
|---|-------|------------|-------|------------|
| 1 | [Infraestrutura CNES](epic-01-infraestrutura-cnes.md) | P0 | Medio | - |
| 2 | [Google Places API](epic-02-google-places.md) | P1 | Baixo | - |
| 3 | [Integracao no Pipeline](epic-03-integracao-pipeline.md) | P0 | Medio | Epicos 1, 2 |
| 4 | [Enriquecimento Batch](epic-04-enriquecimento-batch.md) | P1 | Baixo | Epicos 1, 2, 3 |

---

## Criterios de Sucesso

- [ ] Tabela `cnes_estabelecimentos` populada com estabelecimentos de saude relevantes de SP
- [ ] RPC `buscar_cnes_por_nome` retorna matches corretos para hospitais conhecidos
- [ ] Google Places Text Search retorna dados para hospitais brasileiros
- [ ] Pipeline `normalizar_ou_criar_hospital()` tenta CNES -> Google -> LLM -> fallback
- [ ] >= 70% dos 523 hospitais enriquecidos com dados CNES ou Google
- [ ] Zero vagas orfas apos enriquecimento
- [ ] Testes existentes continuam passando

---

## Riscos

| Risco | Impacto | Probabilidade | Mitigacao |
|-------|---------|---------------|-----------|
| Dados CNES nao cobrem hospitais pequenos/privados | Medio | Media | Google Places como fallback |
| Google Places API key nao configurada | Medio | Baixa | Fallback gracioso — pula etapa silenciosamente |
| Custo Google Places excede budget | Baixo | Baixa | CNES primeiro (gratis), Google so para fallback |
| pg_trgm similarity baixa para nomes informais | Medio | Media | Threshold 0.4 + busca sem filtro de cidade como fallback |
| Rate limit Google Places | Baixo | Baixa | Sleep 0.5s entre requests no batch |

---

## Ordem de Execucao

```
Fase 1:  Epico 1 (CNES infra + import) + Epico 2 (Google Places) — em paralelo
             |
Fase 2:  Epico 3 (Integracao Pipeline) — depende de 1 e 2
             |
Fase 3:  Epico 4 (Enriquecimento Batch) — depende de 1, 2, 3
```

---

## Impacto Esperado

| Metrica | Antes | Depois |
|---------|-------|--------|
| Hospitais com CNES vinculado | 0 | ~350+ |
| Hospitais com endereco completo | ~50 | ~450+ |
| Hospitais com coordenadas | 0 | ~400+ |
| Taxa de fallback pipeline | ~40% | < 10% |
| Fonte primaria novos hospitais | LLM estatico | CNES + Google |

---

## Verificacao

### Apos Epico 1 (CNES)
```sql
SELECT COUNT(*) FROM cnes_estabelecimentos;
SELECT COUNT(*) FROM cnes_estabelecimentos WHERE uf = 'SP';
SELECT * FROM buscar_cnes_por_nome('Hospital Sao Luiz', NULL, 'SP', 5);
```

### Apos Epico 2 (Google Places)
```bash
uv run pytest tests/grupos/test_hospital_google_places.py
```

### Apos Epico 3 (Pipeline)
```bash
uv run pytest tests/grupos/ --no-cov
```

### Apos Epico 4 (Enriquecimento)
```sql
SELECT COUNT(*) FROM hospitais WHERE cnes_codigo IS NOT NULL;
SELECT COUNT(*) FROM hospitais WHERE google_place_id IS NOT NULL;
SELECT COUNT(*) FROM hospitais WHERE enriched_at IS NOT NULL;
-- Integridade
SELECT COUNT(*) FROM vagas v
  LEFT JOIN hospitais h ON h.id = v.hospital_id
  WHERE v.hospital_id IS NOT NULL AND h.id IS NULL;
```

---

## Rollback

| Epico | Estrategia |
|-------|-----------|
| 1 (CNES) | `DROP TABLE cnes_estabelecimentos;` + remover colunas adicionadas |
| 2 (Google Places) | Remover arquivo, nao afeta dados existentes |
| 3 (Pipeline) | Reverter `hospital_web.py` — fluxo anterior continua funcional |
| 4 (Batch) | Dados enriquecidos sao aditivos — nao quebram nada se revertidos |
