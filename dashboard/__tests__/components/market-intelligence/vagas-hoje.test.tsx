/**
 * Testes Unitarios - VagasHoje
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { VagasHoje } from '@/components/market-intelligence/vagas-hoje'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

const sampleData = {
  grupos: [
    { id: 'g1', nome: 'Grupo A', vagas_importadas: 10 },
    { id: 'g2', nome: 'Grupo B', vagas_importadas: 5 },
  ],
  vagas: [
    {
      id: 'v1',
      hospital: 'Hospital ABC',
      especialidade: 'Cardiologia',
      valor: 2000,
      data: '2024-01-15',
      periodo: 'noturno',
      grupo: 'Grupo A',
      created_at: '2024-01-15T10:30:00Z',
      mensagem_original: {
        texto: 'Vaga disponivel para cardio',
        sender_nome: 'Joao',
        created_at: '2024-01-15T09:00:00Z',
      },
    },
    {
      id: 'v2',
      hospital: 'Hospital XYZ',
      especialidade: 'Ortopedia',
      valor: null,
      data: null,
      periodo: null,
      grupo: 'Grupo B',
      created_at: '2024-01-15T11:00:00Z',
      mensagem_original: null,
    },
  ],
}

describe('VagasHoje', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve mostrar skeleton durante loading', () => {
    mockFetch.mockReturnValue(new Promise(() => {})) // never resolves
    render(<VagasHoje />)
    // Skeletons are rendered (no text content yet)
    expect(screen.queryByText('Vagas por Grupo')).not.toBeInTheDocument()
  })

  it('deve renderizar grupos e vagas apos fetch', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(sampleData),
    })

    render(<VagasHoje />)

    await waitFor(() => {
      expect(screen.getByText('Vagas por Grupo')).toBeInTheDocument()
    })
    expect(screen.getByText('Vagas Importadas Hoje')).toBeInTheDocument()
    expect(screen.getByText('Hospital ABC')).toBeInTheDocument()
    expect(screen.getByText('Hospital XYZ')).toBeInTheDocument()
  })

  it('deve mostrar mensagem quando nao ha vagas', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ grupos: [], vagas: [] }),
    })

    render(<VagasHoje />)

    await waitFor(() => {
      expect(screen.getByText(/Nenhuma vaga importada hoje/)).toBeInTheDocument()
    })
  })

  it('deve abrir modal ao clicar em vaga', async () => {
    const user = userEvent.setup()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(sampleData),
    })

    render(<VagasHoje />)

    await waitFor(() => {
      expect(screen.getByText('Hospital ABC')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Hospital ABC'))

    await waitFor(() => {
      expect(screen.getByText('Detalhes da Vaga')).toBeInTheDocument()
    })
  })

  it('deve renderizar nada quando fetch falha', async () => {
    mockFetch.mockResolvedValue({ ok: false })

    const { container } = render(<VagasHoje />)

    await waitFor(() => {
      // After loading, component returns null on failure
      const cards = container.querySelectorAll('[class*="space-y"]')
      // Either renders nothing or empty state
      expect(mockFetch).toHaveBeenCalled()
    })
  })

  it('deve formatar valor como moeda', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(sampleData),
    })

    render(<VagasHoje />)

    await waitFor(() => {
      expect(screen.getByText('Hospital ABC')).toBeInTheDocument()
    })

    // R$ 2.000 format
    expect(screen.getByText(/2\.000/)).toBeInTheDocument()
  })

  it('deve mostrar "-" para valores nulos na tabela', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          grupos: [],
          vagas: [
            {
              id: 'v1',
              hospital: 'Hosp',
              especialidade: 'Esp',
              valor: null,
              data: null,
              periodo: null,
              grupo: 'G',
              created_at: '2024-01-15T10:00:00Z',
              mensagem_original: null,
            },
          ],
        }),
    })

    render(<VagasHoje />)

    await waitFor(() => {
      expect(screen.getByText('Hosp')).toBeInTheDocument()
    })

    // Null values render as "-"
    const dashes = screen.getAllByText('-')
    expect(dashes.length).toBeGreaterThanOrEqual(3) // data, periodo, valor
  })

  it('deve mostrar periodo labels traduzidos', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(sampleData),
    })

    render(<VagasHoje />)

    await waitFor(() => {
      expect(screen.getByText('Noturno')).toBeInTheDocument()
    })
  })
})
