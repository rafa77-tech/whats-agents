/**
 * Tests for instrucoes/page.tsx
 *
 * Tests the pure logic functions (getEscopoLabel, getConteudoLabel)
 * and the page rendering with various data states.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import InstrucoesPage from '@/app/(dashboard)/instrucoes/page'

// Mock dependencies
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/instrucoes',
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}))

vi.mock('@/components/instrucoes/nova-instrucao-dialog', () => ({
  NovaInstrucaoDialog: () => null,
}))

const mockDiretrizes = [
  {
    id: '1',
    tipo: 'margem_negociacao',
    escopo: 'vaga',
    conteudo: { valor_maximo: 3000 },
    criado_por: 'admin',
    criado_em: new Date().toISOString(),
    status: 'ativa',
    vagas: { data: '2026-03-15T10:00:00Z', hospital_id: 'h1' },
  },
  {
    id: '2',
    tipo: 'margem_negociacao',
    escopo: 'medico',
    conteudo: { percentual_maximo: 15 },
    criado_por: 'admin',
    criado_em: new Date().toISOString(),
    status: 'ativa',
    clientes: { primeiro_nome: 'Carlos', sobrenome: 'Silva', telefone: '11999' },
  },
  {
    id: '3',
    tipo: 'regra_especial',
    escopo: 'hospital',
    conteudo: { regra: 'Aceitar apenas CRM ativo' },
    criado_por: 'admin',
    criado_em: new Date().toISOString(),
    expira_em: new Date(Date.now() + 86400000).toISOString(),
    status: 'ativa',
    hospitais: { nome: 'Sao Luiz' },
  },
  {
    id: '4',
    tipo: 'info_adicional',
    escopo: 'especialidade',
    conteudo: { info: 'Precisa de titulo' },
    criado_por: 'admin',
    criado_em: new Date().toISOString(),
    status: 'ativa',
    especialidades: { nome: 'Cardiologia' },
  },
  {
    id: '5',
    tipo: 'info_adicional',
    escopo: 'global',
    conteudo: { info: 'Regra geral' },
    criado_por: 'admin',
    criado_em: new Date().toISOString(),
    status: 'ativa',
  },
]

describe('InstrucoesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('deve renderizar com estado de loading', async () => {
    vi.spyOn(global, 'fetch').mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(<InstrucoesPage />)
    expect(screen.getByText('Instrucoes Ativas')).toBeInTheDocument()
  })

  it('deve renderizar diretrizes carregadas', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockDiretrizes,
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      // Check that table rows are rendered (5 diretrizes)
      expect(screen.getByText('Carlos Silva')).toBeInTheDocument()
    })
  })

  it('deve mostrar estado vazio quando nao ha diretrizes', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Nenhuma instrucao encontrada')).toBeInTheDocument()
    })
  })

  it('deve mostrar erro quando API falha', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'Erro no servidor' }),
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Erro no servidor')).toBeInTheDocument()
    })
  })

  it('deve mostrar erro de conexao quando fetch falha', async () => {
    vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Network error'))

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Erro de conexao com o servidor')).toBeInTheDocument()
    })
  })

  it('deve exibir todos os tipos de escopo', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockDiretrizes,
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      // Vaga com data
      expect(screen.getByText(/Vaga 15\/03/)).toBeInTheDocument()
      // Medico com nome
      expect(screen.getByText('Carlos Silva')).toBeInTheDocument()
      // Hospital com nome
      expect(screen.getByText('Sao Luiz')).toBeInTheDocument()
      // Especialidade com nome
      expect(screen.getByText('Cardiologia')).toBeInTheDocument()
      // Global
      expect(screen.getByText('Todas as conversas')).toBeInTheDocument()
    })
  })

  it('deve exibir conteudo de margem com valor_maximo', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [mockDiretrizes[0]],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText(/Ate R\$/)).toBeInTheDocument()
    })
  })

  it('deve exibir conteudo de margem com percentual_maximo', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [mockDiretrizes[1]],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Ate 15% acima')).toBeInTheDocument()
    })
  })

  it('deve exibir conteudo de regra especial', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [mockDiretrizes[2]],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Aceitar apenas CRM ativo')).toBeInTheDocument()
    })
  })

  it('deve exibir conteudo de info adicional', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [mockDiretrizes[3]],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Precisa de titulo')).toBeInTheDocument()
    })
  })

  it('deve exibir data de expiracao quando presente', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [mockDiretrizes[2]],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      // The expiry date should show formatted
      expect(screen.queryByText('Nao expira')).not.toBeInTheDocument()
    })
  })

  it('deve exibir "Nao expira" quando sem data de expiracao', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [mockDiretrizes[4]],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Nao expira')).toBeInTheDocument()
    })
  })

  it('deve renderizar escopo vaga sem dados', async () => {
    const vagaSemDados = {
      ...mockDiretrizes[0],
      vagas: null,
    }

    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [vagaSemDados],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Vaga')).toBeInTheDocument()
    })
  })

  it('deve renderizar escopo medico sem dados', async () => {
    const medicoSemDados = {
      ...mockDiretrizes[1],
      clientes: null,
    }

    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [medicoSemDados],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Medico')).toBeInTheDocument()
    })
  })

  it('deve renderizar escopo hospital sem dados', async () => {
    const hospitalSemDados = {
      ...mockDiretrizes[2],
      hospitais: null,
    }

    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [hospitalSemDados],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital')).toBeInTheDocument()
    })
  })

  it('deve renderizar escopo especialidade sem dados', async () => {
    const espSemDados = {
      ...mockDiretrizes[3],
      especialidades: null,
    }

    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [espSemDados],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Especialidade')).toBeInTheDocument()
    })
  })

  it('deve renderizar margem_negociacao sem valor nem percentual', async () => {
    const margemVazia = {
      ...mockDiretrizes[0],
      conteudo: {},
    }

    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [margemVazia],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      // Falls through to JSON.stringify
      expect(screen.getByText('{}')).toBeInTheDocument()
    })
  })

  it('deve mudar para aba historico e recarregar', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/diretrizes?status=ativa')
    })

    const historicoTab = screen.getByRole('tab', { name: /Historico/ })
    await userEvent.click(historicoTab)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/diretrizes?status=expirada,cancelada')
    })
  })

  it('deve renderizar com data de expiracao no passado (expirada)', async () => {
    const diretrizExpirada = {
      ...mockDiretrizes[2],
      expira_em: '2020-01-01T12:00:00Z', // Past date
    }

    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [diretrizExpirada],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      // Should render formatted date (dd/MM HH:mm), not "Nao expira"
      expect(screen.queryByText('Nao expira')).not.toBeInTheDocument()
      // The expired date should have the error color class
      expect(screen.getByText(/01\/01/)).toBeInTheDocument()
    })
  })

  it('deve renderizar diretrizes sem criado_em', async () => {
    const semData = {
      ...mockDiretrizes[4],
      criado_em: '',
    }

    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => [semData],
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('-')).toBeInTheDocument()
    })
  })

  it('deve tratar resposta nao-array como array vazio', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => 'not-an-array',
    } as Response)

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Nenhuma instrucao encontrada')).toBeInTheDocument()
    })
  })
})
