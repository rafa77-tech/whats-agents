# Epic 01 — Flows Dashboard CRUD

## Objetivo

Substituir o placeholder estatico da tab Flows por CRUD funcional conectado ao backend MetaFlowService.

## Estimativa: 20 pontos

## Tarefas

### T1: Tipos TypeScript (2 pts)

**Arquivo:** `dashboard/types/meta.ts`

Adicionar:
- `FlowComponent` — componente individual de um screen (TextInput, Dropdown, etc)
- `FlowScreen` — tela do flow com layout e children
- `FlowDefinition` — definicao completa JSON v7.0 com screens e routing
- Atualizar `MetaFlow` com campo opcional `json_definition`

### T2: API Client (3 pts)

**Arquivo:** `dashboard/lib/api/meta.ts`

Adicionar funcoes:
- `getFlows()` — lista todos os flows
- `getFlow(id)` — busca flow por ID
- `publishFlow(id)` — publica flow (DRAFT -> PUBLISHED)
- `deprecateFlow(id)` — depreca flow (PUBLISHED -> DEPRECATED)

### T3: API Routes Next.js (5 pts)

**Arquivos novos:**
- `dashboard/app/api/dashboard/meta/flows/route.ts` — GET list
- `dashboard/app/api/dashboard/meta/flows/[id]/route.ts` — GET detail, DELETE deprecate
- `dashboard/app/api/dashboard/meta/flows/[id]/publish/route.ts` — POST publish

Padrao: mesmo que templates/quality routes existentes (Supabase server client).

### T4: Componente FlowsTab (5 pts)

**Arquivo:** `dashboard/components/meta/tabs/flows-tab.tsx`

Reescrever com:
- Fetch de flows reais via `metaApi.getFlows()`
- Cards com nome, tipo, status badge, data de criacao
- Contagem de respostas
- Botoes de acao: Publish (para DRAFT), Deprecate (para PUBLISHED)
- Toast de feedback para acoes
- Loading state e empty state

### T5: Componente FlowScreenPreview (3 pts)

**Arquivo novo:** `dashboard/components/meta/flow-screen-preview.tsx`

Preview visual dos screens de um flow:
- Renderiza componentes (TextInput, Dropdown, RadioButtons, CheckboxGroup)
- Mostra titulo da screen
- Navegacao entre screens se houver mais de uma

### T6: Testes (2 pts)

**Arquivo:** `dashboard/__tests__/components/meta/flows-tab.test.tsx`

Atualizar testes para:
- Mock da API `metaApi.getFlows`
- Renderizacao de flows com diferentes status
- Loading e empty states
- Acoes de publish/deprecate

## Criterios de Aceite

- [ ] Tab Flows carrega dados reais (sem placeholder)
- [ ] Status badges DRAFT/PUBLISHED/DEPRECATED com cores corretas
- [ ] Publish e Deprecate funcionam com toast de confirmacao
- [ ] Preview de screens renderiza componentes corretamente
- [ ] Testes unitarios passando
- [ ] `npm run validate` sem erros

## Dependencias Tecnicas

- Backend: `MetaFlowService` (app/services/meta/flow_service.py) ✅
- Backend: rotas FastAPI `/meta/flows/*` ✅
- Banco: tabelas `meta_flows`, `meta_flow_responses` ✅
- Dashboard: Supabase server client ✅
