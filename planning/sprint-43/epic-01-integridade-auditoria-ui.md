# Epic 01 - Integridade & Auditoria UI

## Objetivo
Disponibilizar no dashboard visoes para auditoria de eventos, violacoes e anomalias, reduzindo dependencia de SQL manual.

## Stories

### S43.E1.1 - Pagina Integridade (Visao Geral)
**Objetivo:** Criar pagina com cards de auditoria, anomalias e KPI de integridade.

**Tarefas**
1. Criar rota `/integridade` no dashboard.
2. Exibir resumo de auditoria e violacoes.
3. Linkar para detalhes por anomalia.

**Como Testar**
- Acessar `/integridade` e validar cards.

**DoD**
- [ ] Pagina criada
- [ ] Dados carregados via API
- [ ] Estados de erro/empty

### S43.E1.2 - Lista de Anomalias + Filtros
**Objetivo:** Exibir anomalias com filtros por periodo, severidade e status.

**Tarefas**
1. Implementar tabela com filtros.
2. Link para detalhe da anomalia.

**DoD**
- [ ] Filtros funcionando
- [ ] Exportacao CSV simples

### S43.E1.3 - Auditoria de Eventos
**Objetivo:** Exibir execucao de auditoria e resultados por fonte.

**Tarefas**
1. Botao para executar auditoria.
2. Exibir resultado por fonte e violações.

