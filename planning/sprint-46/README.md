# Sprint 46: Market Intelligence - Fundacao

## Objetivo

Criar a base de dados, APIs e componentes visuais para o modulo de Market Intelligence, permitindo visualizacao de KPIs e metricas de volume do pipeline de grupos WhatsApp.

## Regras da Sprint

### Criterios de Qualidade

| Criterio | Requisito |
|----------|-----------|
| Cobertura de Testes | >= 80% por epico |
| Testes Unitarios | Obrigatorio para toda funcao/hook |
| Testes de Integracao | Obrigatorio para toda API |
| Testes E2E | Obrigatorio para todo fluxo de usuario |
| Type Safety | Zero `any`, 100% tipado |
| Linting | Zero warnings |
| Build | Deve passar sem erros |

### Fluxo de Trabalho

```
1. Ler o Epico completo
2. Implementar codigo
3. Escrever testes
4. Verificar cobertura >= 80%
5. Rodar todos os testes
6. Se TODOS passarem → proximo epico
7. Se algum falhar → corrigir antes de prosseguir
```

### Comandos de Verificacao

```bash
# Rodar testes do epico
npm run test -- --coverage --collectCoverageFrom='<path>'

# Verificar cobertura
npm run test:coverage

# Lint
npm run lint

# Type check
npm run type-check

# Build
npm run build
```

---

## Epicos

| ID | Nome | Dependencias | Estimativa |
|----|------|--------------|------------|
| E46.1 | Schema de Banco | - | 2h |
| E46.2 | Tipos TypeScript | E46.1 | 1h |
| E46.3 | API Overview | E46.1, E46.2 | 3h |
| E46.4 | API Volume | E46.1, E46.2 | 3h |
| E46.5 | API Pipeline | E46.1, E46.2 | 3h |
| E46.6 | Hook useMarketIntelligence | E46.3, E46.4, E46.5 | 2h |
| E46.7 | Componente KPICard | E46.2 | 2h |
| E46.8 | Componente VolumeChart | E46.2 | 3h |
| E46.9 | Componente PipelineFunnel | E46.2 | 3h |
| E46.10 | Componente GroupsRanking | E46.2 | 2h |
| E46.11 | Page Analytics Tab | E46.6-E46.10 | 3h |
| E46.12 | Testes E2E | E46.11 | 2h |

**Total Estimado:** 29h (~4 dias)

---

## Detalhamento dos Epicos

Ver arquivos individuais:
- [E46.1 - Schema de Banco](./E46.1-schema-banco.md)
- [E46.2 - Tipos TypeScript](./E46.2-tipos-typescript.md)
- [E46.3 - API Overview](./E46.3-api-overview.md)
- [E46.4 - API Volume](./E46.4-api-volume.md)
- [E46.5 - API Pipeline](./E46.5-api-pipeline.md)
- [E46.6 - Hook useMarketIntelligence](./E46.6-hook-market-intelligence.md)
- [E46.7 - Componente KPICard](./E46.7-componente-kpi-card.md)
- [E46.8 - Componente VolumeChart](./E46.8-componente-volume-chart.md)
- [E46.9 - Componente PipelineFunnel](./E46.9-componente-pipeline-funnel.md)
- [E46.10 - Componente GroupsRanking](./E46.10-componente-groups-ranking.md)
- [E46.11 - Page Analytics Tab](./E46.11-page-analytics-tab.md)
- [E46.12 - Testes E2E](./E46.12-testes-e2e.md)
