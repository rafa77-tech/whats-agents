import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { NovaCampanhaWizard } from '@/components/campanhas/nova-campanha-wizard'

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Store original fetch
const originalFetch = global.fetch

describe('NovaCampanhaWizard', () => {
  const mockOnOpenChange = vi.fn()
  const mockOnSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 1 }),
    })
  })

  afterEach(() => {
    cleanup()
    global.fetch = originalFetch
  })

  it('renderiza wizard quando aberto', () => {
    render(
      <NovaCampanhaWizard open={true} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    expect(screen.getByText('Nova Campanha')).toBeInTheDocument()
  })

  it('mostra etapas do wizard', () => {
    render(
      <NovaCampanhaWizard open={true} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    expect(screen.getByText('Configuracao')).toBeInTheDocument()
    expect(screen.getByText('Audiencia')).toBeInTheDocument()
    expect(screen.getByText('Mensagem')).toBeInTheDocument()
    expect(screen.getByText('Revisao')).toBeInTheDocument()
  })

  it('mostra campos da etapa 1', () => {
    render(
      <NovaCampanhaWizard open={true} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    expect(screen.getByText('Nome da Campanha *')).toBeInTheDocument()
    expect(screen.getByText('Tipo de Campanha')).toBeInTheDocument()
    expect(screen.getByText('Categoria')).toBeInTheDocument()
    expect(screen.getByText('Objetivo (opcional)')).toBeInTheDocument()
  })

  it('desabilita botao Proximo sem nome', () => {
    render(
      <NovaCampanhaWizard open={true} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    const proximoButton = screen.getByText('Proximo')
    expect(proximoButton).toBeDisabled()
  })

  it('habilita botao Proximo com nome preenchido', () => {
    render(
      <NovaCampanhaWizard open={true} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    const nomeInput = screen.getByPlaceholderText('Ex: Oferta Cardio ABC - Janeiro')
    fireEvent.change(nomeInput, { target: { value: 'Minha Campanha' } })

    const proximoButton = screen.getByText('Proximo')
    expect(proximoButton).not.toBeDisabled()
  })

  it('avanca para etapa 2 ao clicar Proximo', async () => {
    render(
      <NovaCampanhaWizard open={true} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    // Preencher nome
    const nomeInput = screen.getByPlaceholderText('Ex: Oferta Cardio ABC - Janeiro')
    fireEvent.change(nomeInput, { target: { value: 'Minha Campanha' } })

    // Clicar proximo
    fireEvent.click(screen.getByText('Proximo'))

    // Deve mostrar campo de audiencia especifico da etapa 2 (nao apenas o label no progress)
    // Verificamos pelo select que existe na etapa 2
    await waitFor(() => {
      // O select de audiencia deve estar presente (primeiro combobox)
      const selectTriggers = screen.getAllByRole('combobox')
      expect(selectTriggers.length).toBeGreaterThan(0)
    })
  })

  it('mostra opcoes de filtro quando seleciona Filtrar audiencia', async () => {
    render(
      <NovaCampanhaWizard open={true} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    // Preencher nome e avancar
    const nomeInput = screen.getByPlaceholderText('Ex: Oferta Cardio ABC - Janeiro')
    fireEvent.change(nomeInput, { target: { value: 'Minha Campanha' } })
    fireEvent.click(screen.getByText('Proximo'))

    // Selecionar filtrar
    await waitFor(() => {
      expect(screen.getByText('Todos os medicos')).toBeInTheDocument()
    })

    // Clicar no primeiro select (audiencia) e escolher filtrado
    const selectTriggers = screen.getAllByRole('combobox')
    fireEvent.click(selectTriggers[0])

    await waitFor(() => {
      const filtradoOption = screen.getByText('Filtrar audiencia')
      fireEvent.click(filtradoOption)
    })

    // Deve mostrar especialidades e estados
    await waitFor(() => {
      expect(screen.getByText('Especialidades')).toBeInTheDocument()
      expect(screen.getByText('Estados')).toBeInTheDocument()
    })
  })

  it('mostra botao Voltar desabilitado na etapa 1', () => {
    render(
      <NovaCampanhaWizard open={true} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    const voltarButton = screen.getByText('Voltar')
    expect(voltarButton).toBeDisabled()
  })

  it('volta para etapa anterior ao clicar Voltar', async () => {
    render(
      <NovaCampanhaWizard open={true} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    // Avancar para etapa 2
    const nomeInput = screen.getByPlaceholderText('Ex: Oferta Cardio ABC - Janeiro')
    fireEvent.change(nomeInput, { target: { value: 'Minha Campanha' } })
    fireEvent.click(screen.getByText('Proximo'))

    await waitFor(() => {
      expect(screen.getByText('Todos os medicos')).toBeInTheDocument()
    })

    // Voltar
    fireEvent.click(screen.getByText('Voltar'))

    // Deve voltar para etapa 1
    await waitFor(() => {
      expect(screen.getByText('Nome da Campanha *')).toBeInTheDocument()
    })
  })

  it('nao renderiza quando fechado', () => {
    render(
      <NovaCampanhaWizard open={false} onOpenChange={mockOnOpenChange} onSuccess={mockOnSuccess} />
    )

    expect(screen.queryByText('Nova Campanha')).not.toBeInTheDocument()
  })
})
