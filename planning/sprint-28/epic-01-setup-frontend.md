# E01: Setup Projeto Frontend

**Épico:** Setup Next.js + Tailwind + shadcn/ui + Railway
**Estimativa:** 6h
**Prioridade:** P0 (Bloqueante)
**Dependências:** Nenhuma

---

## Objetivo

Configurar a estrutura base do projeto frontend com:
- Next.js 14 (App Router)
- Tailwind CSS + shadcn/ui
- TypeScript strict mode
- Deploy automático no Railway
- CI/CD com GitHub Actions

---

## Estrutura do Projeto

```
/dashboard
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions
├── app/
│   ├── (auth)/                 # Grupo de rotas de auth
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── callback/
│   │       └── route.ts
│   ├── (dashboard)/            # Grupo de rotas protegidas
│   │   ├── layout.tsx          # Layout com sidebar
│   │   ├── page.tsx            # Dashboard principal
│   │   ├── conversas/
│   │   ├── medicos/
│   │   ├── vagas/
│   │   ├── campanhas/
│   │   ├── metricas/
│   │   ├── sistema/
│   │   └── auditoria/
│   ├── api/                    # API routes (BFF)
│   │   └── health/
│   │       └── route.ts
│   ├── globals.css
│   ├── layout.tsx              # Root layout
│   └── not-found.tsx
├── components/
│   ├── ui/                     # shadcn/ui (auto-gerado)
│   ├── layout/
│   │   ├── sidebar.tsx
│   │   ├── header.tsx
│   │   ├── bottom-nav.tsx
│   │   └── mobile-drawer.tsx
│   └── providers/
│       ├── auth-provider.tsx
│       ├── query-provider.tsx
│       └── theme-provider.tsx
├── lib/
│   ├── supabase/
│   │   ├── client.ts           # Browser client
│   │   ├── server.ts           # Server client
│   │   └── middleware.ts       # Auth middleware
│   ├── api/
│   │   ├── client.ts           # API client (FastAPI)
│   │   └── endpoints.ts        # Endpoints tipados
│   └── utils.ts
├── hooks/
│   ├── use-auth.ts
│   ├── use-notifications.ts
│   └── use-mobile.ts
├── types/
│   ├── database.ts             # Tipos do Supabase
│   ├── api.ts                  # Tipos das APIs
│   └── index.ts
├── .env.local.example
├── .eslintrc.json
├── .prettierrc
├── components.json             # shadcn/ui config
├── middleware.ts               # Next.js middleware
├── next.config.js
├── package.json
├── postcss.config.js
├── tailwind.config.ts
└── tsconfig.json
```

---

## Stories

### S01.1: Criar projeto Next.js

**Tarefas:**

```bash
# 1. Criar projeto
npx create-next-app@latest dashboard --typescript --tailwind --eslint --app --src-dir=false --import-alias "@/*"

# 2. Entrar no diretório
cd dashboard

# 3. Instalar dependências base
npm install @supabase/supabase-js @supabase/ssr
npm install @tanstack/react-query
npm install lucide-react
npm install date-fns
npm install zod
npm install clsx tailwind-merge

# 4. Instalar dev dependencies
npm install -D @types/node
```

**DoD:**
- [ ] Projeto criado e rodando localmente
- [ ] TypeScript strict mode habilitado
- [ ] ESLint + Prettier configurados

---

### S01.2: Configurar shadcn/ui

**Tarefas:**

```bash
# 1. Inicializar shadcn/ui
npx shadcn-ui@latest init

# Opções:
# - Style: Default
# - Base color: Slate
# - CSS variables: Yes

# 2. Instalar componentes essenciais
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add label
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add avatar
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add sheet
npx shadcn-ui@latest add skeleton
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add tooltip
npx shadcn-ui@latest add switch
npx shadcn-ui@latest add slider
npx shadcn-ui@latest add select
npx shadcn-ui@latest add table
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add alert
npx shadcn-ui@latest add separator
npx shadcn-ui@latest add scroll-area
```

**Arquivo:** `tailwind.config.ts`

```typescript
import type { Config } from "tailwindcss"

const config = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Julia brand colors
        julia: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          800: "#075985",
          900: "#0c4a6e",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config

export default config
```

**DoD:**
- [ ] shadcn/ui inicializado
- [ ] Componentes base instalados
- [ ] Cores Julia configuradas
- [ ] Dark mode funcionando

---

### S01.3: Configurar Supabase Client

**Arquivo:** `lib/supabase/client.ts`

```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

**Arquivo:** `lib/supabase/server.ts`

```typescript
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

export function createClient() {
  const cookieStore = cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value
        },
        set(name: string, value: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value, ...options })
          } catch (error) {
            // Handle cookies in middleware
          }
        },
        remove(name: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value: '', ...options })
          } catch (error) {
            // Handle cookies in middleware
          }
        },
      },
    }
  )
}
```

**Arquivo:** `.env.local.example`

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx

# FastAPI Backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

**DoD:**
- [ ] Client browser funcionando
- [ ] Client server funcionando
- [ ] Variáveis de ambiente documentadas

---

### S01.4: Configurar API Client (FastAPI)

**Arquivo:** `lib/api/client.ts`

```typescript
import { createClient } from '@/lib/supabase/client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>
}

class APIClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async getAuthHeaders(): Promise<HeadersInit> {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()

    return {
      'Content-Type': 'application/json',
      ...(session?.access_token && {
        Authorization: `Bearer ${session.access_token}`,
      }),
    }
  }

  private buildUrl(path: string, params?: Record<string, string | number | boolean>): string {
    const url = new URL(`${this.baseUrl}${path}`)
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, String(value))
      })
    }
    return url.toString()
  }

  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const headers = await this.getAuthHeaders()
    const url = this.buildUrl(path, options?.params)

    const response = await fetch(url, {
      method: 'GET',
      headers,
      ...options,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`)
    }

    return response.json()
  }

  async post<T>(path: string, data?: unknown, options?: RequestOptions): Promise<T> {
    const headers = await this.getAuthHeaders()
    const url = this.buildUrl(path, options?.params)

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`)
    }

    return response.json()
  }

  async put<T>(path: string, data?: unknown, options?: RequestOptions): Promise<T> {
    const headers = await this.getAuthHeaders()
    const url = this.buildUrl(path, options?.params)

    const response = await fetch(url, {
      method: 'PUT',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`)
    }

    return response.json()
  }

  async delete<T>(path: string, options?: RequestOptions): Promise<T> {
    const headers = await this.getAuthHeaders()
    const url = this.buildUrl(path, options?.params)

    const response = await fetch(url, {
      method: 'DELETE',
      headers,
      ...options,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`)
    }

    return response.json()
  }
}

export const api = new APIClient(API_URL)
```

**DoD:**
- [ ] API client com autenticação
- [ ] Métodos GET, POST, PUT, DELETE
- [ ] Tipagem TypeScript completa

---

### S01.5: Deploy Railway

**Arquivo:** `railway.toml` (na raiz do monorepo)

```toml
[build]
builder = "nixpacks"
watchPatterns = ["dashboard/**"]

[deploy]
startCommand = "cd dashboard && npm run start"
healthcheckPath = "/api/health"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

**Ou criar como serviço separado:**

```bash
# No Railway dashboard:
# 1. New Service → GitHub Repo
# 2. Root Directory: /dashboard
# 3. Build Command: npm run build
# 4. Start Command: npm run start

# Variáveis de ambiente no Railway:
NEXT_PUBLIC_SUPABASE_URL=xxx
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
NEXT_PUBLIC_API_URL=https://your-api.railway.app
NEXT_PUBLIC_APP_URL=https://your-dashboard.railway.app
```

**Arquivo:** `next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000', '*.railway.app'],
    },
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.supabase.co',
      },
    ],
  },
}

module.exports = nextConfig
```

**Arquivo:** `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
    paths:
      - 'dashboard/**'
  pull_request:
    branches: [main]
    paths:
      - 'dashboard/**'

jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: dashboard

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: dashboard/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run type-check

      - name: Build
        run: npm run build
        env:
          NEXT_PUBLIC_SUPABASE_URL: ${{ secrets.NEXT_PUBLIC_SUPABASE_URL }}
          NEXT_PUBLIC_SUPABASE_ANON_KEY: ${{ secrets.NEXT_PUBLIC_SUPABASE_ANON_KEY }}
          NEXT_PUBLIC_API_URL: ${{ secrets.NEXT_PUBLIC_API_URL }}
```

**DoD:**
- [ ] Deploy automático no Railway
- [ ] CI rodando no GitHub Actions
- [ ] Health check configurado
- [ ] Variáveis de ambiente no Railway

---

## Checklist Final

- [ ] Projeto Next.js criado
- [ ] TypeScript strict mode
- [ ] Tailwind + shadcn/ui configurados
- [ ] Supabase client funcionando
- [ ] API client funcionando
- [ ] Deploy Railway funcionando
- [ ] CI/CD configurado
- [ ] Documentação README atualizada
