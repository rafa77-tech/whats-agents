# Dashboard CI/CD - Documentação Completa

> Documentação do pipeline de CI/CD implementado para o Julia Dashboard (Next.js/TypeScript).

## Visão Geral

O dashboard possui um pipeline de CI/CD completo seguindo as melhores práticas do mercado para projetos Next.js/TypeScript.

**Arquivo principal:** `.github/workflows/dashboard-ci.yml`

## Pipeline Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRIGGER                                   │
│  • Push para main/develop (paths: dashboard/**)                 │
│  • Pull Request para main (paths: dashboard/**)                 │
│  • Manual (workflow_dispatch)                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     JOB 1: INSTALL                               │
│  • Setup Node.js 20                                              │
│  • Cache node_modules (hash do package-lock.json)               │
│  • npm ci                                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ JOB 2:        │    │ JOB 3:        │    │ JOB 4:        │
│ TYPECHECK     │    │ LINT          │    │ FORMAT        │
│               │    │               │    │               │
│ • tsc --noEmit│    │ • ESLint      │    │ • Prettier    │
│ • Check 'any' │    │ • --max-warn 0│    │ • --check     │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └─────────┬──────────┘                    │
                  ▼                               │
        ┌─────────┴─────────┐                     │
        ▼                   ▼                     │
┌───────────────┐    ┌───────────────┐            │
│ JOB 5:        │    │ JOB 6:        │            │
│ UNIT TESTS    │    │ E2E TESTS     │            │
│               │    │               │            │
│ • Vitest      │    │ • Playwright  │            │
│ • RTL         │    │ • Chromium    │            │
│ • Coverage    │    │ • Screenshots │            │
└───────┬───────┘    └───────┬───────┘            │
        │                    │                    │
        └─────────┬──────────┘                    │
                  ▼                               │
        ┌───────────────────┐                     │
        │ JOB 7: BUILD      │                     │
        │                   │◄────────────────────┘
        │ • next build      │
        │ • Upload artifact │
        └─────────┬─────────┘
                  │
        ┌─────────┼─────────┐
        ▼                   ▼
┌───────────────┐    ┌───────────────┐
│ JOB 8:        │    │ JOB 9:        │
│ SECURITY      │    │ LIGHTHOUSE    │
│               │    │               │
│ • npm audit   │    │ • Performance │
│ • Secrets     │    │ • A11y        │
│   check       │    │ • SEO         │
└───────┬───────┘    └───────┬───────┘
        │                    │
        └─────────┬──────────┘
                  ▼
        ┌───────────────────┐
        │ JOB 10: DEPLOY    │  (apenas main)
        │                   │
        │ • Railway CLI     │
        │ • Health check    │
        └───────────────────┘
                  │
                  ▼
        ┌───────────────────┐
        │ JOB 11: BUNDLE    │  (apenas PRs)
        │ ANALYSIS          │
        │                   │
        │ • @next/bundle-   │
        │   analyzer        │
        └───────────────────┘
```

## Jobs Detalhados

### 1. Install

**Objetivo:** Instalar e cachear dependências.

- Restaura cache de node_modules
- Se cache miss: npm ci
- Gera cache-key para outros jobs

**Cache:** Baseado no hash de `package-lock.json`

### 2. TypeCheck

**Objetivo:** Validar tipos TypeScript.

- `tsc --noEmit`
- Verifica uso de 'any' (grep)
- Falha se houver erros de tipo

**Regras:**
- `strict: true` no tsconfig.json
- Zero tolerance para `any`

### 3. Lint

**Objetivo:** Verificar qualidade de código.

- `next lint --max-warnings 0`
- ESLint com regras strict

**Regras principais:**
- `@typescript-eslint/no-explicit-any: error`
- `@typescript-eslint/no-unsafe-*: error`
- Import ordering
- Accessibility (jsx-a11y)

### 4. Format

**Objetivo:** Verificar formatação.

- `prettier --check`

**Config:** `.prettierrc.json` com Tailwind plugin

### 5. Unit Tests

**Objetivo:** Testes unitários de componentes.

- Vitest com jsdom
- React Testing Library
- Coverage report

**Thresholds de cobertura:**
- Statements: 70%
- Branches: 70%
- Functions: 70%
- Lines: 70%

### 6. E2E Tests

**Objetivo:** Testes end-to-end.

- Playwright com Chromium
- Build da aplicação
- Screenshots on failure
- Traces on retry

**URLs testadas:**
- `/` (homepage)
- `/login`

### 7. Build

**Objetivo:** Verificar build de produção.

- `next build`
- Cache de .next/cache
- Upload de artifacts

**Config:**
- `output: 'standalone'` para Railway
- TypeScript errors = build fail
- ESLint errors = build fail

### 8. Security

**Objetivo:** Auditoria de segurança.

- `npm audit --audit-level=high`
- Grep por secrets no código

**Verifica:**
- Vulnerabilidades em dependências
- SUPABASE_SERVICE_KEY no código
- ANTHROPIC_API_KEY no código

### 9. Lighthouse CI

**Objetivo:** Métricas de performance e qualidade.

- 3 runs por URL (média)
- Performance, A11y, SEO, Best Practices
- Core Web Vitals

**Thresholds:**

| Categoria | Mínimo | Ação |
|-----------|--------|------|
| Performance | 70% | warn |
| Accessibility | 90% | error |
| Best Practices | 80% | warn |
| SEO | 80% | warn |

**Core Web Vitals:**

| Métrica | Máximo |
|---------|--------|
| FCP | 2000ms |
| LCP | 2500ms |
| CLS | 0.1 |
| TBT | 300ms |
| TTI | 3500ms |

### 10. Deploy

**Objetivo:** Deploy para Railway.

- Apenas em push para main
- Railway CLI
- Health check após deploy

**Condições:**
- Branch: main
- Event: push
- Secrets: RAILWAY_TOKEN

### 11. Bundle Analysis

**Objetivo:** Análise de tamanho do bundle.

- Apenas em PRs
- @next/bundle-analyzer
- Upload de relatório

## Arquivos de Configuração

| Arquivo | Descrição |
|---------|-----------|
| `.github/workflows/dashboard-ci.yml` | Pipeline principal |
| `dashboard/tsconfig.json` | TypeScript strict |
| `dashboard/.eslintrc.json` | ESLint strict |
| `dashboard/.prettierrc.json` | Prettier + Tailwind |
| `dashboard/vitest.config.ts` | Vitest + coverage |
| `dashboard/playwright.config.ts` | Playwright E2E |
| `dashboard/lighthouserc.js` | Lighthouse CI |

## Secrets do GitHub

| Secret | Descrição | Status |
|--------|-----------|--------|
| `RAILWAY_TOKEN` | Token para deploy | ✅ Configurado |
| `RAILWAY_PROJECT_ID` | ID do projeto | ✅ Configurado |
| `RAILWAY_APP_URL` | URL da API | ✅ Configurado |
| `SUPABASE_URL` | URL Supabase | ✅ Configurado |
| `SUPABASE_SERVICE_KEY` | Service key | ✅ Configurado |
| `ANTHROPIC_API_KEY` | API Anthropic | ✅ Configurado |
| `LHCI_GITHUB_APP_TOKEN` | Lighthouse CI | ✅ Configurado |

## Comandos Locais

```bash
cd dashboard

# Validação completa (igual ao CI)
npm run validate

# Rodar jobs individuais
npm run type-check      # Job: typecheck
npm run lint            # Job: lint
npm run format:check    # Job: format
npm run test:ci         # Job: unit-tests
npm run test:e2e        # Job: e2e-tests
npm run build           # Job: build

# Lighthouse local
npm install -g @lhci/cli
npm run build && lhci autorun

# Bundle analysis
ANALYZE=true npm run build
```

## O que é um PR (Pull Request)?

Um **Pull Request** é uma solicitação para mesclar código de um branch para outro:

```
1. Criar branch:     git checkout -b minha-feature
2. Fazer mudanças:   (editar arquivos)
3. Commitar:         git add . && git commit -m "feat: ..."
4. Push:             git push origin minha-feature
5. Abrir PR:         No GitHub, "Compare & pull request"
6. CI roda:          Todos os jobs do pipeline
7. Review:           Alguém aprova (ou você mesmo)
8. Merge:            Mescla para main
```

**Benefícios:**
- CI valida código antes de ir para main
- Histórico de mudanças documentado
- Review de código por outros
- Rollback fácil se der problema

## Troubleshooting

### TypeCheck falha com "any"

```typescript
// Errado
const data: any = await fetch(...)

// Correto
const data: unknown = await fetch(...)
if (isValidData(data)) {
  // usar data tipado
}
```

### Lint falha com import order

```typescript
// Ordem correta:
import { useState } from 'react'        // 1. React
import { useRouter } from 'next/router' // 2. Next
import { Button } from '@/components'   // 3. Internal
import type { User } from '@/types'     // 4. Types
```

### Lighthouse score baixo

1. Verificar bundle: `ANALYZE=true npm run build`
2. Lazy load componentes pesados
3. Otimizar imagens com `next/image`
4. Verificar Core Web Vitals no DevTools

## Referências

- [Next.js Docs](https://nextjs.org/docs)
- [Vitest](https://vitest.dev/)
- [Playwright](https://playwright.dev/)
- [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci)
- [ESLint TypeScript](https://typescript-eslint.io/)
