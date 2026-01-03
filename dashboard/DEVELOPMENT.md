# Dashboard Julia - Guia de Desenvolvimento

## Workflow de Desenvolvimento

```
┌─────────────────────────────────────────────────────────┐
│                    AMBIENTE                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  LOCAL (npm run dev)                                     │
│  ├── Desenvolvimento rápido com hot reload               │
│  ├── http://localhost:3000                               │
│  └── Supabase DEV (ofpnronthwcsybfxnxgj)                │
│           │                                              │
│           ▼                                              │
│  STAGING (Railway DEV - sprint-28/dashboard)             │
│  ├── Valida build na cloud                               │
│  ├── Testa integrações                                   │
│  └── Supabase DEV                                        │
│           │                                              │
│           ▼                                              │
│  PRODUÇÃO (Railway PROD - main)                          │
│  ├── Usuários reais                                      │
│  └── Supabase PROD (jyqgbzhqavgpxqacduoi)               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Instalar dependências

```bash
cd dashboard
npm install
```

### 2. Configurar ambiente local

O arquivo `.env.local` já está configurado com Supabase DEV.
Se precisar recriar:

```bash
cp .env.example .env.local
# Editar .env.local com credenciais do Supabase DEV
```

### 3. Rodar localmente

```bash
npm run dev
```

Acesse: http://localhost:3000

### 4. Outros comandos

```bash
npm run build       # Build de produção
npm run lint        # Verificar linting
npm run type-check  # Verificar tipos TypeScript
```

---

## Ambientes

### Supabase

| Ambiente | Project Ref | URL |
|----------|-------------|-----|
| DEV | `ofpnronthwcsybfxnxgj` | https://ofpnronthwcsybfxnxgj.supabase.co |
| PROD | `jyqgbzhqavgpxqacduoi` | https://jyqgbzhqavgpxqacduoi.supabase.co |

### Railway

| Ambiente | Branch | URL |
|----------|--------|-----|
| DEV | `sprint-28/dashboard` | https://dashboard-production-c25f.up.railway.app |
| PROD | `main` | (a configurar) |

---

## Branches

```
main                    # Produção
└── sprint-28/dashboard # Desenvolvimento do dashboard
```

### Workflow Git

1. **Desenvolver** no branch `sprint-28/dashboard`
2. **Testar** localmente com `npm run dev`
3. **Push** para staging (Railway DEV)
4. **Merge** para `main` quando pronto para produção

```bash
# Verificar branch atual SEMPRE antes de commit
git branch --show-current

# Push para staging
git push origin sprint-28/dashboard

# Merge para produção
git checkout main
git merge sprint-28/dashboard
git push origin main
```

---

## Estrutura do Projeto

```
dashboard/
├── app/                      # Next.js App Router
│   ├── (auth)/               # Rotas de autenticação
│   │   └── login/            # Página de login
│   ├── (dashboard)/          # Rotas protegidas
│   │   ├── page.tsx          # Dashboard principal
│   │   ├── conversas/
│   │   ├── medicos/
│   │   ├── vagas/
│   │   ├── campanhas/
│   │   ├── metricas/
│   │   ├── sistema/
│   │   └── auditoria/
│   ├── callback/             # Auth callback
│   ├── api/                  # API routes
│   ├── globals.css           # Estilos globais
│   └── layout.tsx            # Layout principal
│
├── components/
│   ├── auth/                 # Componentes de auth (RequireRole)
│   ├── dashboard/            # Componentes do dashboard
│   ├── providers/            # Context providers (AuthProvider)
│   └── ui/                   # shadcn/ui components
│
├── hooks/                    # Custom hooks (useAuth)
│
├── lib/
│   ├── supabase/             # Clients Supabase (client/server)
│   ├── api/                  # Cliente API backend
│   └── utils.ts              # Utilitários (cn)
│
├── middleware.ts             # Middleware de autenticação
├── tailwind.config.js        # Configuração Tailwind + Revoluna
├── .env.example              # Template de variáveis
├── .env.local                # Variáveis locais (não commitado)
└── DEVELOPMENT.md            # Este arquivo
```

---

## Autenticação

### Magic Link

O dashboard usa **Magic Link** do Supabase Auth:

1. Usuário entra email em `/login`
2. Supabase envia email com link
3. Link redireciona para `/callback`
4. Callback troca código por sessão
5. Middleware protege rotas autenticadas

### Roles (RBAC)

| Role | Permissões |
|------|------------|
| `viewer` | Apenas visualização |
| `operator` | + Controles básicos (pausar Julia, etc) |
| `manager` | + CRUD de dados (médicos, vagas) |
| `admin` | Acesso total + auditoria |

### Componentes de Auth

```tsx
// Proteger conteúdo por role
import { RequireRole } from "@/components/auth/require-role";

<RequireRole role="manager">
  <BotaoEditar />
</RequireRole>

// Usar hook de auth
import { useAuth } from "@/hooks/use-auth";

const { user, dashboardUser, signOut, hasPermission } = useAuth();

if (hasPermission("admin")) {
  // ...
}
```

---

## Paleta de Cores (Revoluna)

Cor principal: **#C82D37** (vermelho Revoluna)

```tsx
// Tailwind classes
bg-revoluna-400    // Vermelho principal
bg-revoluna-50     // Rosa suave (backgrounds)
text-revoluna-700  // Vermelho escuro (texto)

// Semânticas
bg-primary         // = revoluna-400
text-foreground    // = cinza escuro
bg-background      // = off-white
```

Ver `tailwind.config.js` para escala completa.

---

## Troubleshooting

### Erro de autenticação

```
Error: Auth session missing
```

**Solução:** Verifique se `.env.local` tem as credenciais corretas do Supabase.

### Build falha no Railway

```
The `border-border` class does not exist
```

**Solução:** O `tailwind.config.js` deve mapear as variáveis CSS. Isso já está configurado.

### Hot reload não funciona

**Solução:** Reinicie o servidor de desenvolvimento:

```bash
# Ctrl+C para parar
npm run dev
```

---

## Migrations

### Aplicar no DEV

```bash
# Via Claude Code (MCP)
mcp__supabase-dev__apply_migration

# Via Supabase CLI
supabase db push --db-url "postgresql://..."
```

### Aplicar no PROD

```bash
# Via Claude Code (MCP) - CUIDADO!
mcp__supabase-prod__apply_migration

# Sempre testar no DEV primeiro!
```

---

## Links Úteis

- [Next.js Docs](https://nextjs.org/docs)
- [Supabase Auth](https://supabase.com/docs/guides/auth)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [shadcn/ui](https://ui.shadcn.com)
- [Lucide Icons](https://lucide.dev/icons)
