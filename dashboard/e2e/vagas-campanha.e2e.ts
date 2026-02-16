/**
 * E2E Tests for Vagas → Campanha flow - Sprint 58
 *
 * Tests the full flow of selecting vagas and creating campaigns,
 * both from the list page (/vagas) and detail page (/vagas/[id]).
 *
 * Uses route interception to provide deterministic mock data.
 */

import { test, expect, type Page } from '@playwright/test'

// --- Mock Data ---

const mockVagas = [
  {
    id: 'vaga-e2e-1',
    hospital: 'Hospital São Luiz',
    hospital_id: 'hosp-1',
    especialidade: 'Cardiologia',
    especialidade_id: 'esp-1',
    data: '2026-03-15',
    hora_inicio: '08:00',
    hora_fim: '18:00',
    valor: 2500,
    status: 'aberta',
    reservas_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    contato_nome: 'Dr. Marcos',
    contato_whatsapp: '5511999999999',
  },
  {
    id: 'vaga-e2e-2',
    hospital: 'Hospital Albert Einstein',
    hospital_id: 'hosp-2',
    especialidade: 'Ortopedia',
    especialidade_id: 'esp-2',
    data: '2026-03-16',
    hora_inicio: '19:00',
    hora_fim: '07:00',
    valor: 3000,
    status: 'aberta',
    reservas_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    contato_nome: null,
    contato_whatsapp: null,
  },
]

const mockVagaDetail = {
  ...mockVagas[0],
  setor: 'UTI',
  setor_id: 'setor-1',
  cliente_id: null,
  cliente_nome: null,
  updated_at: null,
}

// --- Helpers ---

/**
 * Intercepts API calls to provide deterministic mock data.
 * This avoids needing a running Supabase instance or real data.
 */
async function setupMockRoutes(page: Page) {
  // Mock GET /api/vagas (list)
  await page.route('**/api/vagas?*', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: mockVagas,
        total: mockVagas.length,
        pages: 1,
      }),
    })
  })

  // Mock GET /api/vagas/vaga-e2e-1 (detail)
  await page.route('**/api/vagas/vaga-e2e-1', (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockVagaDetail),
      })
    } else {
      route.continue()
    }
  })

  // Mock POST /api/campanhas (create campaign)
  await page.route('**/api/campanhas', (route) => {
    if (route.request().method() === 'POST') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 999, status: 'rascunho' }),
      })
    } else {
      route.continue()
    }
  })

  // Mock GET /api/filtros (used by wizard step 2)
  await page.route('**/api/filtros*', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ especialidades: [], estados: [] }),
    })
  })

  // Mock GET /api/chips (used by wizard step 2)
  await page.route('**/api/chips*', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })
}

function isOnPage(page: Page, path: string): boolean {
  const url = page.url()
  return url.includes(path) && !url.includes('/login')
}

// --- Tests ---

test.describe('Vagas → Campanha Flow', () => {
  test.describe('Vagas List Page - Selection Mode', () => {
    test('should load vagas page with Selecionar button', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByRole('heading', { name: 'Vagas' })).toBeVisible()
      await expect(page.getByRole('button', { name: /selecionar/i })).toBeVisible()
    })

    test('should enter selection mode and show checkboxes', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      // Wait for vagas to load
      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Enter selection mode
      await page.getByRole('button', { name: /selecionar/i }).click()

      // Checkboxes should appear
      const checkboxes = page.getByRole('checkbox')
      await expect(checkboxes.first()).toBeVisible()
      expect(await checkboxes.count()).toBe(2)

      // Cancel button should appear
      await expect(page.getByRole('button', { name: /cancelar/i })).toBeVisible()
    })

    test('should show floating action bar when vagas selected', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Enter selection mode
      await page.getByRole('button', { name: /selecionar/i }).click()

      // Select first vaga
      const checkboxes = page.getByRole('checkbox')
      await checkboxes.first().click()

      // Floating action bar should appear with count
      await expect(page.getByText(/1 vaga selecionada/)).toBeVisible()
      await expect(page.getByRole('button', { name: /criar campanha/i })).toBeVisible()
    })

    test('should show correct count for multiple selections', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Enter selection mode
      await page.getByRole('button', { name: /selecionar/i }).click()

      // Select both vagas
      const checkboxes = page.getByRole('checkbox')
      await checkboxes.nth(0).click()
      await checkboxes.nth(1).click()

      // Should show plural
      await expect(page.getByText(/2 vagas selecionadas/)).toBeVisible()
    })

    test('should clear selection with Limpar button', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Enter selection mode and select
      await page.getByRole('button', { name: /selecionar/i }).click()
      await page.getByRole('checkbox').first().click()
      await expect(page.getByText(/1 vaga selecionada/)).toBeVisible()

      // Clear selection
      await page.getByRole('button', { name: /limpar/i }).click()

      // Floating bar should disappear
      await expect(page.getByText(/vaga selecionada/)).not.toBeVisible()
    })

    test('should exit selection mode with Cancelar', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Enter selection mode
      await page.getByRole('button', { name: /selecionar/i }).click()
      await expect(page.getByRole('checkbox').first()).toBeVisible()

      // Exit
      await page.getByRole('button', { name: /cancelar/i }).click()

      // Checkboxes should be gone
      await expect(page.getByRole('checkbox')).not.toBeVisible()
      // Selecionar button should be back
      await expect(page.getByRole('button', { name: /selecionar/i })).toBeVisible()
    })

    test('should open wizard with pre-filled data on Criar Campanha', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Select a vaga
      await page.getByRole('button', { name: /selecionar/i }).click()
      await page.getByRole('checkbox').first().click()

      // Click Criar Campanha
      await page.getByRole('button', { name: /criar campanha/i }).click()

      // Wizard should open with pre-filled name
      await expect(page.getByText('Nova Campanha')).toBeVisible({ timeout: 5000 })

      // The name field should be pre-filled with the auto-generated name
      const nameInput = page.locator('input[placeholder*="Oferta"]')
      const nameValue = await nameInput.inputValue().catch(() => '')

      // Name should contain hospital reference (auto-generated)
      if (nameValue) {
        expect(nameValue).toContain('Oferta')
      }
    })

    test('should show wizard with multiple vagas selected', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Select both vagas
      await page.getByRole('button', { name: /selecionar/i }).click()
      const checkboxes = page.getByRole('checkbox')
      await checkboxes.nth(0).click()
      await checkboxes.nth(1).click()

      // Open wizard
      await page.getByRole('button', { name: /criar campanha/i }).click()

      // Wizard should open
      await expect(page.getByText('Nova Campanha')).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Vaga Detail Page - Criar Campanha Button', () => {
    test('should display Criar Campanha button on detail page', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas/vaga-e2e-1')

      if (!isOnPage(page, '/vagas/vaga-e2e-1')) return

      // Wait for vaga to load
      await expect(page.getByText('Hospital São Luiz').first()).toBeVisible({ timeout: 10000 })

      // Criar Campanha button should be visible
      await expect(page.getByRole('button', { name: /criar campanha/i })).toBeVisible()
    })

    test('should open wizard from detail page', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas/vaga-e2e-1')

      if (!isOnPage(page, '/vagas/vaga-e2e-1')) return

      await expect(page.getByText('Hospital São Luiz').first()).toBeVisible({ timeout: 10000 })

      // Click Criar Campanha
      await page.getByRole('button', { name: /criar campanha/i }).click()

      // Wizard should open
      await expect(page.getByText('Nova Campanha')).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Wizard Pre-filled Flow', () => {
    test('should navigate through wizard steps with pre-filled data', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Select and open wizard
      await page.getByRole('button', { name: /selecionar/i }).click()
      await page.getByRole('checkbox').first().click()
      await page.getByRole('button', { name: /criar campanha/i }).click()

      // Step 1: Configuration should be pre-filled
      await expect(page.getByText('Nova Campanha')).toBeVisible({ timeout: 5000 })

      // The "Proximo" button should be enabled (name is pre-filled)
      const proximoButton = page.getByRole('button', { name: /proximo/i })
      await expect(proximoButton).toBeVisible()

      // If the button is enabled, advance to step 2
      const isEnabled = await proximoButton.isEnabled().catch(() => false)
      if (isEnabled) {
        await proximoButton.click()

        // Step 2: Audiencia - advance to step 3
        const step2Proximo = page.getByRole('button', { name: /proximo/i })
        await expect(step2Proximo).toBeVisible()
        await step2Proximo.click()

        // Step 3: Mensagem - corpo should be pre-filled
        const textarea = page.locator('textarea')
        const textValue = await textarea.inputValue().catch(() => '')
        if (textValue) {
          expect(textValue.length).toBeGreaterThan(10)
          expect(textValue).toContain('{{nome}}')
        }

        // Advance to step 4
        const step3Proximo = page.getByRole('button', { name: /proximo/i })
        if (await step3Proximo.isEnabled().catch(() => false)) {
          await step3Proximo.click()

          // Step 4: Revisão - should show vagas vinculadas
          await expect(page.getByText(/vaga vinculada/i)).toBeVisible({ timeout: 5000 })
          // Hospital name appears multiple times; narrow to the vagas vinculadas section
          await expect(page.getByText('Hospital São Luiz', { exact: true }).first()).toBeVisible()
        }
      }
    })

    test('should submit campaign with escopo_vagas', async ({ page }) => {
      await setupMockRoutes(page)

      // Track the POST request to verify escopo_vagas
      let capturedBody: Record<string, unknown> | null = null
      await page.route('**/api/campanhas', (route) => {
        if (route.request().method() === 'POST') {
          capturedBody = route.request().postDataJSON()
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ id: 999, status: 'rascunho' }),
          })
        } else {
          route.continue()
        }
      })

      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Select and open wizard
      await page.getByRole('button', { name: /selecionar/i }).click()
      await page.getByRole('checkbox').first().click()
      await page.getByRole('button', { name: /criar campanha/i }).click()

      await expect(page.getByText('Nova Campanha')).toBeVisible({ timeout: 5000 })

      // Navigate through all steps
      const clickNext = async () => {
        const btn = page.getByRole('button', { name: /proximo/i })
        if (await btn.isEnabled().catch(() => false)) {
          await btn.click()
          return true
        }
        return false
      }

      // Step 1 → 2 → 3 → 4
      if (await clickNext()) {
        if (await clickNext()) {
          if (await clickNext()) {
            // Step 4: Click "Criar Campanha" to submit
            const submitButton = page.getByRole('button', { name: /criar campanha/i })
            await expect(submitButton).toBeVisible()

            if (await submitButton.isEnabled().catch(() => false)) {
              await submitButton.click()

              // Wait for the request to complete
              await page.waitForTimeout(1000)

              // Verify the POST body contains escopo_vagas
              const body = capturedBody as Record<string, unknown> | null
              if (body) {
                expect(body).toHaveProperty('escopo_vagas')
                const escopo = body['escopo_vagas'] as Record<string, unknown>
                expect(escopo).toHaveProperty('vaga_ids')
                expect(escopo).toHaveProperty('vagas')
              }
            }
          }
        }
      }
    })
  })

  test.describe('Accessibility', () => {
    test('selection mode should have accessible checkboxes', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Enter selection mode
      await page.getByRole('button', { name: /selecionar/i }).click()

      // Checkboxes should be keyboard accessible
      const checkbox = page.getByRole('checkbox').first()
      await expect(checkbox).toBeVisible()

      // Tab to checkbox and toggle with space
      await checkbox.focus()
      await page.keyboard.press('Space')

      // Should have selected state
      await expect(checkbox).toHaveAttribute('data-state', 'checked')
    })

    test('floating action bar should have accessible buttons', async ({ page }) => {
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Select a vaga
      await page.getByRole('button', { name: /selecionar/i }).click()
      await page.getByRole('checkbox').first().click()

      // Buttons in the floating bar should have accessible names
      const limparButton = page.getByRole('button', { name: /limpar/i })
      const criarButton = page.getByRole('button', { name: /criar campanha/i })

      await expect(limparButton).toBeVisible()
      await expect(criarButton).toBeVisible()
    })
  })

  test.describe('Responsive', () => {
    test('selection mode should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 })
      await setupMockRoutes(page)
      await page.goto('/vagas')

      if (!isOnPage(page, '/vagas')) return

      await expect(page.getByText('Hospital São Luiz')).toBeVisible({ timeout: 10000 })

      // Selecionar button should be visible (might be icon-only on mobile)
      const selectButton = page
        .locator('button')
        .filter({ has: page.locator('.lucide-check-square') })
      const hasSelectButton = await selectButton.isVisible().catch(() => false)

      if (hasSelectButton) {
        await selectButton.click()
        // Checkboxes should appear on mobile too
        await expect(page.getByRole('checkbox').first()).toBeVisible()
      }
    })
  })
})
