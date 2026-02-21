# Sprint 69 — WhatsApp Flows Dashboard + Backlog Consolidado

## Status: Em Progresso

**Inicio previsto:** 2026-02-21
**Duracao:** 5 dias uteis (1 semana)
**Premissa de capacidade:** 1 dev (fullstack), ~25-30 pontos totais

## Objetivo

Implementar CRUD funcional de WhatsApp Flows no dashboard Meta e consolidar todos os itens de trabalho futuro do codebase em documento unico de backlog.

## Contexto

O backend de flows esta completo (Sprint 68): `MetaFlowService` (CRUD), `FlowBuilder` (3 flows pre-definidos), rotas FastAPI (6 endpoints), tabelas `meta_flows` + `meta_flow_responses`. A tab Flows na pagina `/meta` e um placeholder estatico com badge "Em breve". Esta sprint conecta o dashboard ao backend.

## Epicos

| # | Epico | Estimativa | Dependencias |
|---|-------|------------|--------------|
| 01 | Flows Dashboard CRUD | 20 pts | Backend completo (Sprint 68) |
| 02 | Backlog Consolidado | 8 pts | Nenhuma |

## Criterios de Sucesso

- [ ] Tab Flows exibe lista de flows reais do banco (sem placeholder)
- [ ] Status badges (DRAFT, PUBLISHED, DEPRECATED) com cores corretas
- [ ] Acoes de Publish e Deprecate funcionais com feedback via toast
- [ ] Preview de screens do flow com componentes renderizados
- [ ] Contagem de respostas visivel por flow
- [ ] API routes Next.js criadas (GET list, GET detail, POST publish, DELETE deprecate)
- [ ] Tipos TypeScript atualizados com FlowScreen/FlowComponent/FlowDefinition
- [ ] Testes unitarios atualizados e passando
- [ ] `npm run validate` e `npm run build` passando
- [ ] Documento de backlog consolidado com 65+ itens categorizados
- [ ] Seed dos 3 flows pre-definidos no banco via migration

## Riscos

| Risco | Impacto | Probabilidade | Mitigacao |
|-------|---------|---------------|-----------|
| Tabela meta_flows vazia em producao | Medio | Alta | Seed migration com 3 flows padrao |
| Flow JSON definition grande demais para preview | Baixo | Media | Renderizar apenas primeiro screen |
| Backlog items dispersos e dificeis de encontrar | Baixo | Media | Busca sistematica por TODO/FIXME/placeholder |

## Dependencias

| Epico | Depende de | Status |
|-------|-----------|--------|
| 01 | Backend MetaFlowService (Sprint 68) | ✅ |
| 01 | Tabelas meta_flows/meta_flow_responses | ✅ |
| 02 | Nenhuma | - |

## Metricas da Sprint

- `# flows visiveis no dashboard`
- `# acoes CRUD funcionais`
- `# itens de backlog catalogados`
- `cobertura de testes do modulo flows`

## Ordem de Execucao

1. Documentacao (README + epics + backlog)
2. Types + API client
3. API routes Next.js
4. Componente FlowsTab
5. Componente FlowScreenPreview
6. Testes
7. Seed migration
8. Validacao final
