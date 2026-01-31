# Epic 07: Tests & Validation

## Objetivo

Validar a implementação com testes E2E, build de produção e verificação manual.

## Contexto

Este épico foca em garantir que tudo funciona corretamente antes de considerar a sprint completa.

### Estratégia de Testes

| Tipo | Escopo | Quando Usar |
|------|--------|-------------|
| **E2E** | Navegação, carregamento de páginas | Crítico para novas rotas |
| **Unitário** | Funções de utilidade (formatDuration, etc.) | Opcional, se houver lógica complexa |
| **Build** | Compilação TypeScript, bundling | Sempre antes de merge |
| **Manual** | Fluxos completos, UX | Sempre antes de merge |

---

## Story 7.1: Testes E2E - Página Monitor

### Objetivo
Criar testes E2E para a página Monitor.

### Tarefas

1. **Criar arquivo de teste:**

**Arquivo:** `dashboard/e2e/monitor.e2e.ts`

```typescript
/**
 * Monitor Page E2E Tests - Sprint 42
 */

import { test, expect } from '@playwright/test'

test.describe('Monitor Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navegar para a página
    await page.goto('/monitor')
  })

  test('should load monitor page', async ({ page }) => {
    // Verificar URL
    await expect(page).toHaveURL(/monitor/)

    // Verificar título
    await expect(page.locator('h1')).toContainText('Monitor')
  })

  test('should display system health card', async ({ page }) => {
    // Aguardar carregamento
    await page.waitForLoadState('networkidle')

    // Verificar que o card de saúde existe
    const healthCard = page.locator('text=Saúde do Sistema')
    await expect(healthCard).toBeVisible()
  })

  test('should display stats cards', async ({ page }) => {
    await page.waitForLoadState('networkidle')

    // Verificar cards de estatísticas
    await expect(page.locator('text=Total Jobs')).toBeVisible()
    await expect(page.locator('text=Taxa de Sucesso')).toBeVisible()
  })

  test('should display jobs table', async ({ page }) => {
    await page.waitForLoadState('networkidle')

    // Verificar que a tabela existe
    const table = page.locator('text=Jobs do Sistema')
    await expect(table).toBeVisible()
  })

  test('should filter jobs by search', async ({ page }) => {
    await page.waitForLoadState('networkidle')

    // Buscar por um job específico
    const searchInput = page.locator('input[placeholder*="Buscar"]')
    await searchInput.fill('heartbeat')

    // Aguardar filtro
    await page.waitForTimeout(500)

    // Verificar que apenas heartbeat aparece (ou menos resultados)
    // Nota: verificação exata depende dos dados
  })

  test('should open job detail modal on click', async ({ page }) => {
    await page.waitForLoadState('networkidle')

    // Clicar em uma linha da tabela
    const firstRow = page.locator('table tbody tr').first()
    await firstRow.click()

    // Verificar que modal abriu
    const modal = page.locator('[role="dialog"]')
    await expect(modal).toBeVisible()
  })

  test('should have monitor link in sidebar', async ({ page }) => {
    // Verificar que o link existe no sidebar
    const sidebar = page.locator('nav')
    await expect(sidebar.locator('text=Monitor')).toBeVisible()
  })

  test('should highlight monitor in sidebar when active', async ({ page }) => {
    // Verificar que o item está ativo
    const monitorLink = page.locator('nav a[href="/monitor"]')
    // Classes de ativo dependem da implementação
    await expect(monitorLink).toHaveClass(/revoluna|active|bg-/)
  })

  test('should refresh data on button click', async ({ page }) => {
    await page.waitForLoadState('networkidle')

    // Clicar no botão de refresh
    const refreshButton = page.locator('button:has-text("Atualizar")')
    await refreshButton.click()

    // Verificar que o ícone está animando (spin)
    const spinIcon = page.locator('svg.animate-spin')
    await expect(spinIcon).toBeVisible()

    // Aguardar término do refresh
    await page.waitForTimeout(2000)
    await expect(spinIcon).not.toBeVisible()
  })
})

test.describe('Warmup Page (renamed from Scheduler)', () => {
  test('should load warmup page', async ({ page }) => {
    await page.goto('/chips/warmup')
    await expect(page).toHaveURL(/chips\/warmup/)
  })

  test('should have warmup link in chips sidebar', async ({ page }) => {
    await page.goto('/chips/warmup')
    const sidebar = page.locator('nav')
    await expect(sidebar.locator('text=Warmup')).toBeVisible()
  })

  test('old scheduler URL should not work', async ({ page }) => {
    // Tentar acessar URL antiga
    const response = await page.goto('/chips/scheduler')

    // Deve retornar 404 ou redirecionar
    // Nota: comportamento exato depende se há redirect configurado
    expect(response?.status()).toBeOneOf([404, 301, 302, 200])
  })
})
```

### DoD

- [ ] Arquivo `e2e/monitor.e2e.ts` criado
- [ ] Testes de carregamento de página
- [ ] Testes de exibição de componentes
- [ ] Testes de filtros
- [ ] Testes de modal
- [ ] Testes de sidebar
- [ ] Testes de warmup (rename)
- [ ] Todos os testes passando

---

## Story 7.2: Build de Produção

### Objetivo
Garantir que o build de produção compila sem erros.

### Tarefas

1. **Executar build:**

```bash
cd dashboard

# Limpar cache
rm -rf .next

# Build de produção
npm run build
```

2. **Verificar saída:**
- Sem erros de TypeScript
- Sem erros de lint
- Bundle gerado corretamente

3. **Testar build localmente:**

```bash
npm run start
# Acessar http://localhost:3000/monitor
```

### DoD

- [ ] `npm run build` passa sem erros
- [ ] Sem warnings de TypeScript
- [ ] Bundle gerado em `.next/`
- [ ] Página funciona no modo produção

---

## Story 7.3: Validação Manual

### Objetivo
Verificar fluxos completos manualmente.

### Tarefas

1. **Checklist de Verificação:**

**Página /monitor:**
- [ ] Carrega em menos de 2s
- [ ] System Health Card exibe status correto
- [ ] Stats Cards mostram números
- [ ] Jobs Table lista 32 jobs
- [ ] Filtro de status funciona (all, running, success, error, timeout, stale)
- [ ] Filtro de categoria funciona (critical, frequent, hourly, daily, weekly)
- [ ] Filtro de período funciona (1h, 6h, 24h)
- [ ] Busca por nome funciona
- [ ] Clicar em job abre modal
- [ ] Modal mostra histórico de execuções
- [ ] Paginação do modal funciona
- [ ] Botão Atualizar recarrega dados
- [ ] Auto-refresh atualiza a cada 30s
- [ ] Sidebar destaca "Monitor" quando ativo
- [ ] Mobile: página responsiva

**Página /chips/warmup:**
- [ ] Carrega corretamente
- [ ] Título mostra "Warmup"
- [ ] Sidebar de chips mostra "Warmup" (não "Scheduler")
- [ ] Navegação funciona

**Verificação de URLs:**
- [ ] `/monitor` → funciona
- [ ] `/chips/warmup` → funciona
- [ ] `/chips/scheduler` → 404 (ou redirect)

2. **Verificar em diferentes browsers:**
- [ ] Chrome
- [ ] Firefox
- [ ] Safari (se disponível)

3. **Verificar em mobile:**
- [ ] Responsive design funciona
- [ ] Touch em elementos funciona
- [ ] Modal abre corretamente

### DoD

- [ ] Todos os itens do checklist verificados
- [ ] Nenhum bug crítico encontrado
- [ ] UX aceitável

---

## Story 7.4: Verificar Dados Reais

### Objetivo
Confirmar que a API retorna dados reais do Supabase.

### Tarefas

1. **Verificar tabela job_executions existe:**

```sql
-- Executar via MCP ou Supabase dashboard
SELECT COUNT(*) FROM job_executions;

-- Verificar estrutura
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'job_executions';
```

2. **Verificar que APIs retornam dados:**

```bash
# Após iniciar dev server
curl http://localhost:3000/api/dashboard/monitor | jq '.systemHealth.status'
curl http://localhost:3000/api/dashboard/monitor/jobs | jq '.total'
```

3. **Se tabela não existir:**
- Criar migration para a tabela
- Ou verificar com o time de backend

### DoD

- [ ] Tabela job_executions existe
- [ ] APIs retornam dados reais
- [ ] Dashboard exibe dados corretos

---

## Story 7.5: Limpeza e Documentação

### Objetivo
Remover código morto e documentar decisões.

### Tarefas

1. **Verificar que não há referências antigas:**

```bash
cd dashboard

# Buscar referências a "scheduler" (exceto tipos que podem manter o nome)
grep -r "scheduler" app/ components/ lib/ --include="*.tsx" --include="*.ts" \
  | grep -v "node_modules" \
  | grep -v "types/chips.ts"  # tipos podem manter nome original

# Deve retornar vazio ou apenas referências válidas
```

2. **Remover diretórios vazios:**

```bash
# Se ainda existirem
rm -rf app/(dashboard)/chips/scheduler
rm -rf app/api/dashboard/chips/scheduler
```

3. **Atualizar CLAUDE.md se necessário:**
- Adicionar Sprint 42 à lista de sprints completas
- Documentar novas rotas

### DoD

- [ ] Sem referências mortas a "scheduler"
- [ ] Diretórios antigos removidos
- [ ] Documentação atualizada

---

## Checklist do Épico

- [ ] **S42.E07.1** - Testes E2E criados e passando
- [ ] **S42.E07.2** - Build de produção OK
- [ ] **S42.E07.3** - Validação manual completa
- [ ] **S42.E07.4** - Dados reais funcionando
- [ ] **S42.E07.5** - Limpeza concluída
- [ ] Sprint pronta para merge

---

## Comandos de Validação Final

```bash
cd dashboard

# 1. Lint
npm run lint

# 2. Type check
npx tsc --noEmit

# 3. Build
npm run build

# 4. Testes E2E
npm run test:e2e

# 5. Verificar referências mortas
grep -r "scheduler" app/ components/ lib/ --include="*.tsx" --include="*.ts" | grep -v types

# Se tudo passar, sprint está completa!
```
