/**
 * Testes para o middleware de autenticação.
 *
 * Verifica redirecionamentos e proteção de rotas.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest, NextResponse } from 'next/server'

// Mock do Supabase SSR
vi.mock('@supabase/ssr', () => ({
  createServerClient: vi.fn(() => ({
    auth: {
      getUser: vi.fn(),
    },
  })),
}))

// Precisamos importar após o mock
import { createServerClient } from '@supabase/ssr'
import { middleware } from '../middleware'

// Helper para criar request mock
function createMockRequest(pathname: string, hostname = 'example.com'): NextRequest {
  const url = new URL(`https://${hostname}${pathname}`)
  return {
    nextUrl: {
      pathname,
      hostname,
      clone: () => url,
    },
    cookies: {
      getAll: () => [],
      set: vi.fn(),
    },
  } as unknown as NextRequest
}

describe('Middleware', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.NEXT_PUBLIC_ENV = 'production'
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://test.supabase.co'
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-key'
  })

  describe('Bypass em desenvolvimento local', () => {
    it('permite acesso sem autenticação em localhost quando env=development', async () => {
      process.env.NEXT_PUBLIC_ENV = 'development'
      const request = createMockRequest('/dashboard', 'localhost')

      const response = await middleware(request)

      // Deve retornar NextResponse.next() sem redirect
      expect(response.headers.get('x-middleware-rewrite')).toBeNull()
    })
  })

  describe('Rotas protegidas (isDashboardRoute)', () => {
    const protectedRoutes = [
      '/',
      '/dashboard',
      '/dashboard/chips',
      '/campanhas',
      '/campanhas/123',
      '/sistema',
      '/instrucoes',
      '/hospitais',
      '/ajuda',
    ]

    protectedRoutes.forEach((route) => {
      it(`redireciona ${route} para /login quando não autenticado`, async () => {
        const mockGetUser = vi.fn().mockResolvedValue({ data: { user: null } })
        vi.mocked(createServerClient).mockReturnValue({
          auth: { getUser: mockGetUser },
        } as never)

        const request = createMockRequest(route)
        const response = await middleware(request)

        // Verificar que é um redirect para /login
        expect(response.status).toBe(307) // Redirect
        expect(response.headers.get('location')).toContain('/login')
      })
    })

    protectedRoutes.forEach((route) => {
      it(`permite acesso a ${route} quando autenticado`, async () => {
        const mockGetUser = vi.fn().mockResolvedValue({
          data: { user: { id: 'user-123', email: 'test@example.com' } },
        })
        vi.mocked(createServerClient).mockReturnValue({
          auth: { getUser: mockGetUser },
        } as never)

        const request = createMockRequest(route)
        const response = await middleware(request)

        // Não deve ser redirect
        expect(response.status).not.toBe(307)
      })
    })
  })

  describe('Rotas de autenticação', () => {
    it('redireciona usuário autenticado de /login para /', async () => {
      const mockGetUser = vi.fn().mockResolvedValue({
        data: { user: { id: 'user-123', email: 'test@example.com' } },
      })
      vi.mocked(createServerClient).mockReturnValue({
        auth: { getUser: mockGetUser },
      } as never)

      const request = createMockRequest('/login')
      const response = await middleware(request)

      expect(response.status).toBe(307)
      expect(response.headers.get('location')).toContain('/')
    })

    it('permite acesso a /login quando não autenticado', async () => {
      const mockGetUser = vi.fn().mockResolvedValue({ data: { user: null } })
      vi.mocked(createServerClient).mockReturnValue({
        auth: { getUser: mockGetUser },
      } as never)

      const request = createMockRequest('/login')
      const response = await middleware(request)

      expect(response.status).not.toBe(307)
    })

    it('permite acesso a /auth/callback sem autenticação', async () => {
      const mockGetUser = vi.fn().mockResolvedValue({ data: { user: null } })
      vi.mocked(createServerClient).mockReturnValue({
        auth: { getUser: mockGetUser },
      } as never)

      const request = createMockRequest('/auth/callback')
      const response = await middleware(request)

      expect(response.status).not.toBe(307)
    })
  })

  describe('Rotas de API', () => {
    it('permite acesso a rotas /api sem autenticação', async () => {
      const mockGetUser = vi.fn().mockResolvedValue({ data: { user: null } })
      vi.mocked(createServerClient).mockReturnValue({
        auth: { getUser: mockGetUser },
      } as never)

      const request = createMockRequest('/api/dashboard/metrics')
      const response = await middleware(request)

      // API routes devem passar sem redirect
      expect(response.status).not.toBe(307)
    })
  })

  describe('Proteção de /dashboard', () => {
    it('/dashboard é uma rota protegida', async () => {
      const mockGetUser = vi.fn().mockResolvedValue({ data: { user: null } })
      vi.mocked(createServerClient).mockReturnValue({
        auth: { getUser: mockGetUser },
      } as never)

      const request = createMockRequest('/dashboard')
      const response = await middleware(request)

      expect(response.status).toBe(307)
      expect(response.headers.get('location')).toContain('/login')
    })

    it('/dashboard/chips é uma rota protegida', async () => {
      const mockGetUser = vi.fn().mockResolvedValue({ data: { user: null } })
      vi.mocked(createServerClient).mockReturnValue({
        auth: { getUser: mockGetUser },
      } as never)

      const request = createMockRequest('/dashboard/chips')
      const response = await middleware(request)

      expect(response.status).toBe(307)
      expect(response.headers.get('location')).toContain('/login')
    })
  })
})
