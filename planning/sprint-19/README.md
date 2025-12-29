# Sprint 19: Valor Flexivel em Vagas

## Objetivo

Implementar suporte completo para valores flexiveis em vagas (fixo, a combinar, faixa), desde a extracao ate a comunicacao pela Julia.

## Problema que Resolve

Atualmente o campo `valor` e um `integer`, mas muitas ofertas de plantao tem valores negociaveis ("A combinar", "Entre 1.500 e 2.000"). Isso causa:

1. **Erro de banco**: LLM retorna string, banco espera integer
2. **Perda de informacao**: Vagas com "A combinar" ficam sem valor
3. **Comunicacao imprecisa**: Julia nao consegue informar corretamente ao medico

## Contexto

| Aspecto | Valor Atual | Problema |
|---------|-------------|----------|
| Campo valor | `integer` nullable | Nao suporta "A combinar" |
| Vagas sem valor | 185 (33%) | Informacao perdida |
| Erro na pipeline | 1 item travado | Bug de parsing |
| Template Julia | Unico | Nao diferencia tipos |

## Solucao

### Modelo de Dados

```sql
-- Novos campos em vagas_grupo e vagas
valor          INTEGER    -- Valor exato (quando fixo)
valor_minimo   INTEGER    -- Faixa minima (opcional)
valor_maximo   INTEGER    -- Faixa maxima (opcional)
valor_tipo     TEXT       -- 'fixo', 'a_combinar', 'faixa'
```

### Cenarios Suportados

| Mensagem Original | valor | valor_minimo | valor_maximo | valor_tipo |
|-------------------|-------|--------------|--------------|------------|
| "R$ 1.800 PJ" | 1800 | null | null | `fixo` |
| "A combinar" | null | null | null | `a_combinar` |
| "Entre 1.500 e 2.000" | null | 1500 | 2000 | `faixa` |
| "A partir de 1.500" | null | 1500 | null | `faixa` |
| "Ate 2.000" | null | null | 2000 | `faixa` |

## Epicos

| # | Epico | Descricao | Arquivos |
|---|-------|-----------|----------|
| E01 | [Migracao de Schema](./epic-01-migracao-schema.md) | Adicionar colunas, migrar dados | 2 migracoes |
| E02 | [Atualizacao Extracao LLM](./epic-02-extracao-llm.md) | Prompt, parsing, validacao | 3 arquivos |
| E03 | [Atualizacao Pipeline](./epic-03-pipeline.md) | Normalizacao, importacao | 4 arquivos |
| E04 | [Adaptacao Julia](./epic-04-julia-oferta.md) | Templates de oferta | 3 arquivos |
| E05 | [Atualizacao Slack Tools](./epic-05-slack-tools.md) | Exibicao e filtros | 2 arquivos |
| E06 | [Testes e Documentacao](./epic-06-testes-docs.md) | Cobertura completa | 6+ arquivos |

## Dependencias

```
E01 (Schema)
    └─► E02 (Extracao)
            └─► E03 (Pipeline)
                    ├─► E04 (Julia)
                    └─► E05 (Slack)
                            └─► E06 (Testes)
```

## Metricas de Sucesso

| Metrica | Antes | Depois |
|---------|-------|--------|
| Vagas com valor perdido | 33% | < 5% |
| Erros de parsing valor | 1+ | 0 |
| Tipos de valor suportados | 1 | 3 |
| Templates Julia para valor | 1 | 3 |

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Migracao quebrar dados | Baixa | Alto | Backup + migracao em etapas |
| LLM nao entender novo prompt | Media | Medio | Few-shot examples + testes |
| Regressao em vagas fixas | Baixa | Alto | Testes de regressao |

## Estimativa

| Epico | Complexidade | Estimativa |
|-------|--------------|------------|
| E01 | Baixa | 2h |
| E02 | Media | 4h |
| E03 | Media | 3h |
| E04 | Media | 3h |
| E05 | Baixa | 2h |
| E06 | Media | 4h |
| **Total** | | **~18h** |

---

*Sprint criada em 29/12/2025*
