# E15: QA Mobile + Polish

**Épico:** Testes Mobile + Ajustes Finais + Deploy
**Estimativa:** 6h
**Prioridade:** P0 (Bloqueante para release)
**Dependências:** Todos os épicos anteriores

---

## Objetivo

Garantir qualidade da experiência mobile e finalizar o dashboard:
- Testes em múltiplos dispositivos
- Ajustes de responsividade
- Performance optimization
- Acessibilidade
- Deploy final

---

## Stories

### S15.1: Checklist de Testes Mobile

**Dispositivos para teste:**

| Dispositivo | Viewport | Prioridade |
|-------------|----------|------------|
| iPhone SE | 375x667 | P0 |
| iPhone 14 | 390x844 | P0 |
| iPhone 14 Pro Max | 430x932 | P1 |
| Samsung Galaxy S21 | 360x800 | P0 |
| iPad Mini | 768x1024 | P1 |
| iPad Pro | 1024x1366 | P2 |

**Checklist por página:**

```markdown
## Dashboard Principal
- [ ] Cards de status responsivos
- [ ] Gráficos redimensionam corretamente
- [ ] Lista de atividades scroll suave
- [ ] Touch targets >= 44px

## Conversas
- [ ] Lista de conversas scroll infinito
- [ ] Cards não cortam texto
- [ ] Filtros em sheet mobile
- [ ] Detalhe da conversa fullscreen
- [ ] Bubbles de mensagem não overflow
- [ ] Ações de handoff acessíveis

## Médicos
- [ ] Lista com cards compactos
- [ ] Perfil tabs funcionando
- [ ] Timeline scroll suave
- [ ] Ações acessíveis

## Vagas
- [ ] Toggle lista/calendário
- [ ] Calendário navegável touch
- [ ] Formulário em múltiplas etapas
- [ ] Cards informativos

## Métricas
- [ ] KPI cards em grid 2x2
- [ ] Gráficos touch-friendly
- [ ] Date picker mobile
- [ ] Scroll horizontal se necessário

## Campanhas
- [ ] Lista com progresso visível
- [ ] Formulário em steps
- [ ] Selector de audiência usável

## Sistema
- [ ] Toggle Julia touch-friendly
- [ ] Sliders funcionando
- [ ] Feature flags scroll

## Notificações
- [ ] Bell menu responsivo
- [ ] Push permission banner
- [ ] Itens clicáveis

## Auditoria
- [ ] Lista compacta
- [ ] Filtros em sheet
- [ ] Detalhes expandíveis
```

---

### S15.2: Ajustes de Responsividade

**Arquivo:** `app/globals.css` (adicionar)

```css
/* Mobile touch improvements */
@media (max-width: 768px) {
  /* Larger touch targets */
  .touch-target {
    min-height: 44px;
    min-width: 44px;
  }

  /* Prevent zoom on input focus (iOS) */
  input, select, textarea {
    font-size: 16px !important;
  }

  /* Smooth scrolling */
  .scroll-container {
    -webkit-overflow-scrolling: touch;
  }

  /* Hide scrollbars but keep functionality */
  .hide-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }

  /* Safe area for notch devices */
  .safe-area-top {
    padding-top: env(safe-area-inset-top);
  }
  .safe-area-bottom {
    padding-bottom: env(safe-area-inset-bottom);
  }
}

/* Prevent content shift on scrollbar */
html {
  scrollbar-gutter: stable;
}

/* Focus states for accessibility */
:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

### S15.3: Performance Optimization

**Checklist de performance:**

```markdown
## Bundle Size
- [ ] Verificar bundle size com `npm run analyze`
- [ ] Code splitting por rota
- [ ] Dynamic imports para gráficos
- [ ] Tree shaking de Lucide icons

## Images
- [ ] next/image para todas imagens
- [ ] Formatos modernos (WebP)
- [ ] Lazy loading

## Data Fetching
- [ ] React Query com cache
- [ ] Prefetch de rotas comuns
- [ ] Skeleton loading states
- [ ] Error boundaries

## Runtime
- [ ] Memoização de componentes pesados
- [ ] Virtualização de listas longas
- [ ] Debounce em inputs de busca
```

**Arquivo:** `next.config.js` (otimizações)

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // Bundle analyzer
  ...(process.env.ANALYZE === 'true' && {
    webpack: (config, { isServer }) => {
      if (!isServer) {
        const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer')
        config.plugins.push(
          new BundleAnalyzerPlugin({
            analyzerMode: 'static',
            openAnalyzer: true,
          })
        )
      }
      return config
    },
  }),

  // Image optimization
  images: {
    formats: ['image/avif', 'image/webp'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.supabase.co',
      },
    ],
  },

  // Headers for caching
  async headers() {
    return [
      {
        source: '/:all*(svg|jpg|png|webp|avif)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ]
  },
}

module.exports = nextConfig
```

---

### S15.4: Acessibilidade

**Checklist de acessibilidade:**

```markdown
## Semântica
- [ ] Headings hierárquicos (h1 > h2 > h3)
- [ ] Landmarks (main, nav, aside)
- [ ] Labels em todos inputs
- [ ] Alt text em imagens

## Navegação
- [ ] Skip link para conteúdo principal
- [ ] Focus trap em modals
- [ ] Keyboard navigation funcional
- [ ] Focus visible states

## ARIA
- [ ] aria-labels em botões de ícone
- [ ] aria-expanded em dropdowns
- [ ] aria-live para updates dinâmicos
- [ ] role="alert" para mensagens de erro

## Contraste
- [ ] Ratio mínimo 4.5:1 para texto
- [ ] Ratio mínimo 3:1 para elementos UI
- [ ] Dark mode com contraste adequado
```

**Arquivo:** `components/ui/skip-link.tsx`

```typescript
export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded"
    >
      Pular para conteúdo principal
    </a>
  )
}
```

---

### S15.5: Deploy Final

**Checklist de deploy:**

```markdown
## Pré-deploy
- [ ] Todos os testes passando
- [ ] Build sem erros ou warnings
- [ ] Variáveis de ambiente configuradas no Railway
- [ ] SSL/HTTPS configurado
- [ ] CORS configurado no backend

## Railway Configuration
- [ ] Service: dashboard
- [ ] Root Directory: /dashboard
- [ ] Build Command: npm run build
- [ ] Start Command: npm run start
- [ ] Health Check: /api/health

## Variáveis de Ambiente
- [ ] NEXT_PUBLIC_SUPABASE_URL
- [ ] NEXT_PUBLIC_SUPABASE_ANON_KEY
- [ ] NEXT_PUBLIC_API_URL
- [ ] NEXT_PUBLIC_APP_URL
- [ ] NEXT_PUBLIC_VAPID_PUBLIC_KEY

## Pós-deploy
- [ ] Smoke test em produção
- [ ] Login/logout funcionando
- [ ] Páginas principais carregando
- [ ] Notificações push funcionando
- [ ] Mobile responsive em produção
```

**Arquivo:** `app/api/health/route.ts`

```typescript
import { NextResponse } from 'next/server'

export async function GET() {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.NEXT_PUBLIC_VERSION || '1.0.0',
    environment: process.env.NODE_ENV
  }

  return NextResponse.json(health)
}
```

---

### S15.6: Smoke Tests

**Arquivo:** `tests/smoke.spec.ts` (Playwright)

```typescript
import { test, expect } from '@playwright/test'

test.describe('Smoke Tests', () => {
  test('should load login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page).toHaveTitle(/Julia Dashboard/)
    await expect(page.getByRole('button', { name: /entrar/i })).toBeVisible()
  })

  test('should redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/login/)
  })

  test('should display dashboard after login', async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('[name="email"]', process.env.TEST_EMAIL!)
    await page.fill('[name="password"]', process.env.TEST_PASSWORD!)
    await page.click('button[type="submit"]')

    // Verificar dashboard
    await expect(page).toHaveURL('/')
    await expect(page.getByText('Dashboard')).toBeVisible()
  })

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/login')

    // Bottom nav should be visible on mobile
    await expect(page.getByRole('navigation')).toBeVisible()
  })
})
```

---

## Definition of Done

### Épico completo quando:

- [ ] **Mobile First**
  - [ ] Todas as páginas testadas em 375px
  - [ ] Touch targets >= 44px
  - [ ] Sem overflow horizontal
  - [ ] Scroll suave

- [ ] **Performance**
  - [ ] Lighthouse mobile >= 80
  - [ ] First Contentful Paint < 2s
  - [ ] Time to Interactive < 4s

- [ ] **Acessibilidade**
  - [ ] WCAG 2.1 AA compliance
  - [ ] Navegação por teclado
  - [ ] Screen reader friendly

- [ ] **Qualidade**
  - [ ] Sem erros no console
  - [ ] Sem warnings de TypeScript
  - [ ] Build sem erros

- [ ] **Deploy**
  - [ ] Rodando em produção
  - [ ] Health check passando
  - [ ] Métricas de erro < 1%

---

## Checklist Final Sprint 28

```markdown
## Épicos Completos
- [ ] E01: Setup Frontend ✓
- [ ] E02: Autenticação ✓
- [ ] E03: Layout Responsivo ✓
- [ ] E04: APIs Backend ✓
- [ ] E05: Dashboard Principal ✓
- [ ] E06: Painel de Controle ✓
- [ ] E07: Sistema de Notificações ✓
- [ ] E08: Gestão de Conversas ✓
- [ ] E09: Gestão de Médicos ✓
- [ ] E10: Gestão de Vagas ✓
- [ ] E11: Métricas e Analytics ✓
- [ ] E12: Sistema de Campanhas ✓
- [ ] E13: Auditoria e Logs ✓
- [ ] E14: Preview Pool Chips ✓
- [ ] E15: QA Mobile + Polish ✓

## Entregáveis
- [ ] Dashboard funcional em produção
- [ ] Documentação de uso
- [ ] Treinamento da equipe
```
