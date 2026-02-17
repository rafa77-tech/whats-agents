# EPICO 4: Fix do Dropdown do Dashboard

## Contexto

O dropdown de hospitais nos dialogos de criar/editar vaga carrega TODOS os 2.703 registros do banco de uma vez. Isso torna o componente lento, inutilizavel com scroll infinito, e sem busca efetiva.

**Arquivos afetados:**
- `dashboard/lib/hospitais/repository.ts` (304 linhas) — `listarHospitais()`
- `dashboard/lib/hospitais/types.ts` (97 linhas) — tipos de parametros
- `dashboard/app/api/hospitais/route.ts` (60 linhas) — endpoint GET
- `dashboard/app/(dashboard)/vagas/components/nova-vaga-dialog.tsx` (648 linhas) — dropdown
- `dashboard/app/(dashboard)/vagas/components/editar-vaga-dialog.tsx` (611 linhas) — dropdown

**Objetivo:** Tornar o dropdown utilizavel com busca server-side e filtros inteligentes.

## Escopo

- **Incluido:**
  - Busca server-side com `ilike` no repositorio
  - Filtro `precisa_revisao = false` por padrao no dropdown
  - Limite de resultados (50)
  - Ordenacao por relevancia (vagas abertas)
  - Debounce no input de busca dos dialogos

- **Excluido:**
  - Pagina de gestao de hospitais (Epico 5)
  - Merge de hospitais no dropdown
  - Autocomplete com fuzzy search

---

## Tarefa 4.1: Atualizar repositorio e tipos

### Objetivo

Adicionar parametros de busca, filtro e limite em `listarHospitais()`.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `dashboard/lib/hospitais/repository.ts` (304 linhas) |
| MODIFICAR | `dashboard/lib/hospitais/types.ts` (97 linhas) |

### Implementacao

**types.ts — novos campos em `ListarHospitaisParams`:**

```typescript
export interface ListarHospitaisParams {
  excluirBloqueados?: boolean
  // Novos params
  search?: string           // Busca por nome (ilike)
  apenasRevisados?: boolean // Filtrar precisa_revisao = false
  limit?: number            // Default: 50
  orderBy?: 'nome' | 'vagas_abertas'  // Default: vagas_abertas DESC
}
```

**repository.ts — `listarHospitais()` atualizada:**

```typescript
export async function listarHospitais(
  supabase: SupabaseClient,
  params: ListarHospitaisParams = {}
): Promise<Hospital[]> {
  const {
    excluirBloqueados = false,
    search,
    apenasRevisados = false,
    limit = 50,
    orderBy = 'nome',
  } = params

  let query = supabase
    .from('hospitais')
    .select('id, nome, cidade, estado, ativo, precisa_revisao')
    .eq('ativo', true)

  if (apenasRevisados) {
    query = query.eq('precisa_revisao', false)
  }

  if (search && search.length >= 2) {
    query = query.ilike('nome', `%${search}%`)
  }

  if (excluirBloqueados) {
    // ... logica existente ...
  }

  query = query
    .order(orderBy === 'vagas_abertas' ? 'vagas_abertas' : 'nome', {
      ascending: orderBy !== 'vagas_abertas',
    })
    .limit(limit)

  const { data, error } = await query
  if (error) throw error
  return data ?? []
}
```

### Testes Obrigatorios

- [ ] `listarHospitais({ search: "sao luiz" })` filtra por nome
- [ ] `listarHospitais({ apenasRevisados: true })` exclui pendentes
- [ ] `listarHospitais({ limit: 10 })` retorna no maximo 10
- [ ] `listarHospitais({})` retorna default (50, sem filtro de revisao)
- [ ] Backward compatible: chamada sem params funciona como antes

### Definition of Done

- [ ] Novos campos em `ListarHospitaisParams`
- [ ] `listarHospitais()` com busca, filtro e limite
- [ ] Backward compatible
- [ ] Testes passando

---

## Tarefa 4.2: Atualizar endpoint API

### Objetivo

Expor novos query params no endpoint GET `/api/hospitais`.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `dashboard/app/api/hospitais/route.ts` (60 linhas) |

### Implementacao

```typescript
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const search = searchParams.get('search') ?? undefined
  const apenasRevisados = searchParams.get('apenas_revisados') === 'true'
  const limit = parseInt(searchParams.get('limit') ?? '50', 10)
  const excluirBloqueados = searchParams.get('excluir_bloqueados') === 'true'

  const hospitais = await listarHospitais(supabase, {
    search,
    apenasRevisados,
    limit: Math.min(limit, 200), // Cap maximo
    excluirBloqueados,
  })

  return NextResponse.json(hospitais)
}
```

### Testes Obrigatorios

- [ ] `GET /api/hospitais?search=sao+luiz` passa search para repositorio
- [ ] `GET /api/hospitais?apenas_revisados=true` filtra revisados
- [ ] `GET /api/hospitais?limit=10` limita resultados
- [ ] `GET /api/hospitais` sem params retorna default
- [ ] `limit` nao pode exceder 200

### Definition of Done

- [ ] Query params `search`, `apenas_revisados`, `limit` implementados
- [ ] Cap de 200 no limit
- [ ] Backward compatible
- [ ] Testes passando

---

## Tarefa 4.3: Atualizar dialogos de vaga

### Objetivo

Trocar load-all por busca server-side debounced nos dialogos `nova-vaga-dialog.tsx` e `editar-vaga-dialog.tsx`.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `dashboard/app/(dashboard)/vagas/components/nova-vaga-dialog.tsx` (648 linhas) |
| MODIFICAR | `dashboard/app/(dashboard)/vagas/components/editar-vaga-dialog.tsx` (611 linhas) |

### Implementacao

**Padrao de busca debounced:**

```typescript
const [hospitalSearch, setHospitalSearch] = useState('')
const [hospitais, setHospitais] = useState<Hospital[]>([])
const [loadingHospitais, setLoadingHospitais] = useState(false)

// Debounce de 300ms
useEffect(() => {
  const timer = setTimeout(async () => {
    setLoadingHospitais(true)
    try {
      const params = new URLSearchParams({
        apenas_revisados: 'true',
        limit: '20',
      })
      if (hospitalSearch.length >= 2) {
        params.set('search', hospitalSearch)
      }
      const res = await fetch(`/api/hospitais?${params}`)
      const data = await res.json()
      setHospitais(data)
    } finally {
      setLoadingHospitais(false)
    }
  }, 300)

  return () => clearTimeout(timer)
}, [hospitalSearch])
```

**Comportamento:**
- Ao abrir: carrega top 20 hospitais por contagem de vagas
- Ao digitar (>= 2 chars): busca server-side com debounce 300ms
- Loading state enquanto busca
- Resultado limitado a 20 items no dropdown

**editar-vaga-dialog.tsx:**
- Mesmo padrao do nova-vaga-dialog
- Pre-seleciona hospital atual da vaga
- Se hospital atual nao esta nos resultados, adiciona no topo

### Testes Obrigatorios

- [ ] Dropdown carrega top 20 ao abrir
- [ ] Busca dispara apos 2 chars
- [ ] Debounce de 300ms funciona (nao faz request a cada keystroke)
- [ ] Loading state visivel durante busca
- [ ] Hospital atual preservado no editar-vaga-dialog

### Definition of Done

- [ ] Ambos dialogos com busca server-side
- [ ] Debounce 300ms
- [ ] Top 20 por default
- [ ] Loading state
- [ ] Hospital atual preservado na edicao
- [ ] `npm run validate` passando
- [ ] `npm run build` passando

---

## Dependencias

Pode ser feito em paralelo com Epicos 1 e 2. Fica melhor apos Epico 3 (menos registros), mas nao bloqueia.

## Risco: BAIXO

Mudancas aditivas com backward compatibility. Dropdown funciona melhor com menos dados, mas funciona mesmo antes da limpeza.
