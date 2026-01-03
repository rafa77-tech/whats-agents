import { expect, test } from '@playwright/test'

test.describe('Health Check', () => {
  test('should return healthy status from API', async ({ request }) => {
    const response = await request.get('/api/health')

    expect(response.ok()).toBeTruthy()

    const body = await response.json()
    expect(body).toHaveProperty('status', 'healthy')
  })

  test('should load the login page', async ({ page }) => {
    await page.goto('/login')

    // Should see login form or be redirected
    await expect(page).toHaveURL(/\/(login|dashboard)?/)
  })

  test('should have correct meta tags', async ({ page }) => {
    await page.goto('/')

    // Check for viewport meta tag
    const viewport = await page.locator('meta[name="viewport"]').getAttribute('content')
    expect(viewport).toContain('width=device-width')

    // Check for title
    const title = await page.title()
    expect(title).toBeTruthy()
  })
})

test.describe('Accessibility', () => {
  test('should not have detectable accessibility issues on login', async ({ page }) => {
    await page.goto('/login')

    // Basic accessibility checks
    // Check that there are no images without alt text
    const imagesWithoutAlt = await page.locator('img:not([alt])').count()
    expect(imagesWithoutAlt).toBe(0)

    // Check that buttons have accessible names
    const buttons = await page.locator('button').all()
    for (const button of buttons) {
      const accessibleName = await button.getAttribute('aria-label') ||
        await button.textContent()
      expect(accessibleName).toBeTruthy()
    }
  })
})

test.describe('Performance', () => {
  test('should load within acceptable time', async ({ page }) => {
    const startTime = Date.now()

    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const loadTime = Date.now() - startTime

    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000)
  })
})
