/**
 * Tests for FlowsTab component
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import type { MetaFlow } from '@/types/meta'

// Stable toast mock
const stableToast = vi.fn()
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: stableToast }),
}))

// Mock metaApi
const mockGetFlows = vi.fn()
const mockPublishFlow = vi.fn()
const mockDeprecateFlow = vi.fn()
vi.mock('@/lib/api/meta', () => ({
  metaApi: {
    getFlows: (...args: unknown[]) => mockGetFlows(...args),
    publishFlow: (...args: unknown[]) => mockPublishFlow(...args),
    deprecateFlow: (...args: unknown[]) => mockDeprecateFlow(...args),
  },
}))

import FlowsTab from '@/components/meta/tabs/flows-tab'

const mockFlows: MetaFlow[] = [
  {
    id: 'f1',
    waba_id: 'waba1',
    meta_flow_id: 'meta_f1',
    name: 'Onboarding Medicos',
    flow_type: 'FLOW',
    status: 'DRAFT',
    created_at: '2026-02-01T00:00:00Z',
    updated_at: '2026-02-01T00:00:00Z',
    response_count: 0,
    json_definition: {
      version: '7.0',
      screens: [
        {
          id: 'SCREEN_1',
          title: 'Cadastro',
          layout: {
            type: 'SingleColumnLayout',
            children: [{ type: 'TextInput', name: 'nome', label: 'Nome completo', required: true }],
          },
        },
      ],
    },
  },
  {
    id: 'f2',
    waba_id: 'waba1',
    meta_flow_id: 'meta_f2',
    name: 'Confirmacao Plantao',
    flow_type: 'FLOW',
    status: 'PUBLISHED',
    created_at: '2026-02-02T00:00:00Z',
    updated_at: '2026-02-02T00:00:00Z',
    response_count: 42,
  },
  {
    id: 'f3',
    waba_id: 'waba1',
    meta_flow_id: 'meta_f3',
    name: 'Avaliacao Pos-Plantao',
    flow_type: 'FLOW',
    status: 'DEPRECATED',
    created_at: '2026-02-03T00:00:00Z',
    updated_at: '2026-02-03T00:00:00Z',
    response_count: 15,
  },
]

beforeEach(() => {
  mockGetFlows.mockReset()
  mockPublishFlow.mockReset()
  mockDeprecateFlow.mockReset()
  stableToast.mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('FlowsTab', () => {
  it('should show loading state initially', () => {
    mockGetFlows.mockReturnValue(new Promise(() => {}))
    render(<FlowsTab />)
    expect(screen.getByText('Carregando flows...')).toBeInTheDocument()
  })

  it('should render flow cards after loading', async () => {
    mockGetFlows.mockResolvedValue(mockFlows)
    render(<FlowsTab />)

    await waitFor(() => {
      expect(screen.getByText('Onboarding Medicos')).toBeInTheDocument()
    })
    expect(screen.getByText('Confirmacao Plantao')).toBeInTheDocument()
    expect(screen.getByText('Avaliacao Pos-Plantao')).toBeInTheDocument()
  })

  it('should display status badges', async () => {
    mockGetFlows.mockResolvedValue(mockFlows)
    render(<FlowsTab />)

    await waitFor(() => {
      expect(screen.getByText('Rascunho')).toBeInTheDocument()
    })
    expect(screen.getByText('Publicado')).toBeInTheDocument()
    expect(screen.getByText('Descontinuado')).toBeInTheDocument()
  })

  it('should display response counts', async () => {
    mockGetFlows.mockResolvedValue(mockFlows)
    render(<FlowsTab />)

    await waitFor(() => {
      expect(screen.getByText('0 respostas')).toBeInTheDocument()
    })
    expect(screen.getByText('42 respostas')).toBeInTheDocument()
    expect(screen.getByText('15 respostas')).toBeInTheDocument()
  })

  it('should show Publicar button for DRAFT flows', async () => {
    mockGetFlows.mockResolvedValue(mockFlows)
    render(<FlowsTab />)

    await waitFor(() => {
      expect(screen.getByText('Publicar')).toBeInTheDocument()
    })
  })

  it('should show Descontinuar button for PUBLISHED flows', async () => {
    mockGetFlows.mockResolvedValue(mockFlows)
    render(<FlowsTab />)

    await waitFor(() => {
      expect(screen.getByText('Descontinuar')).toBeInTheDocument()
    })
  })

  it('should call publishFlow on Publicar click', async () => {
    mockGetFlows.mockResolvedValue(mockFlows)
    mockPublishFlow.mockResolvedValue(undefined)
    const user = userEvent.setup()

    render(<FlowsTab />)

    await waitFor(() => {
      expect(screen.getByText('Publicar')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Publicar'))

    await waitFor(() => {
      expect(mockPublishFlow).toHaveBeenCalledWith('f1')
    })
  })

  it('should call deprecateFlow on Descontinuar click', async () => {
    mockGetFlows.mockResolvedValue(mockFlows)
    mockDeprecateFlow.mockResolvedValue(undefined)
    const user = userEvent.setup()

    render(<FlowsTab />)

    await waitFor(() => {
      expect(screen.getByText('Descontinuar')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Descontinuar'))

    await waitFor(() => {
      expect(mockDeprecateFlow).toHaveBeenCalledWith('f2')
    })
  })

  it('should show empty state when no flows', async () => {
    mockGetFlows.mockResolvedValue([])
    render(<FlowsTab />)

    await waitFor(() => {
      expect(screen.getByText('Nenhum WhatsApp Flow encontrado.')).toBeInTheDocument()
    })
  })

  it('should show error toast on fetch failure', async () => {
    mockGetFlows.mockRejectedValue(new Error('Network error'))
    render(<FlowsTab />)

    await waitFor(() => {
      expect(stableToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Erro ao carregar flows',
          variant: 'destructive',
        })
      )
    })
  })

  it('should render flow screen preview when json_definition exists', async () => {
    mockGetFlows.mockResolvedValue(mockFlows)
    render(<FlowsTab />)

    await waitFor(() => {
      expect(screen.getByText('Cadastro')).toBeInTheDocument()
    })
    expect(screen.getByText('Nome completo')).toBeInTheDocument()
  })
})
