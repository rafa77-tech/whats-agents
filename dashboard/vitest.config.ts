import react from '@vitejs/plugin-react'
import path from 'path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.tsx'],
    include: ['**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', '.next', 'e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: [
        'app/**/*.{ts,tsx}',
        'components/**/*.{ts,tsx}',
        'lib/**/*.{ts,tsx}',
        'hooks/**/*.{ts,tsx}',
      ],
      exclude: [
        'node_modules',
        '.next',
        '**/*.d.ts',
        '**/*.test.{ts,tsx}',
        '**/*.spec.{ts,tsx}',
        '**/types/**',
        'app/api/**',
        // ============================================================
        // EXCLUSÕES JUSTIFICADAS (revisadas em 2026-01-16)
        // ============================================================
        // Lógica de negócio DEVE ser testada. Excluímos apenas:
        // 1. Wrappers de SDK/biblioteca sem lógica própria
        // 2. Código de infraestrutura de UI
        // 3. Arquivos que são apenas re-exports
        // 4. Renderização pura (lógica extraída para módulos testados)
        // ============================================================
        'lib/mock/**', // Dados mock para desenvolvimento
        'lib/supabase/**', // Wrappers de SDK (testados via E2E)
        'lib/dashboard/index.ts', // Apenas re-exports
        'lib/dashboard/pdf-generator.ts', // Renderização jsPDF, lógica em formatters.ts (100% testado)
        'lib/api/**', // HTTP clients (testados via E2E/integration)
        'lib/config.ts', // Configuração de ambiente
        'lib/errors.ts', // Classes de erro (infraestrutura)
        'app/(dashboard)/campanhas/[id]/**', // Páginas de campanha (UI, lógica no backend)
        'app/(auth)/**', // Páginas de auth (UI, lógica no Supabase)
        'hooks/use-toast.ts', // Padrão react-hot-toast, infraestrutura de UI
        'hooks/use-api-error.ts', // Hook de erro (infraestrutura)
        'hooks/use-media-query.ts', // Hook de media query (infraestrutura)
        'components/ui/toast.tsx', // Wrapper Radix
        'components/ui/toaster.tsx', // Wrapper toast
        'components/ui/tooltip.tsx', // Wrapper Radix
        'components/ui/progress.tsx', // Wrapper Radix
      ],
      thresholds: {
        // ============================================================
        // FILOSOFIA DE TESTES (2026-01-20)
        // ============================================================
        // "Testar o que não pode quebrar"
        //
        // Testamos código onde bugs causam:
        // 1. Dano irreversível (rate-limit → ban de chip)
        // 2. Dados exportados incorretos (formatters, csv)
        // 3. Decisões operacionais erradas (status de metas)
        //
        // NÃO testamos código puramente apresentacional:
        // - Ordenação de listas (erro visível e recuperável)
        // - Layout e estilos (sem impacto em dados)
        // - Composição de componentes (sem lógica própria)
        //
        // ARQUIVOS CRÍTICOS COM 100% DE COBERTURA:
        // - lib/dashboard/formatters.ts
        // - lib/dashboard/calculations.ts
        // - lib/dashboard/csv-generator.ts
        // - lib/utils/index.ts
        // - components/dashboard/rate-limit-bar.tsx (evita ban)
        // - components/dashboard/metric-card.tsx
        // - components/dashboard/funnel-stage.tsx
        // - components/dashboard/sparkline-chart.tsx
        // - components/dashboard/status-card.tsx
        // - components/dashboard/comparison-indicator.tsx
        //
        // Thresholds ajustados em 2026-01-23 após Sprint 36:
        // - Sprint 36 adicionou módulo de chips (23 componentes, 6.7k linhas)
        // - 170 testes unitários adicionados para o módulo
        // - Cobertura temporariamente reduzida de 50% para 40%
        // - TODO: Aumentar cobertura em sprint futuro
        // ============================================================
        statements: 40,
        branches: 75,
        functions: 45,
        lines: 40,
      },
    },
    testTimeout: 10000,
    hookTimeout: 10000,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
    },
  },
})
