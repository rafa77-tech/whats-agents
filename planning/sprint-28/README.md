# Sprint 28: Dashboard Julia + Painel de Controle

**Status:** Planejado
**Inicio:** A definir (após Sprint 25/26)
**Estimativa:** 3-4 semanas
**Dependencias:** Nenhuma (pode rodar em paralelo com Sprint 25/26)

---

## Objetivo

Construir o **Dashboard completo da Julia** com:
- Visualização de métricas e KPIs em tempo real
- Painel de controle operacional (substituindo/complementando Slack)
- Gestão de médicos, vagas e campanhas
- Sistema de notificações push no browser
- Experiência mobile-first responsiva
- Auditoria completa de operações

### Decisões de Arquitetura

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Hosting Frontend | Railway | Manter tudo no mesmo lugar |
| Autenticação | Supabase Auth | Já temos Supabase |
| Framework | Next.js 14 (App Router) | SSR, performance, DX |
| UI Components | shadcn/ui + Tailwind | Mobile-first, acessível |
| Charts | Tremor | Componentes dashboard prontos |
| Real-time | Supabase Realtime | Updates automáticos |
| Notificações | Web Push API | Push nativo no browser |
| Mobile | Responsivo obrigatório | PWA no futuro |

### Relação com Slack

- Dashboard **complementa** Slack, não substitui
- Mesmas funcionalidades disponíveis em ambos
- Slack continua funcionando normalmente
- Deprecation do Slack será decidido futuramente

---

## Stack Técnico

### Frontend

```
/dashboard
├── app/                    # Next.js App Router
│   ├── (auth)/            # Rotas de autenticação
│   │   ├── login/
│   │   └── callback/
│   ├── (dashboard)/       # Rotas protegidas
│   │   ├── page.tsx       # Dashboard principal
│   │   ├── conversas/
│   │   ├── medicos/
│   │   ├── vagas/
│   │   ├── campanhas/
│   │   ├── metricas/
│   │   ├── sistema/
│   │   └── auditoria/
│   ├── api/               # API routes (BFF)
│   └── layout.tsx
├── components/
│   ├── ui/                # shadcn/ui components
│   ├── dashboard/         # Componentes específicos
│   └── charts/            # Gráficos
├── lib/
│   ├── supabase/          # Client Supabase
│   ├── api/               # Chamadas ao backend FastAPI
│   └── utils/
├── hooks/                 # Custom hooks
└── types/                 # TypeScript types
```

### Backend (Extensão FastAPI)

```
/app/api/routes/
├── dashboard/             # Novos endpoints
│   ├── __init__.py
│   ├── status.py          # Status geral
│   ├── metricas.py        # Métricas agregadas
│   ├── conversas.py       # CRUD conversas
│   ├── medicos.py         # CRUD médicos
│   ├── vagas.py           # CRUD vagas
│   ├── campanhas.py       # CRUD campanhas
│   ├── sistema.py         # Controles operacionais
│   └── auditoria.py       # Logs e auditoria
```

---

## Épicos (Ordenados por Dependência)

### Fase 1: Foundation (Semana 1)

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E01 | Setup Projeto Frontend | Next.js + Tailwind + shadcn/ui + Railway | 6h |
| E02 | Autenticação Supabase | Login + RBAC + Middleware | 6h |
| E03 | Layout Base Responsivo | Sidebar + Header + Mobile nav | 6h |
| E04 | APIs Backend Base | Estrutura + Auth middleware + CORS | 4h |

### Fase 2: Core Dashboard (Semana 1-2)

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E05 | Dashboard Principal | Cards status + métricas + atividade | 8h |
| E06 | Painel de Controle | Toggle Julia + Flags + Rate Limit | 8h |
| E07 | Sistema de Notificações | Web Push + Toast + Realtime | 6h |

### Fase 3: Gestão (Semana 2-3)

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E08 | Gestão de Conversas | Lista + detalhes + ações | 8h |
| E09 | Gestão de Médicos | CRUD + busca + perfil | 8h |
| E10 | Gestão de Vagas | CRUD + filtros + status | 6h |

### Fase 4: Analytics & Campanhas (Semana 3)

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E11 | Métricas e Analytics | Gráficos + funil + tendências | 10h |
| E12 | Sistema de Campanhas | Lista + wizard + execução | 10h |

### Fase 5: Auditoria & Polish (Semana 3-4)

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E13 | Auditoria e Logs | Timeline + filtros + export | 6h |
| E14 | Preview Pool Chips | Visualização status (Sprint 25/26) | 4h |
| E15 | QA Mobile + Polish | Testes responsivos + ajustes UX | 6h |

**Total Estimado:** ~102h (3-4 semanas)

---

## Ordenação e Dependências

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEPENDÊNCIAS ENTRE ÉPICOS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   E01 (Setup) ────────────────────────────────────────────────────────────┐ │
│        │                                                                   │ │
│        ├──► E02 (Auth) ──► E03 (Layout) ──────────────────────────────┐   │ │
│        │                        │                                      │   │ │
│        └──► E04 (APIs) ─────────┼──────────────────────────────────┐  │   │ │
│                                 │                                   │  │   │ │
│                                 ▼                                   │  │   │ │
│                          ┌─────────────┐                           │  │   │ │
│                          │ E05 (Dash)  │◄──────────────────────────┘  │   │ │
│                          └──────┬──────┘                              │   │ │
│                                 │                                      │   │ │
│              ┌──────────────────┼──────────────────┐                  │   │ │
│              │                  │                  │                  │   │ │
│              ▼                  ▼                  ▼                  │   │ │
│      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │   │ │
│      │ E06 (Control)│  │ E07 (Notif) │  │ E08 (Convers)│            │   │ │
│      └──────────────┘  └──────────────┘  └──────┬───────┘            │   │ │
│                                                  │                    │   │ │
│                                   ┌──────────────┼──────────────┐    │   │ │
│                                   │              │              │    │   │ │
│                                   ▼              ▼              ▼    │   │ │
│                           ┌────────────┐ ┌────────────┐ ┌──────────┐│   │ │
│                           │E09 (Médico)│ │E10 (Vagas) │ │E11 (Métr)││   │ │
│                           └────────────┘ └────────────┘ └──────────┘│   │ │
│                                                  │                   │   │ │
│                                                  ▼                   │   │ │
│                                          ┌─────────────┐             │   │ │
│                                          │E12 (Campan) │             │   │ │
│                                          └──────┬──────┘             │   │ │
│                                                 │                    │   │ │
│                              ┌──────────────────┼────────────────┐   │   │ │
│                              │                  │                │   │   │ │
│                              ▼                  ▼                ▼   │   │ │
│                       ┌────────────┐    ┌────────────┐   ┌─────────┐│   │ │
│                       │E13 (Audit) │    │E14 (Chips) │   │E15 (QA) ││   │ │
│                       └────────────┘    └────────────┘   └─────────┘│   │ │
│                                                                      │   │ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Níveis de Acesso (RBAC)

### Roles

| Role | Descrição | Quem |
|------|-----------|------|
| `viewer` | Apenas visualização | Estagiários, observadores |
| `operator` | Visualização + controles básicos | Escalistas, operação |
| `manager` | Tudo + edição de dados | Gestores, coordenadores |
| `admin` | Acesso total + auditoria | Rafael, tech leads |

### Permissões por Role

| Funcionalidade | viewer | operator | manager | admin |
|----------------|--------|----------|---------|-------|
| Ver dashboard | ✅ | ✅ | ✅ | ✅ |
| Ver métricas | ✅ | ✅ | ✅ | ✅ |
| Ver conversas | ✅ | ✅ | ✅ | ✅ |
| Pausar/Retomar Julia | ❌ | ✅ | ✅ | ✅ |
| Toggle feature flags | ❌ | ✅ | ✅ | ✅ |
| Enviar mensagem manual | ❌ | ✅ | ✅ | ✅ |
| Criar/editar médico | ❌ | ❌ | ✅ | ✅ |
| Criar/editar vaga | ❌ | ❌ | ✅ | ✅ |
| Criar/executar campanha | ❌ | ❌ | ✅ | ✅ |
| Editar diretrizes | ❌ | ❌ | ✅ | ✅ |
| Ver auditoria completa | ❌ | ❌ | ❌ | ✅ |
| Gerenciar usuários | ❌ | ❌ | ❌ | ✅ |
| Configurações sistema | ❌ | ❌ | ❌ | ✅ |

### Implementação

```sql
-- Tabela de usuários dashboard
CREATE TABLE dashboard_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_user_id UUID UNIQUE NOT NULL,
    email TEXT NOT NULL,
    nome TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('viewer', 'operator', 'manager', 'admin')),
    ativo BOOLEAN DEFAULT true,
    ultimo_acesso TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Log de ações para auditoria
CREATE TABLE dashboard_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES dashboard_users(id),
    acao TEXT NOT NULL,
    recurso TEXT NOT NULL,
    recurso_id TEXT,
    dados_antes JSONB,
    dados_depois JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Sistema de Notificações

### Tipos de Notificação

| Tipo | Severidade | Exemplo | Push? |
|------|------------|---------|-------|
| `critical` | 🔴 Crítico | Julia parou, ban detectado | Sim |
| `warning` | 🟠 Atenção | Trust caindo, handoff pendente | Sim |
| `info` | 🔵 Info | Plantão confirmado, meta atingida | Não |
| `success` | 🟢 Sucesso | Campanha concluída | Não |

### Implementação

```typescript
// Push Notification Service
interface Notification {
  id: string;
  type: 'critical' | 'warning' | 'info' | 'success';
  title: string;
  message: string;
  action_url?: string;
  created_at: Date;
  read: boolean;
}

// Supabase Realtime subscription
const channel = supabase
  .channel('dashboard-notifications')
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'dashboard_notifications'
  }, handleNewNotification)
  .subscribe();

// Web Push API
async function sendPushNotification(notification: Notification) {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(notification.title, {
      body: notification.message,
      icon: '/icons/julia-icon.png',
      badge: '/icons/badge.png',
      tag: notification.id,
    });
  }
}
```

### Tabela de Notificações

```sql
CREATE TABLE dashboard_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES dashboard_users(id), -- NULL = todos
    tipo TEXT NOT NULL CHECK (tipo IN ('critical', 'warning', 'info', 'success')),
    titulo TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    action_url TEXT,
    lida BOOLEAN DEFAULT false,
    lida_em TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índice para busca de não lidas
CREATE INDEX idx_notifications_unread ON dashboard_notifications(user_id, lida, created_at DESC)
    WHERE lida = false;
```

---

## Mobile-First Design

### Breakpoints

```css
/* Tailwind breakpoints padrão */
sm: 640px   /* Mobile landscape */
md: 768px   /* Tablet */
lg: 1024px  /* Desktop */
xl: 1280px  /* Large desktop */
2xl: 1536px /* Extra large */
```

### Padrões Mobile

1. **Bottom Navigation** - Navegação principal no mobile fica embaixo
2. **Drawer Pattern** - Sidebar vira drawer no mobile
3. **Touch Targets** - Mínimo 44x44px para botões
4. **Pull to Refresh** - Atualizar dados puxando para baixo
5. **Swipe Actions** - Ações rápidas com swipe
6. **Skeleton Loading** - Placeholders durante carregamento

### Componentes Responsivos

```tsx
// Exemplo: Layout responsivo
<div className="flex flex-col lg:flex-row min-h-screen">
  {/* Sidebar - hidden on mobile, drawer on demand */}
  <aside className="hidden lg:block lg:w-64 lg:flex-shrink-0">
    <Sidebar />
  </aside>

  {/* Mobile bottom nav */}
  <nav className="fixed bottom-0 left-0 right-0 lg:hidden z-50">
    <BottomNavigation />
  </nav>

  {/* Main content */}
  <main className="flex-1 pb-16 lg:pb-0">
    {children}
  </main>
</div>
```

---

## Entregáveis por Semana

### Semana 1

**Objetivo:** Setup completo + Dashboard básico funcionando

- [x] E01: Setup Next.js + Railway deploy
- [x] E02: Login Supabase funcionando
- [x] E03: Layout responsivo com sidebar/bottom nav
- [x] E04: APIs de status e métricas básicas
- [x] E05: Dashboard principal com cards

**Entregável:** Login → Dashboard com métricas do dia

### Semana 2

**Objetivo:** Controles operacionais + Gestão básica

- [x] E06: Painel de controle completo
- [x] E07: Sistema de notificações
- [x] E08: Lista e detalhes de conversas

**Entregável:** Pausar Julia, toggle flags, ver conversas

### Semana 3

**Objetivo:** Gestão completa + Analytics

- [x] E09: CRUD de médicos
- [x] E10: CRUD de vagas
- [x] E11: Dashboard de métricas
- [x] E12: Sistema de campanhas

**Entregável:** Gestão completa de médicos, vagas, campanhas

### Semana 4

**Objetivo:** Auditoria + Polish + Deploy final

- [x] E13: Logs de auditoria
- [x] E14: Preview de chips (se Sprint 25 pronta)
- [x] E15: QA mobile + ajustes finais

**Entregável:** Versão completa em produção

---

## Checklist de Qualidade

### Performance

- [ ] Lighthouse score > 90 (mobile)
- [ ] First Contentful Paint < 1.5s
- [ ] Time to Interactive < 3s
- [ ] Bundle size < 200kb (gzipped)

### Acessibilidade

- [ ] WCAG 2.1 AA compliance
- [ ] Keyboard navigation completa
- [ ] Screen reader friendly
- [ ] Color contrast adequado

### Mobile

- [ ] Funciona em telas 320px+
- [ ] Touch targets 44x44px mínimo
- [ ] Sem horizontal scroll
- [ ] Pull to refresh implementado
- [ ] PWA installable

### Segurança

- [ ] HTTPS obrigatório
- [ ] CSP headers configurados
- [ ] Rate limiting nas APIs
- [ ] Audit log de ações sensíveis
- [ ] Sessões com timeout

---

## APIs Backend (Resumo)

### Endpoints Novos

```
# Status e controle
GET  /api/v1/dashboard/status          # Status geral do sistema
POST /api/v1/dashboard/julia/pause     # Pausar Julia
POST /api/v1/dashboard/julia/resume    # Retomar Julia
GET  /api/v1/dashboard/flags           # Listar feature flags
POST /api/v1/dashboard/flags/{name}    # Toggle feature flag

# Métricas
GET  /api/v1/dashboard/metrics/summary # Resumo do período
GET  /api/v1/dashboard/metrics/funnel  # Funil de vendas
GET  /api/v1/dashboard/metrics/trends  # Tendências temporais

# Conversas
GET  /api/v1/dashboard/conversations          # Listar conversas
GET  /api/v1/dashboard/conversations/{id}     # Detalhes conversa
POST /api/v1/dashboard/conversations/{id}/message  # Enviar mensagem

# Médicos
GET    /api/v1/dashboard/doctors              # Listar médicos
GET    /api/v1/dashboard/doctors/{id}         # Detalhes médico
POST   /api/v1/dashboard/doctors              # Criar médico
PUT    /api/v1/dashboard/doctors/{id}         # Atualizar médico
DELETE /api/v1/dashboard/doctors/{id}         # Deletar médico

# Vagas
GET    /api/v1/dashboard/jobs                 # Listar vagas
GET    /api/v1/dashboard/jobs/{id}            # Detalhes vaga
POST   /api/v1/dashboard/jobs                 # Criar vaga
PUT    /api/v1/dashboard/jobs/{id}            # Atualizar vaga
DELETE /api/v1/dashboard/jobs/{id}            # Deletar vaga

# Campanhas
GET    /api/v1/dashboard/campaigns            # Listar campanhas
GET    /api/v1/dashboard/campaigns/{id}       # Detalhes campanha
POST   /api/v1/dashboard/campaigns            # Criar campanha
POST   /api/v1/dashboard/campaigns/{id}/execute  # Executar campanha

# Auditoria
GET  /api/v1/dashboard/audit/logs             # Logs de auditoria
GET  /api/v1/dashboard/audit/export           # Exportar logs

# Notificações
GET  /api/v1/dashboard/notifications          # Listar notificações
POST /api/v1/dashboard/notifications/{id}/read # Marcar como lida
```

---

## Riscos e Mitigações

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| Railway pricing aumentar | Médio | Baixa | Monitorar uso, ter backup Vercel |
| Performance mobile ruim | Alto | Média | Lighthouse CI, testes em devices |
| Supabase Auth issues | Alto | Baixa | Fallback para magic links |
| Escopo creep | Alto | Alta | Priorização rígida, MVP first |
| Mobile UX complexa | Médio | Média | Design review constante |

---

## Próximos Passos

1. **Criar épicos detalhados** - Cada épico terá seu próprio arquivo
2. **Setup do projeto** - Iniciar E01
3. **Deploy Railway** - Configurar CI/CD
4. **Design system** - Definir componentes base

---

*Sprint criada em 31/12/2025*
