# EPICO 5: Pagina de Gestao de Hospitais no Dashboard

## Contexto

Atualmente o dashboard tem hospitais apenas como campo de selecao em vagas e na funcionalidade de bloqueio. Nao existe pagina dedicada para gerenciar hospitais — revisar, editar, fazer merge de duplicatas, ou deletar lixo.

Com a funcao `mesclar_hospitais()` do Epico 3, o backend esta pronto. Este epico cria a interface.

**Objetivo:** Interface completa para revisao, merge e gestao continua de hospitais.

## Escopo

- **Incluido:**
  - Pagina de listagem `/hospitais` com filtros e acoes em lote
  - Pagina de detalhe `/hospitais/[id]` com edicao, aliases e merge
  - Endpoints API para CRUD, merge e aliases
  - Dialog de merge com preview de impacto
  - Link na sidebar de navegacao

- **Excluido:**
  - Merge automatico sem supervisao humana
  - Importacao em massa de hospitais
  - Integracao com mapa/geolocalizacao

---

## Tarefa 5.1: Novos endpoints API

### Objetivo

Endpoints REST para operacoes de gestao de hospitais.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `dashboard/app/api/hospitais/[id]/route.ts` |
| CRIAR | `dashboard/app/api/hospitais/[id]/merge/route.ts` |
| CRIAR | `dashboard/app/api/hospitais/[id]/aliases/route.ts` |
| CRIAR | `dashboard/app/api/hospitais/duplicados/route.ts` |

### Endpoints

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/api/hospitais/[id]` | Detalhe com aliases e stats (count vagas, grupos) |
| PATCH | `/api/hospitais/[id]` | Atualizar nome, cidade, estado, precisa_revisao |
| DELETE | `/api/hospitais/[id]` | Deletar se sem FKs (usa RPC) |
| POST | `/api/hospitais/[id]/merge` | Merge de outro hospital neste (body: `{ duplicado_id }`) |
| GET | `/api/hospitais/[id]/aliases` | Listar aliases |
| POST | `/api/hospitais/[id]/aliases` | Adicionar alias (body: `{ alias }`) |
| DELETE | `/api/hospitais/[id]/aliases?alias_id=X` | Remover alias |
| GET | `/api/hospitais/duplicados` | Candidatos a merge (similaridade, query param: `threshold`) |

### Implementacao (exemplos)

**GET `/api/hospitais/[id]`:**
```typescript
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const hospital = await supabase
    .from('hospitais')
    .select(`
      *,
      hospitais_alias(*),
      vagas(count),
      vagas_grupo(count),
      grupos_whatsapp(count)
    `)
    .eq('id', params.id)
    .single()

  return NextResponse.json(hospital.data)
}
```

**POST `/api/hospitais/[id]/merge`:**
```typescript
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const { duplicado_id } = await request.json()
  const result = await supabase.rpc('mesclar_hospitais', {
    p_principal_id: params.id,
    p_duplicado_id: duplicado_id,
    p_executado_por: 'dashboard',
  })

  return NextResponse.json(result.data)
}
```

**GET `/api/hospitais/duplicados`:**
```typescript
export async function GET(request: NextRequest) {
  const threshold = parseFloat(
    new URL(request.url).searchParams.get('threshold') ?? '0.85'
  )

  // Usa pg_trgm similarity
  const { data } = await supabase.rpc('listar_candidatos_merge', {
    p_threshold: threshold,
    p_limit: 50,
  })

  return NextResponse.json(data)
}
```

### Testes Obrigatorios

- [ ] GET `/api/hospitais/[id]` retorna hospital com aliases e counts
- [ ] PATCH `/api/hospitais/[id]` atualiza campos
- [ ] DELETE `/api/hospitais/[id]` rejeita se tem FKs
- [ ] POST `/api/hospitais/[id]/merge` chama RPC e retorna contagens
- [ ] GET `/api/hospitais/duplicados` retorna pares com score

### Definition of Done

- [ ] Todos os 8 endpoints implementados
- [ ] Validacao de input em todos os endpoints
- [ ] Tratamento de erro consistente
- [ ] Testes passando

---

## Tarefa 5.2: Funcoes de repositorio

### Objetivo

Funcoes TypeScript para as operacoes de gestao no repositorio existente.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `dashboard/lib/hospitais/repository.ts` (304 linhas) |
| MODIFICAR | `dashboard/lib/hospitais/types.ts` (97 linhas) |

### Novas funcoes

```typescript
// repository.ts
export async function buscarHospitalDetalhe(supabase, id: string): Promise<HospitalDetalhe>
export async function atualizarHospital(supabase, id: string, dados: AtualizarHospitalInput): Promise<Hospital>
export async function deletarHospital(supabase, id: string): Promise<boolean>
export async function mesclarHospitais(supabase, principalId: string, duplicadoId: string): Promise<MergeResult>
export async function listarAliases(supabase, hospitalId: string): Promise<HospitalAlias[]>
export async function adicionarAlias(supabase, hospitalId: string, alias: string): Promise<HospitalAlias>
export async function removerAlias(supabase, aliasId: string): Promise<void>
export async function listarCandidatosMerge(supabase, threshold?: number): Promise<MergeCandidate[]>
export async function marcarRevisado(supabase, hospitalId: string): Promise<void>
```

### Novos tipos

```typescript
// types.ts
export interface HospitalDetalhe extends Hospital {
  aliases: HospitalAlias[]
  totalVagas: number
  totalVagasGrupo: number
  totalGrupos: number
  criado_automaticamente: boolean
  precisa_revisao: boolean
  created_at: string
}

export interface HospitalAlias {
  id: string
  alias_original: string
  alias_normalizado: string
  confianca: number
  criado_por: string
}

export interface MergeCandidate {
  hospital_a: { id: string; nome: string; vagas: number }
  hospital_b: { id: string; nome: string; vagas: number }
  similarity: number
}

export interface MergeResult {
  principal_id: string
  duplicado_nome: string
  vagas_migradas: number
  vagas_grupo_migradas: number
  eventos_migrados: number
  aliases_migrados: number
}

export interface AtualizarHospitalInput {
  nome?: string
  cidade?: string
  estado?: string
  precisa_revisao?: boolean
}
```

### Definition of Done

- [ ] Todas as funcoes de repositorio implementadas
- [ ] Tipos TypeScript completos
- [ ] Zero uso de `any`
- [ ] Testes passando

---

## Tarefa 5.3: Pagina de listagem `/hospitais`

### Objetivo

Pagina com tabela de hospitais, filtros, banner de stats e acoes em lote.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `dashboard/app/(dashboard)/hospitais/page.tsx` |

### Componentes da pagina

**Banner de stats:**
- Total de hospitais
- Pendentes de revisao
- Auto-criados
- Duplicatas detectadas (candidatos merge)

**Tabela:**
| Coluna | Tipo | Ordenavel |
|--------|------|-----------|
| Nome | Text | Sim |
| Cidade | Text | Sim |
| Vagas | Number | Sim |
| Status | Badge (revisado/pendente/auto) | Sim |
| Aliases | Number | Nao |
| Acoes | Buttons (editar, deletar) | Nao |

**Filtros:**
- Busca por nome (server-side)
- Status: todos, revisados, pendentes, auto-criados
- Cidade

**Acoes em lote:**
- Selecionar multiplos → merge (escolher principal)
- Selecionar multiplos → deletar (apenas sem FKs)
- Marcar como revisado

### Definition of Done

- [ ] Pagina funcional com tabela, filtros e banner
- [ ] Busca server-side (nao load-all)
- [ ] Acoes em lote: merge, delete, marcar revisado
- [ ] Status badges (revisado/pendente/auto)
- [ ] Responsivo (mobile-friendly)
- [ ] `npm run validate` passando

---

## Tarefa 5.4: Pagina de detalhe `/hospitais/[id]`

### Objetivo

Pagina de detalhe com edicao, aliases, vagas vinculadas e sugestoes de merge.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `dashboard/app/(dashboard)/hospitais/[id]/page.tsx` |

### Componentes da pagina

**Header:**
- Nome (editavel inline)
- Cidade, Estado (editaveis)
- Badge de status
- Botao "Marcar como revisado"

**Secao Aliases:**
- Lista de aliases com botao de remover
- Input para adicionar novo alias

**Secao Vagas:**
- Lista de vagas vinculadas (link para detalhe da vaga)
- Contagem total

**Secao Merge:**
- Sugestoes de merge (hospitais similares com score)
- Para cada sugestao: preview de impacto (quantas vagas, grupos migrariam)
- Botao "Merge" com dialog de confirmacao

### Definition of Done

- [ ] Pagina funcional com todas as secoes
- [ ] Edicao inline de nome, cidade, estado
- [ ] CRUD de aliases
- [ ] Lista de vagas vinculadas
- [ ] Sugestoes de merge com preview
- [ ] Dialog de confirmacao antes de merge
- [ ] `npm run validate` passando

---

## Tarefa 5.5: Dialog de merge

### Objetivo

Componente reutilizavel para merge de hospitais com preview de impacto.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `dashboard/components/hospitais/merge-dialog.tsx` |

### Implementacao

```typescript
interface MergeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  principalId: string
  principalNome: string
  duplicadoId: string
  duplicadoNome: string
  onSuccess: (result: MergeResult) => void
}
```

**Conteudo do dialog:**
- "Merge X → Y" (mostra direcao)
- Preview: quantas vagas, grupos, eventos serao migrados
- Warning: "Esta acao nao pode ser desfeita"
- Botoes: Cancelar, Confirmar merge

### Definition of Done

- [ ] Componente reutilizavel
- [ ] Preview de impacto antes de confirmar
- [ ] Loading state durante merge
- [ ] Toast de sucesso/erro
- [ ] Testes passando

---

## Tarefa 5.6: Atualizar navegacao

### Objetivo

Adicionar link "Hospitais" na sidebar do dashboard.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | Config de navegacao da sidebar (verificar arquivo exato) |

### Posicao

Na secao "Cadastros", junto com "Medicos":

```
Cadastros
├── Medicos
└── Hospitais  ← NOVO
```

### Definition of Done

- [ ] Link na sidebar apontando para `/hospitais`
- [ ] Icone adequado (Building2 do Lucide)
- [ ] Mobile nav atualizado
- [ ] Command palette (Cmd+K) inclui "Hospitais"

---

## Dependencias

Epico 3 (precisa das funcoes SQL `mesclar_hospitais()` e `deletar_hospital_sem_referencias()`).

## Risco: MEDIO

Paginas novas sem risco de backward compat. Merge usa funcao atomica do Epico 3. Principal risco e na UX do merge (usuario merging por engano), mitigado com dialog de confirmacao e preview.
