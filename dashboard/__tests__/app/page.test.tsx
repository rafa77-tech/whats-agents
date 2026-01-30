/**
 * Testes para a página raiz (/).
 *
 * Verifica redirecionamentos baseados em autenticação.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { redirect } from 'next/navigation'

// Mock do next/navigation
vi.mock('next/navigation', () => ({
  redirect: vi.fn(),
}))

// Mock do Supabase client
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(),
}))

import { createClient } from '@/lib/supabase/server'
import Home from '../../app/page'

describe('Home Page (/)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('redireciona para /dashboard quando usuário está autenticado', async () => {
    const mockGetUser = vi.fn().mockResolvedValue({
      data: { user: { id: 'user-123', email: 'test@example.com' } },
    })

    vi.mocked(createClient).mockResolvedValue({
      auth: { getUser: mockGetUser },
    } as never)

    await Home()

    expect(redirect).toHaveBeenCalledWith('/dashboard')
  })

  it('redireciona para /login quando usuário não está autenticado', async () => {
    const mockGetUser = vi.fn().mockResolvedValue({
      data: { user: null },
    })

    vi.mocked(createClient).mockResolvedValue({
      auth: { getUser: mockGetUser },
    } as never)

    await Home()

    expect(redirect).toHaveBeenCalledWith('/login')
  })

  it('chama createClient para verificar autenticação', async () => {
    const mockGetUser = vi.fn().mockResolvedValue({
      data: { user: null },
    })

    vi.mocked(createClient).mockResolvedValue({
      auth: { getUser: mockGetUser },
    } as never)

    await Home()

    expect(createClient).toHaveBeenCalled()
  })

  it('chama getUser do Supabase auth', async () => {
    const mockGetUser = vi.fn().mockResolvedValue({
      data: { user: null },
    })

    vi.mocked(createClient).mockResolvedValue({
      auth: { getUser: mockGetUser },
    } as never)

    await Home()

    expect(mockGetUser).toHaveBeenCalled()
  })
})
