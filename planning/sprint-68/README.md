# Sprint 68 — DDD Foundation (ADRs 006-008)

## Status: Planejada

**Inicio previsto:** 2026-02-24  
**Duracao:** 10 dias uteis (2 semanas)  
**Premissa de capacidade:** 3 devs (backend), ~60-75 pontos totais

## Objetivo

Executar a base arquitetural DDD definida nas ADRs 006, 007 e 008 para reduzir acoplamento entre interface e dominio, formalizar fronteiras de contexto e padronizar linguagem/estados canonicos.

## ADRs da Sprint

| Prioridade | ADR | Tema |
|------------|-----|------|
| P1 | 006 | Formalizar bounded contexts |
| P2 | 007 | Sem SQL direto em rotas de dominio |
| P3 | 008 | Linguagem ubiqua e estados canonicos |

## Epicos

| # | Epico | ADR | Estimativa | Dependencias |
|---|-------|-----|------------|--------------|
| 01 | Context Map e Ownership de Contextos | 006 | 18 pts | Nenhuma |
| 02 | Boundary Enforcement API -> Application -> Repository | 007 | 32 pts | Epic 01 |
| 03 | Ubiquitous Language e Canonical States | 008 | 20 pts | Epic 01 |

## Criterios de Sucesso

- [ ] Context map oficial publicado com owners e contratos por contexto
- [ ] Zero novos usos de `supabase.table(...)` em rotas de dominio
- [ ] Pelo menos 3 rotas criticas migradas para application service
- [ ] Dicionario de linguagem ubiqua publicado e aprovado por Engenharia + Produto
- [ ] Catalogo de estados canonicos publicado com aliases legados
- [ ] Suite de testes adicionada para os novos boundaries e mapeamentos
- [ ] ADR-006/007/008 atualizadas de `Proposta` para `Aceita` (se validado no fechamento)

## Riscos

| Risco | Impacto | Probabilidade | Mitigacao |
|-------|---------|---------------|-----------|
| Refatoracao quebrar endpoints de producao | Alto | Media | Migracao incremental por rota + testes de regressao |
| Divergencia negocio vs engenharia na linguagem | Medio | Alta | Workshop rapido de termos + decisor unico por contexto |
| Escopo excessivo de migracao de SQL legado | Alto | Media | Limite de escopo: 3 rotas criticas na sprint |
| Aumento de lead time por nova camada | Medio | Baixa | Templates de application service e checklist padrao |

## Dependencias

| Epico | Depende de | Status |
|-------|-----------|--------|
| 01 | ADRs 006-008 publicadas | ✅ |
| 02 | Context map/ownership definido no Epic 01 | Pendente |
| 03 | Context map/ownership definido no Epic 01 | Pendente |

## Metricas da Sprint

- `% rotas de dominio sem SQL direto`
- `# usos de supabase.table em app/api/routes (baseline vs final)`
- `# casos de teste de boundary adicionados`
- `# termos/estados canonicamente definidos`
- `tempo medio de PR em modulos refatorados` (monitorar regressao de produtividade)

## Ordem de Execucao

1. Epic 01 (fundacao estrategica)
2. Epic 02 e Epic 03 em paralelo apos contratos/ownership definidos
3. Hardening final: lint, testes, docs, aceite das ADRs

