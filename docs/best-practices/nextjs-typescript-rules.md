# Next.js + TypeScript - Regras Obrigatórias para Claude Code

> **CONSULTA OBRIGATÓRIA**: Este arquivo DEVE ser lido:
> 1. ANTES de escrever qualquer código Next.js/TypeScript
> 2. APÓS terminar de escrever para verificar conformidade
> 3. ANTES de commitar - todos os testes devem passar

---

## PROBLEMAS CRÍTICOS CONHECIDOS

| Problema | Causa | Impacto |
|----------|-------|---------|
| Claude ignora CLAUDE.md | Não consulta automaticamente | Reintroduz bugs já corrigidos |
| Client/Server Component confusion | Importa Node.js em código cliente | Build errors, webpack crashes |
| Hydration errors | Diferença server/client render | UI quebrada, dados que somem |
| Build falha mas dev funciona | Webpack 4 vs 5 incompatibilidade | Deploy impossível |
| Uso excessivo de `any` | Preguiça de tipar | Bugs em produção, TS inútil |
| Testes não executados | Escreve mas não roda | Código quebrado em prod |

---

## 1. WEBPACK BUILD ERROR PREVENTION (PRIORIDADE MÁXIMA)

### Regra: NUNCA importar Node.js em Client Components

**Módulos PROIBIDOS em código cliente:**
- `fs`, `path`, `crypto`, `events`, `stream`, `buffer`, `os`, `util`

**Onde Node.js é PERMITIDO:**
- Server Components (sem "use client")
- API routes (`app/api/**/route.ts`)
- Server Actions ("use server")
- `getServerSideProps`, `getStaticProps`

### Exemplos

```typescript
// ERRADO - Causa build errors
"use client"
import fs from 'fs'

// CORRETO - Server Component (sem diretiva)
import fs from 'fs/promises'
async function ServerComponent() {
  const data = await fs.readFile('file.txt')
}

// CORRETO - Client Component (sem Node.js imports)
"use client"
import { useState } from 'react'
```

### Checklist ANTES de editar qualquer arquivo:

- [ ] Arquivo tem "use client"?
  - SIM → NÃO importar módulos Node.js
  - NÃO → Server Component, Node.js permitido

---

## 2. TYPESCRIPT STRICT - TOLERÂNCIA ZERO PARA `any`

### PROIBIÇÃO ABSOLUTA

```typescript
// PROIBIDO - Será rejeitado
function processData(data: any) { ... }
const response: any = await fetch(...)
const [state, setState] = useState<any>(null)
props: any
catch (error: any)
as any
```

### Padrões OBRIGATÓRIOS

```typescript
// Use unknown + type guards
function processData(data: unknown): User {
  if (!isValidUser(data)) {
    throw new Error('Invalid user data')
  }
  return data
}

// Generics tipados
async function fetchData<T>(url: string): Promise<T> {
  const response = await fetch(url)
  return response.json() as T
}

// State tipado
interface UserState {
  user: User | null
  loading: boolean
  error: Error | null
}
const [state, setState] = useState<UserState>({
  user: null,
  loading: false,
  error: null
})

// Error typing correto
catch (error: unknown) {
  if (error instanceof Error) {
    console.error(error.message)
  }
}

// Props sempre com interface
interface ButtonProps {
  onClick: () => void
  disabled?: boolean
  label: string
}
```

### Type Guards - OBRIGATÓRIO para dados externos

```typescript
// Type guard pattern
function isUser(data: unknown): data is User {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    'name' in data &&
    typeof data.id === 'string' &&
    typeof data.name === 'string'
  )
}

// Type guard para erros de API
function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    'message' in error
  )
}

// Uso
async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`/api/users/${id}`)
  const data: unknown = await response.json()

  if (!isUser(data)) {
    throw new Error('Invalid user data from API')
  }

  return data // Agora é User, não unknown
}
```

### Retornos Explícitos - OBRIGATÓRIO

```typescript
// ERRADO - Retorno inferido pode ser any
async function getData() {
  return await fetch('/api/data').then(r => r.json())
}

// CORRETO - Retorno explícito
async function getData(): Promise<UserData> {
  const response = await fetch('/api/data')
  const data: unknown = await response.json()

  if (!isUserData(data)) {
    throw new Error('Invalid data structure')
  }

  return data
}
```

### Event Handlers React - Tipagem Correta

```typescript
const handleClick = (e: React.MouseEvent<HTMLButtonElement>): void => {
  e.preventDefault()
}

const handleChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
  const value = e.target.value
}

const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
  e.preventDefault()
}
```

### Discriminated Unions para Estado Complexo

```typescript
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error }

function renderState<T>(state: AsyncState<T>): JSX.Element {
  switch (state.status) {
    case 'idle':
      return <div>Click to load</div>
    case 'loading':
      return <div>Loading...</div>
    case 'success':
      return <div>{JSON.stringify(state.data)}</div>
    case 'error':
      return <div>Error: {state.error.message}</div>
    default:
      const _exhaustive: never = state
      return _exhaustive
  }
}
```

### Validação com Zod (Recomendado)

```typescript
import { z } from 'zod'

const UserSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
  age: z.number().min(0)
})

type User = z.infer<typeof UserSchema>

async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`/api/users/${id}`)
  const data: unknown = await response.json()

  return UserSchema.parse(data) // Valida e retorna tipado
}
```

---

## 3. HYDRATION ERROR PREVENTION

### NUNCA usar durante render inicial:

```typescript
// PROIBIDO no render
Math.random()
Date.now()
new Date() // sem formatação consistente
window, document, localStorage, sessionStorage
IDs aleatórios sem seed
```

### Padrões CORRETOS:

```typescript
// ERRADO - Diferente server/client
const id = Math.random()

// CORRETO - Consistente
const id = useId() // React 18+

// ERRADO - Window no render
const isMobile = window.innerWidth < 768

// CORRETO - Window após mount
const [isMobile, setIsMobile] = useState(false)
useEffect(() => {
  setIsMobile(window.innerWidth < 768)
}, [])
```

### Dynamic Imports para código browser-only:

```typescript
import dynamic from 'next/dynamic'

const BrowserOnlyComponent = dynamic(
  () => import('./BrowserComponent'),
  { ssr: false }
)
```

---

## 4. ESTRUTURA DE PROJETO RECOMENDADA

```
app/
├── (routes)/
│   ├── page.tsx          # Server Component (default)
│   └── layout.tsx        # Server Component (default)
├── components/
│   ├── client/           # Client Components ("use client")
│   └── server/           # Server Components (sem diretiva)
├── lib/
│   ├── server/           # Utilities server-only (Node.js OK)
│   └── client/           # Utilities cliente (NO Node.js)
└── api/
    └── */route.ts        # API routes (Node.js OK)
```

---

## 5. TSCONFIG.JSON - CONFIGURAÇÃO OBRIGATÓRIA

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

---

## 6. ESLINT - REGRAS OBRIGATÓRIAS

```javascript
// .eslintrc.js
module.exports = {
  rules: {
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unsafe-assignment': 'error',
    '@typescript-eslint/no-unsafe-member-access': 'error',
    '@typescript-eslint/no-unsafe-call': 'error',
    '@typescript-eslint/no-unsafe-return': 'error',
    '@typescript-eslint/explicit-function-return-type': 'warn',
    '@typescript-eslint/explicit-module-boundary-types': 'warn'
  }
}
```

---

## 7. WORKFLOW OBRIGATÓRIO

### Fase 1: Planejamento (ANTES de codificar)

1. Ler este arquivo (CLAUDE.md)
2. Ler arquivos relevantes do projeto
3. Identificar: é código client ou server?
4. Identificar riscos de hydration
5. Criar plano de implementação
6. **AGUARDAR aprovação antes de codificar**

### Fase 2: Implementação

1. Escrever/atualizar TESTES primeiro (TDD)
2. Implementar código para passar testes
3. Rodar validação (ver abaixo)

### Fase 3: Validação (OBRIGATÓRIO após cada mudança)

```bash
# 1. Type checking - DEVE passar com ZERO erros
npm run tsc -- --noEmit

# 2. Verificar uso de any
grep -r ": any" src/
grep -r "<any>" src/
grep -r "as any" src/

# 3. Linting
npm run lint

# 4. Formatting
npm run format

# 5. Testes
npm test

# 6. Build (para mudanças críticas)
npm run build
```

### Checklist ANTES de commitar:

- [ ] ZERO instâncias de `: any`
- [ ] ZERO instâncias de `as any`
- [ ] ZERO instâncias de `<any>`
- [ ] ZERO erros TypeScript (`npm run tsc --noEmit`)
- [ ] Todos retornos de função explícitos
- [ ] Todas funções async retornam `Promise<T>` explícito
- [ ] Todos `unknown` têm type guards antes de uso
- [ ] Todas respostas de API validadas com Zod ou type guards
- [ ] Todos event handlers React tipados
- [ ] Todas interfaces de props definidas
- [ ] Lint passa sem erros
- [ ] Todos testes passam
- [ ] Build passa (se aplicável)

---

## 8. ERROR RECOVERY

### "Invalid or unexpected token" durante build:

1. PARAR imediatamente
2. Buscar imports Node.js em arquivos client
3. Mover código server para Server Components/API routes
4. Re-rodar build

### "Hydration failed":

1. Verificar `window`, `Math.random()`, `Date` no render
2. Mover para `useEffect` ou usar `useState` com inicial false
3. Garantir que server/client renderizam mesmo HTML inicial

### "Module not found":

1. Verificar paths de import
2. Verificar se arquivo existe
3. Checar dependências circulares

---

## 9. ARMADILHAS COMUNS COM `any`

### Libraries sem tipos:

```typescript
// ERRADO - Fallback para any
import SomeLibrary from 'untyped-library'

// CORRETO - Criar declaration file
// types/untyped-library.d.ts
declare module 'untyped-library' {
  export interface SomeLibraryConfig {
    apiKey: string
    endpoint: string
  }

  export default function SomeLibrary(
    config: SomeLibraryConfig
  ): Promise<void>
}
```

### JSON.parse:

```typescript
// ERRADO
const data = JSON.parse(jsonString) // Type é any

// CORRETO
const data: unknown = JSON.parse(jsonString)
if (!isExpectedType(data)) {
  throw new Error('Invalid JSON structure')
}
```

### Object.keys / Object.entries:

```typescript
// ERRADO - Resulta em any
const obj = { a: 1, b: 2 }
Object.keys(obj).forEach(key => {
  console.log(obj[key]) // Type é any
})

// CORRETO
const obj = { a: 1, b: 2 } as const
type ObjKeys = keyof typeof obj

Object.keys(obj).forEach((key) => {
  const typedKey = key as ObjKeys
  console.log(obj[typedKey]) // Type é number
})

// OU usar Object.entries
Object.entries(obj).forEach(([key, value]) => {
  console.log(key, value) // Ambos tipados
})
```

---

## 10. COMANDOS CUSTOMIZADOS (.claude/commands/)

### validate.md

```markdown
Run validation sequence on $ARGUMENTS:
1. TypeScript check: `npm run tsc --noEmit $ARGUMENTS`
2. Linting: `npm run eslint --fix $ARGUMENTS`
3. Formatting: `npm run prettier --write $ARGUMENTS`
4. Tests: `npm test $ARGUMENTS`

Show results of each step. Stop if any fail.
```

### check-any.md

```markdown
Scan $ARGUMENTS for ANY usage of the `any` type.

Search patterns:
1. `: any` (variable/parameter typing)
2. `<any>` (generic typing)
3. `as any` (type assertions)
4. `any[]` (array typing)
5. `Record<string, any>` (object typing)

For EACH occurrence found:
1. Report file path and line number
2. Show the problematic code
3. Suggest the proper type alternative
4. Provide example fix

If ZERO `any` found: Report "Type safety verified - no any detected"
If ANY `any` found: Report "TYPE SAFETY VIOLATION - Fix required"
```

### check-client-server.md

```markdown
Analyze $ARGUMENTS and report:
1. Does file have "use client" directive?
2. List all imports from Node.js modules (fs, path, crypto, etc.)
3. If Client Component + Node.js imports = ERROR - explain fix
4. Check for window/document access during render
5. Suggest fixes if issues found
```

---

## 11. HOOKS DE VALIDAÇÃO (.claude/hooks/)

### pre-commit.json

```json
{
  "stop": [
    "grep -r ': any' src/ && exit 1 || exit 0",
    "grep -r '<any>' src/ && exit 1 || exit 0",
    "grep -r 'as any' src/ && exit 1 || exit 0",
    "npm run tsc -- --noEmit"
  ]
}
```

---

## 12. RESUMO EXECUTIVO

### 5 Regras de Ouro:

1. **NUNCA use `any`** - Use `unknown` + type guards
2. **Separe Client/Server** - Node.js só em Server Components
3. **Valide SEMPRE** - typecheck → lint → format → test
4. **Hydration safe** - Nada dinâmico no render inicial
5. **TDD** - Testes primeiro, código depois

### Padrão de Substituição any → Tipo:

```typescript
// De:
const data: any = await response.json()

// Para:
const data: unknown = await response.json()
if (!isValidData(data)) throw new Error('Invalid data')
return data // agora é tipado
```

### Checklist Mental (SEMPRE seguir):

- [ ] Todos retornos de função explícitos
- [ ] `unknown` ao invés de `any` para dados externos
- [ ] Type guards implementados e testados
- [ ] Zero erros TypeScript compiler
- [ ] Zero warnings sobre `any`
- [ ] Nenhum Node.js import em Client Components
- [ ] Nenhum código dinâmico no render inicial
