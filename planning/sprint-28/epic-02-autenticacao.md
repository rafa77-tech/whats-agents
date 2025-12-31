# E02: Autenticação Supabase

**Épico:** Login + RBAC + Middleware
**Estimativa:** 6h
**Prioridade:** P0 (Bloqueante)
**Dependências:** E01

---

## Objetivo

Implementar autenticação completa com:
- Login via Supabase Auth (email/password ou magic link)
- RBAC (Role-Based Access Control)
- Middleware de proteção de rotas
- Sessão persistente
- Logout

---

## Roles e Permissões

### Tabela: dashboard_users

```sql
CREATE TABLE dashboard_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    nome TEXT NOT NULL,
    avatar_url TEXT,
    role TEXT NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('viewer', 'operator', 'manager', 'admin')),
    ativo BOOLEAN DEFAULT true,
    ultimo_acesso TIMESTAMPTZ,
    notificacoes_habilitadas BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Índices
CREATE INDEX idx_dashboard_users_supabase ON dashboard_users(supabase_user_id);
CREATE INDEX idx_dashboard_users_email ON dashboard_users(email);

-- RLS
ALTER TABLE dashboard_users ENABLE ROW LEVEL SECURITY;

-- Política: usuário pode ver próprio registro
CREATE POLICY "Users can view own record"
ON dashboard_users FOR SELECT
USING (supabase_user_id = auth.uid());

-- Política: admin pode ver todos
CREATE POLICY "Admin can view all"
ON dashboard_users FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM dashboard_users
    WHERE supabase_user_id = auth.uid() AND role = 'admin'
  )
);

-- Trigger para atualizar updated_at
CREATE TRIGGER update_dashboard_users_updated_at
    BEFORE UPDATE ON dashboard_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Trigger para criar registro ao criar usuário
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.dashboard_users (supabase_user_id, email, nome)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1))
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();
```

---

## Stories

### S02.1: Página de Login

**Arquivo:** `app/(auth)/login/page.tsx`

```tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2 } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const supabase = createClient()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'password' | 'magic_link'>('password')

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      if (mode === 'password') {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (error) throw error
        router.push('/')
        router.refresh()
      } else {
        const { error } = await supabase.auth.signInWithOtp({
          email,
          options: {
            emailRedirectTo: `${window.location.origin}/callback`,
          },
        })
        if (error) throw error
        setError('Link mágico enviado! Verifique seu email.')
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao fazer login')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-julia-50 to-julia-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-julia-500 flex items-center justify-center">
            <span className="text-white font-bold text-xl">J</span>
          </div>
          <CardTitle className="text-2xl">Julia Dashboard</CardTitle>
          <CardDescription>
            Entre para acessar o painel de controle
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            {error && (
              <Alert variant={error.includes('enviado') ? 'default' : 'destructive'}>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            {mode === 'password' && (
              <div className="space-y-2">
                <Label htmlFor="password">Senha</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                />
              </div>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Carregando...
                </>
              ) : mode === 'password' ? (
                'Entrar'
              ) : (
                'Enviar link mágico'
              )}
            </Button>

            <div className="text-center">
              <button
                type="button"
                className="text-sm text-muted-foreground hover:text-primary underline"
                onClick={() => setMode(mode === 'password' ? 'magic_link' : 'password')}
              >
                {mode === 'password'
                  ? 'Prefere receber um link por email?'
                  : 'Prefere usar senha?'}
              </button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
```

**DoD:**
- [ ] Página de login responsiva
- [ ] Login com email/senha funcionando
- [ ] Magic link funcionando
- [ ] Mensagens de erro claras

---

### S02.2: Callback de Auth

**Arquivo:** `app/(auth)/callback/route.ts`

```typescript
import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const next = requestUrl.searchParams.get('next') ?? '/'

  if (code) {
    const supabase = createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)

    if (!error) {
      return NextResponse.redirect(new URL(next, requestUrl.origin))
    }
  }

  // Redirect to login on error
  return NextResponse.redirect(new URL('/login', requestUrl.origin))
}
```

**DoD:**
- [ ] Magic link redireciona corretamente
- [ ] Sessão criada após callback

---

### S02.3: Middleware de Autenticação

**Arquivo:** `middleware.ts`

```typescript
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value
        },
        set(name: string, value: string, options: CookieOptions) {
          request.cookies.set({
            name,
            value,
            ...options,
          })
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          })
          response.cookies.set({
            name,
            value,
            ...options,
          })
        },
        remove(name: string, options: CookieOptions) {
          request.cookies.set({
            name,
            value: '',
            ...options,
          })
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          })
          response.cookies.set({
            name,
            value: '',
            ...options,
          })
        },
      },
    }
  )

  const { data: { session } } = await supabase.auth.getSession()

  // Rotas públicas
  const publicRoutes = ['/login', '/callback', '/api/health']
  const isPublicRoute = publicRoutes.some(route =>
    request.nextUrl.pathname.startsWith(route)
  )

  // Redirecionar para login se não autenticado
  if (!session && !isPublicRoute) {
    const redirectUrl = new URL('/login', request.url)
    redirectUrl.searchParams.set('next', request.nextUrl.pathname)
    return NextResponse.redirect(redirectUrl)
  }

  // Redirecionar para dashboard se já logado tentando acessar login
  if (session && request.nextUrl.pathname === '/login') {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
```

**DoD:**
- [ ] Rotas protegidas redirecionam para login
- [ ] Usuário logado não vê página de login
- [ ] Sessão persistida entre requests

---

### S02.4: Auth Provider e Hook

**Arquivo:** `components/providers/auth-provider.tsx`

```tsx
'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { User, Session } from '@supabase/supabase-js'
import { createClient } from '@/lib/supabase/client'

type UserRole = 'viewer' | 'operator' | 'manager' | 'admin'

interface DashboardUser {
  id: string
  email: string
  nome: string
  avatar_url: string | null
  role: UserRole
}

interface AuthContextType {
  user: User | null
  dashboardUser: DashboardUser | null
  session: Session | null
  loading: boolean
  signOut: () => Promise<void>
  hasPermission: (requiredRole: UserRole) => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const ROLE_HIERARCHY: Record<UserRole, number> = {
  viewer: 0,
  operator: 1,
  manager: 2,
  admin: 3,
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const supabase = createClient()

  const [user, setUser] = useState<User | null>(null)
  const [dashboardUser, setDashboardUser] = useState<DashboardUser | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      if (session?.user) {
        fetchDashboardUser(session.user.id)
      } else {
        setLoading(false)
      }
    })

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session)
        setUser(session?.user ?? null)

        if (session?.user) {
          await fetchDashboardUser(session.user.id)
        } else {
          setDashboardUser(null)
        }

        if (event === 'SIGNED_OUT') {
          router.push('/login')
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  async function fetchDashboardUser(supabaseUserId: string) {
    try {
      const { data, error } = await supabase
        .from('dashboard_users')
        .select('*')
        .eq('supabase_user_id', supabaseUserId)
        .single()

      if (error) throw error
      setDashboardUser(data)

      // Atualizar último acesso
      await supabase
        .from('dashboard_users')
        .update({ ultimo_acesso: new Date().toISOString() })
        .eq('id', data.id)

    } catch (error) {
      console.error('Error fetching dashboard user:', error)
    } finally {
      setLoading(false)
    }
  }

  async function signOut() {
    await supabase.auth.signOut()
  }

  function hasPermission(requiredRole: UserRole): boolean {
    if (!dashboardUser) return false
    return ROLE_HIERARCHY[dashboardUser.role] >= ROLE_HIERARCHY[requiredRole]
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        dashboardUser,
        session,
        loading,
        signOut,
        hasPermission,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
```

**Arquivo:** `hooks/use-auth.ts`

```typescript
export { useAuth } from '@/components/providers/auth-provider'
```

**DoD:**
- [ ] AuthProvider envolvendo app
- [ ] Hook useAuth funcionando
- [ ] hasPermission verificando roles
- [ ] Último acesso sendo atualizado

---

### S02.5: Componente de Proteção de Role

**Arquivo:** `components/auth/require-role.tsx`

```tsx
'use client'

import { useAuth } from '@/hooks/use-auth'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { ShieldX } from 'lucide-react'

type UserRole = 'viewer' | 'operator' | 'manager' | 'admin'

interface RequireRoleProps {
  role: UserRole
  children: React.ReactNode
  fallback?: React.ReactNode
}

export function RequireRole({ role, children, fallback }: RequireRoleProps) {
  const { hasPermission, loading } = useAuth()

  if (loading) {
    return null // ou skeleton
  }

  if (!hasPermission(role)) {
    if (fallback) {
      return <>{fallback}</>
    }

    return (
      <Alert variant="destructive">
        <ShieldX className="h-4 w-4" />
        <AlertTitle>Acesso negado</AlertTitle>
        <AlertDescription>
          Você não tem permissão para acessar este recurso.
          Entre em contato com um administrador.
        </AlertDescription>
      </Alert>
    )
  }

  return <>{children}</>
}
```

**Uso:**

```tsx
// Em qualquer componente
<RequireRole role="manager">
  <Button onClick={handleDelete}>Deletar</Button>
</RequireRole>

// Com fallback customizado
<RequireRole role="admin" fallback={<span>Apenas admins</span>}>
  <SettingsPanel />
</RequireRole>
```

**DoD:**
- [ ] Componente RequireRole funcionando
- [ ] Fallback customizável
- [ ] Suporte a todos os roles

---

### S02.6: Logout e User Menu

**Arquivo:** `components/layout/user-menu.tsx`

```tsx
'use client'

import { useAuth } from '@/hooks/use-auth'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { LogOut, Settings, User } from 'lucide-react'

const ROLE_LABELS: Record<string, string> = {
  viewer: 'Visualizador',
  operator: 'Operador',
  manager: 'Gestor',
  admin: 'Admin',
}

const ROLE_COLORS: Record<string, string> = {
  viewer: 'secondary',
  operator: 'default',
  manager: 'default',
  admin: 'destructive',
}

export function UserMenu() {
  const { dashboardUser, signOut, loading } = useAuth()

  if (loading || !dashboardUser) {
    return null
  }

  const initials = dashboardUser.nome
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-2 outline-none">
        <Avatar className="h-8 w-8">
          <AvatarImage src={dashboardUser.avatar_url || undefined} />
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        <div className="hidden md:block text-left">
          <p className="text-sm font-medium">{dashboardUser.nome}</p>
          <Badge variant={ROLE_COLORS[dashboardUser.role] as any} className="text-xs">
            {ROLE_LABELS[dashboardUser.role]}
          </Badge>
        </div>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium">{dashboardUser.nome}</p>
            <p className="text-xs text-muted-foreground">{dashboardUser.email}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem>
          <User className="mr-2 h-4 w-4" />
          Meu perfil
        </DropdownMenuItem>
        <DropdownMenuItem>
          <Settings className="mr-2 h-4 w-4" />
          Configurações
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={signOut} className="text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          Sair
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
```

**DoD:**
- [ ] Menu do usuário com avatar
- [ ] Badge de role visível
- [ ] Logout funcionando
- [ ] Responsivo (esconde nome no mobile)

---

## Migration Completa

```sql
-- =====================================================
-- DASHBOARD USERS E AUTH
-- Sprint 28: Dashboard Julia
-- =====================================================

-- Extensão para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabela de usuários do dashboard
CREATE TABLE IF NOT EXISTS dashboard_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_user_id UUID UNIQUE NOT NULL,
    email TEXT NOT NULL,
    nome TEXT NOT NULL,
    avatar_url TEXT,
    role TEXT NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('viewer', 'operator', 'manager', 'admin')),
    ativo BOOLEAN DEFAULT true,
    ultimo_acesso TIMESTAMPTZ,
    notificacoes_habilitadas BOOLEAN DEFAULT true,
    preferencias JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_dashboard_users_supabase
    ON dashboard_users(supabase_user_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_users_email
    ON dashboard_users(email);
CREATE INDEX IF NOT EXISTS idx_dashboard_users_role
    ON dashboard_users(role) WHERE ativo = true;

-- RLS
ALTER TABLE dashboard_users ENABLE ROW LEVEL SECURITY;

-- Políticas RLS
CREATE POLICY "Users can view own record" ON dashboard_users
    FOR SELECT USING (supabase_user_id = auth.uid());

CREATE POLICY "Admin can view all users" ON dashboard_users
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM dashboard_users
            WHERE supabase_user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admin can update users" ON dashboard_users
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM dashboard_users
            WHERE supabase_user_id = auth.uid() AND role = 'admin'
        )
    );

-- Trigger updated_at
CREATE TRIGGER update_dashboard_users_updated_at
    BEFORE UPDATE ON dashboard_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Função para criar usuário dashboard ao criar auth user
CREATE OR REPLACE FUNCTION handle_new_dashboard_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.dashboard_users (supabase_user_id, email, nome)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'name',
            NEW.raw_user_meta_data->>'full_name',
            split_part(NEW.email, '@', 1)
        )
    )
    ON CONFLICT (supabase_user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger para criar usuário
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_dashboard_user();

-- Inserir admin inicial (Rafael)
INSERT INTO dashboard_users (supabase_user_id, email, nome, role)
SELECT id, email, COALESCE(raw_user_meta_data->>'name', email), 'admin'
FROM auth.users
WHERE email = 'rafael@revoluna.com'
ON CONFLICT (supabase_user_id) DO UPDATE SET role = 'admin';
```

---

## Checklist Final

- [ ] Login email/senha funcionando
- [ ] Magic link funcionando
- [ ] Middleware protegendo rotas
- [ ] AuthProvider configurado
- [ ] useAuth hook funcionando
- [ ] hasPermission verificando roles
- [ ] RequireRole component
- [ ] UserMenu com logout
- [ ] Migration aplicada
- [ ] Admin inicial criado
