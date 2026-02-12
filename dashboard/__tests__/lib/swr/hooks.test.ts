/**
 * Testes para lib/swr/hooks
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock SWR
const mockUseSWR = vi.fn()
const mockUseSWRMutation = vi.fn()

vi.mock('swr', () => ({
  default: (...args: unknown[]) => mockUseSWR(...args),
}))

vi.mock('swr/mutation', () => ({
  default: (...args: unknown[]) => mockUseSWRMutation(...args),
}))

vi.mock('@/lib/swr/config', () => ({
  realtimeConfig: { refreshInterval: 30000 },
  staticConfig: { revalidateIfStale: false },
  postFetcher: vi.fn(),
}))

import {
  useMetrics,
  useFunnel,
  useChips,
  useChip,
  useAlerts,
  useConversas,
  useConversa,
  useChipAction,
  useResolveAlert,
} from '@/lib/swr/hooks'

function mockSWRReturn(overrides = {}) {
  return {
    data: undefined,
    error: undefined,
    isLoading: false,
    mutate: vi.fn(),
    isValidating: false,
    ...overrides,
  }
}

function mockSWRMutationReturn(overrides = {}) {
  return {
    trigger: vi.fn(),
    isMutating: false,
    error: undefined,
    ...overrides,
  }
}

describe('useMetrics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve retornar dados de metricas', () => {
    const mockData = { conversasAtivas: 10, taxaResposta: 0.8 }
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: mockData }))

    const result = useMetrics()

    expect(result.metrics).toEqual(mockData)
    expect(result.isLoading).toBe(false)
    expect(result.isError).toBe(false)
  })

  it('deve retornar isLoading=true quando carregando', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ isLoading: true }))

    const result = useMetrics()

    expect(result.isLoading).toBe(true)
  })

  it('deve retornar isError=true quando ha erro', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ error: new Error('fail') }))

    const result = useMetrics()

    expect(result.isError).toBe(true)
    expect(result.error).toBeTruthy()
  })

  it('deve usar periodo default 7d', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn())

    useMetrics()

    expect(mockUseSWR).toHaveBeenCalledWith('/api/dashboard/metrics?period=7d', expect.any(Object))
  })

  it('deve passar periodo customizado na URL', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn())

    useMetrics('30d')

    expect(mockUseSWR).toHaveBeenCalledWith('/api/dashboard/metrics?period=30d', expect.any(Object))
  })
})

describe('useFunnel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve retornar dados do funil', () => {
    const mockData = { etapas: [], periodo: '7d' }
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: mockData }))

    const result = useFunnel()

    expect(result.funnel).toEqual(mockData)
    expect(result.isError).toBe(false)
  })

  it('deve usar periodo default 7d', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn())

    useFunnel()

    expect(mockUseSWR).toHaveBeenCalledWith('/api/dashboard/funnel?period=7d', expect.any(Object))
  })
})

describe('useChips', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve retornar URL sem params quando sem filtros', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: [] }))

    const result = useChips()

    expect(mockUseSWR).toHaveBeenCalledWith('/api/chips', expect.any(Object))
    expect(result.chips).toEqual([])
  })

  it('deve adicionar status param quando fornecido', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: [] }))

    useChips({ status: 'ativo' })

    expect(mockUseSWR).toHaveBeenCalledWith('/api/chips?status=ativo', expect.any(Object))
  })

  it('deve adicionar instancia param quando fornecido', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: [] }))

    useChips({ instancia: 'inst1' })

    expect(mockUseSWR).toHaveBeenCalledWith('/api/chips?instancia=inst1', expect.any(Object))
  })

  it('deve adicionar ambos params quando fornecidos', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: [] }))

    useChips({ status: 'ativo', instancia: 'inst1' })

    expect(mockUseSWR).toHaveBeenCalledWith(
      '/api/chips?status=ativo&instancia=inst1',
      expect.any(Object)
    )
  })

  it('deve retornar array vazio quando data é undefined', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: undefined }))

    const result = useChips()

    expect(result.chips).toEqual([])
  })
})

describe('useChip', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve passar null key quando chipId é null', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn())

    useChip(null)

    expect(mockUseSWR).toHaveBeenCalledWith(null, expect.any(Object))
  })

  it('deve passar URL com chipId quando fornecido', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn())

    useChip('chip-1')

    expect(mockUseSWR).toHaveBeenCalledWith('/api/chips/chip-1', expect.any(Object))
  })

  it('deve retornar dados do chip', () => {
    const mockData = { id: 'chip-1', telefone: '5511999999999' }
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: mockData }))

    const result = useChip('chip-1')

    expect(result.chip).toEqual(mockData)
  })
})

describe('useAlerts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve usar limit default de 10', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: [] }))

    useAlerts()

    expect(mockUseSWR).toHaveBeenCalledWith('/api/alerts?limit=10', expect.any(Object))
  })

  it('deve usar limit customizado', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: [] }))

    useAlerts(5)

    expect(mockUseSWR).toHaveBeenCalledWith('/api/alerts?limit=5', expect.any(Object))
  })

  it('deve retornar array vazio quando data é undefined', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: undefined }))

    const result = useAlerts()

    expect(result.alerts).toEqual([])
  })
})

describe('useConversas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve retornar URL sem params quando sem filtros', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: [] }))

    useConversas()

    expect(mockUseSWR).toHaveBeenCalledWith('/api/conversas', expect.any(Object))
  })

  it('deve adicionar status param', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: [] }))

    useConversas({ status: 'ativa' })

    expect(mockUseSWR).toHaveBeenCalledWith('/api/conversas?status=ativa', expect.any(Object))
  })

  it('deve adicionar controlled_by param', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: [] }))

    useConversas({ controlled_by: 'ai' })

    expect(mockUseSWR).toHaveBeenCalledWith('/api/conversas?controlled_by=ai', expect.any(Object))
  })

  it('deve retornar array vazio quando data é undefined', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn({ data: undefined }))

    const result = useConversas()

    expect(result.conversas).toEqual([])
  })
})

describe('useConversa', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve passar null key quando conversaId é null', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn())

    useConversa(null)

    expect(mockUseSWR).toHaveBeenCalledWith(null, expect.any(Object))
  })

  it('deve passar URL com conversaId', () => {
    mockUseSWR.mockReturnValue(mockSWRReturn())

    useConversa('conv-1')

    expect(mockUseSWR).toHaveBeenCalledWith('/api/conversas/conv-1', expect.any(Object))
  })
})

describe('useChipAction', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve retornar funcao trigger', () => {
    const mockTrigger = vi.fn()
    mockUseSWRMutation.mockReturnValue(mockSWRMutationReturn({ trigger: mockTrigger }))

    const result = useChipAction()

    expect(result.executeAction).toBe(mockTrigger)
    expect(result.isLoading).toBe(false)
  })

  it('deve retornar isLoading=true quando mutating', () => {
    mockUseSWRMutation.mockReturnValue(mockSWRMutationReturn({ isMutating: true }))

    const result = useChipAction()

    expect(result.isLoading).toBe(true)
  })
})

describe('useResolveAlert', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve retornar funcao trigger', () => {
    const mockTrigger = vi.fn()
    mockUseSWRMutation.mockReturnValue(mockSWRMutationReturn({ trigger: mockTrigger }))

    const result = useResolveAlert()

    expect(result.resolveAlert).toBe(mockTrigger)
    expect(result.isLoading).toBe(false)
  })

  it('deve retornar erro quando presente', () => {
    const mockError = new Error('fail')
    mockUseSWRMutation.mockReturnValue(mockSWRMutationReturn({ error: mockError }))

    const result = useResolveAlert()

    expect(result.error).toBe(mockError)
  })
})
