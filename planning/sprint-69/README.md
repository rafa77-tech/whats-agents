# Sprint 69 — Flows Dashboard CRUD + DDD Campanhas Phase 2

## Status: Concluida

**Inicio:** 2026-02-21
**PR:** [#158](https://github.com/revoluna/whatsapp-api/pull/158) — `feat: Sprint 69 — Flows dashboard CRUD + DDD campanhas phase 2`

## Objetivo

Expandir o modulo Meta no dashboard com CRUD completo de Flows (visualizacao detalhada, preview de telas, publicar/deprecar), aprimorar a exibicao de Templates com componentes tipados, e avancar a Phase 2 do DDD (ADR-007) migrando rotas de campanhas para a camada de Application Service.

---

## Diagnostico (pre-sprint)

| Metrica | Sprint 68 (Anterior) | Sprint 69 (Meta) |
|---------|----------------------|-------------------|
| Flows no dashboard | Listagem basica (nome, status) | CRUD completo + detail view + preview |
| Templates display | `body_text` + `header_format` | `TemplateComponent[]` tipado |
| Campanhas routes | SQL direto em rotas | Application Service (DDD boundary) |
| Tipos Flow | `MetaFlow` basico | `FlowDefinition`, `FlowScreen`, `FlowComponent` |

---

## Epicos

| # | Epico | Estimativa | Dependencias |
|---|-------|------------|--------------|
| 69.1 | Flows Dashboard CRUD | 25 pts | Nenhuma |
| 69.2 | Templates Enhancement | 8 pts | Nenhuma |
| 69.3 | DDD Campanhas Phase 2 (ADR-007) | 20 pts | Sprint 68 (context map) |

**Total estimado:** ~53 pontos

---

### Epic 69.1 — Flows Dashboard CRUD

Implementar visualizacao detalhada de Flows com preview de telas WhatsApp e acoes de publicar/deprecar.

**Tarefas:**

- [x] T1: Criar tipos `FlowDefinition`, `FlowScreen`, `FlowComponent`, `FlowComponentType` em `types/meta.ts`
- [x] T2: Criar API route `GET /api/dashboard/meta/flows` (listagem)
- [x] T3: Criar API route `GET /api/dashboard/meta/flows/[id]` (detalhe com JSON do flow)
- [x] T4: Criar API route `POST /api/dashboard/meta/flows/[id]/publish` (publicar flow)
- [x] T5: Criar API route `POST /api/dashboard/meta/flows/[id]/publish` com `action=deprecate` (deprecar)
- [x] T6: Criar componente `flow-screen-preview.tsx` (renderiza telas do flow)
- [x] T7: Criar componente `whatsapp-preview.tsx` (preview estilo WhatsApp)
- [x] T8: Expandir `flows-tab.tsx` com detail view (lista + detalhe lado a lado)
- [x] T9: Adicionar funcoes `getFlows`, `getFlow`, `publishFlow`, `deprecateFlow` em `lib/api/meta.ts`
- [x] T10: Testes para flows-tab (203 linhas adicionadas)

---

### Epic 69.2 — Templates Enhancement

Migrar exibicao de templates de campos simples (`body_text`, `header_format`) para array tipado de `TemplateComponent[]`.

**Tarefas:**

- [x] T1: Atualizar `templates-tab.tsx` para renderizar componentes (HEADER, BODY, FOOTER, BUTTONS)
- [x] T2: Ajustar API route `meta/templates/route.ts` para novo formato
- [x] T3: Atualizar testes de templates-tab

---

### Epic 69.3 — DDD Campanhas Phase 2 (ADR-007)

Remover SQL direto das rotas de campanhas e delegar para `CampanhasApplicationService`, conforme ADR-007 (sem SQL em rotas de dominio).

**Tarefas:**

- [x] T1: Criar `app/contexts/campanhas/application.py` (Application Service)
- [x] T2: Adicionar metodos de repositorio em `app/services/campanhas/repository.py` para integracao DDD
- [x] T3: Refatorar `app/api/routes/campanhas.py` (-195 linhas SQL, +62 linhas delegacao)
- [x] T4: Atualizar testes de campanhas para nova camada

---

## Arquivos Modificados/Criados

### Novos (8 arquivos)

```
dashboard/app/api/dashboard/meta/flows/route.ts              # API: listar flows
dashboard/app/api/dashboard/meta/flows/[id]/route.ts          # API: detalhe flow
dashboard/app/api/dashboard/meta/flows/[id]/publish/route.ts  # API: publicar/deprecar
dashboard/components/meta/flow-screen-preview.tsx              # Preview de telas do flow
dashboard/components/meta/whatsapp-preview.tsx                 # Preview estilo WhatsApp
app/contexts/campanhas/application.py                          # Application Service DDD (+341 linhas)
docs/arquitetura/ddd-context-map.md                            # Context map oficial
planning/backlog-consolidado.md                                # Backlog consolidado
```

### Modificados (10 arquivos)

```
dashboard/types/meta.ts                                        # +53 linhas (tipos Flow)
dashboard/lib/api/meta.ts                                      # +27 linhas (client functions)
dashboard/components/meta/tabs/flows-tab.tsx                   # +173/-29 (detail view)
dashboard/components/meta/tabs/templates-tab.tsx                # +63/-44 (component-based)
dashboard/app/api/dashboard/meta/templates/route.ts            # +1/-1
app/api/routes/campanhas.py                                    # +62/-195 (DDD refactor)
app/services/campanhas/repository.py                           # +59 (novos metodos)
dashboard/__tests__/components/meta/flows-tab.test.tsx         # +203/-10
dashboard/__tests__/components/meta/templates-tab.test.tsx     # +21/-18
dashboard/__tests__/components/meta/quality-tab.test.tsx       # +2/-2
```

### Testes

```
tests/api/routes/test_campanhas.py                             # +139/-147 (reescrito)
```

---

## Criterios de Aceite

- [x] Flows tab exibe lista de flows e detail view com preview de telas
- [x] Acoes de publicar e deprecar funcionam via API routes
- [x] Templates tab exibe componentes tipados (HEADER, BODY, FOOTER, BUTTONS)
- [x] Rotas de campanhas delegam para Application Service (zero SQL direto)
- [x] `CampanhasApplicationService` encapsula toda logica de negocio
- [x] Repository com metodos para integracao DDD
- [x] `npm run validate` passa no dashboard
- [x] Testes de campanhas passam com nova camada

---

## Riscos

| Risco | Impacto | Probabilidade | Mitigacao |
|-------|---------|---------------|-----------|
| Refatoracao de campanhas quebrar endpoints existentes | Alto | Media | Testes de regressao reescritos (+139 linhas) |
| Flows API retornar JSON inesperado | Medio | Baixa | Tipagem forte com FlowDefinition/FlowScreen |
| Preview de flow nao renderizar componentes complexos | Baixo | Media | Fallback para JSON raw |
| Application Service com logica incompleta | Medio | Baixa | Mapeamento 1:1 das rotas existentes |

---

## Dependencias

| Epico | Depende de | Status |
|-------|-----------|--------|
| 69.1 | Sprint 66-67 (Meta API base) | Concluido |
| 69.2 | Sprint 66 (templates base) | Concluido |
| 69.3 | Sprint 68 (ADR-007, context map) | Concluido |

---

## Metricas da Sprint

- `# linhas SQL removidas de rotas`: 195
- `# linhas Application Service`: 341
- `# novos componentes dashboard`: 2 (flow-screen-preview, whatsapp-preview)
- `# novas API routes`: 3 (flows list, detail, publish)
- `# testes adicionados/reescritos`: ~400 linhas de teste
- `% rotas campanhas via Application Service`: 100%

---

## Ordem de Execucao

1. **Fase 1 — Tipos e API (paralelo):**
   - Epic 69.1 T1-T5 (tipos + API routes de flows)
   - Epic 69.2 T1-T2 (templates enhancement)
   - Epic 69.3 T1-T2 (application service + repository)

2. **Fase 2 — Componentes e integracao:**
   - Epic 69.1 T6-T9 (componentes de preview + client functions)
   - Epic 69.3 T3 (refatorar rotas)

3. **Fase 3 — Testes e validacao:**
   - Epic 69.1 T10, Epic 69.2 T3, Epic 69.3 T4
   - `npm run validate` + `pytest`
