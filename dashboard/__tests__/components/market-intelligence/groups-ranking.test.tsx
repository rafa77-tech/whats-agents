/**
 * Testes Unitarios - GroupsRanking
 */

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GroupsRanking } from '@/components/market-intelligence/groups-ranking'
import type { GrupoRanking } from '@/types/market-intelligence'

// =============================================================================
// TEST DATA
// =============================================================================

const mockGrupos: GrupoRanking[] = [
  {
    grupoId: 'g1',
    grupoNome: 'Grupo Cardiologia SP',
    grupoTipo: 'especialidade',
    grupoRegiao: 'Sao Paulo',
    grupoAtivo: true,
    mensagens30d: 500,
    ofertas30d: 100,
    vagasExtraidas30d: 80,
    vagasImportadas30d: 60,
    confiancaMedia30d: 0.85,
    valorMedio30d: 250000, // R$ 2.500,00 em centavos
    scoreQualidade: 85,
    ultimaMensagemEm: '2026-02-01T10:00:00Z',
    ultimaVagaEm: '2026-02-01T09:00:00Z',
    calculatedAt: '2026-02-02T00:00:00Z',
  },
  {
    grupoId: 'g2',
    grupoNome: 'Grupo Pediatria RJ',
    grupoTipo: 'especialidade',
    grupoRegiao: 'Rio de Janeiro',
    grupoAtivo: true,
    mensagens30d: 300,
    ofertas30d: 50,
    vagasExtraidas30d: 40,
    vagasImportadas30d: 30,
    confiancaMedia30d: 0.75,
    valorMedio30d: 180000,
    scoreQualidade: 55,
    ultimaMensagemEm: '2026-01-30T10:00:00Z',
    ultimaVagaEm: '2026-01-28T09:00:00Z',
    calculatedAt: '2026-02-02T00:00:00Z',
  },
  {
    grupoId: 'g3',
    grupoNome: 'Grupo Plantoes MG',
    grupoTipo: 'geral',
    grupoRegiao: 'Minas Gerais',
    grupoAtivo: false,
    mensagens30d: 100,
    ofertas30d: 20,
    vagasExtraidas30d: 15,
    vagasImportadas30d: 10,
    confiancaMedia30d: 0.65,
    valorMedio30d: 150000,
    scoreQualidade: 30,
    ultimaMensagemEm: '2026-01-20T10:00:00Z',
    ultimaVagaEm: '2026-01-15T09:00:00Z',
    calculatedAt: '2026-02-02T00:00:00Z',
  },
]

// Gerar mais dados para testes de paginacao
function generateMockGrupos(count: number): GrupoRanking[] {
  return Array.from({ length: count }, (_, i) => ({
    grupoId: `g${i + 1}`,
    grupoNome: `Grupo ${i + 1}`,
    grupoTipo: 'geral',
    grupoRegiao: `Regiao ${i + 1}`,
    grupoAtivo: i % 2 === 0,
    mensagens30d: 100 + i * 10,
    ofertas30d: 20 + i * 2,
    vagasExtraidas30d: 15 + i,
    vagasImportadas30d: 10 + i,
    confiancaMedia30d: 0.5 + (i % 5) * 0.1,
    valorMedio30d: 100000 + i * 10000,
    scoreQualidade: 20 + (i % 8) * 10,
    ultimaMensagemEm: new Date(Date.now() - i * 86400000).toISOString(),
    ultimaVagaEm: new Date(Date.now() - i * 86400000 * 2).toISOString(),
    calculatedAt: new Date().toISOString(),
  }))
}

// =============================================================================
// TESTS
// =============================================================================

describe('GroupsRanking', () => {
  describe('Renderizacao', () => {
    it('deve renderizar o componente com dados', () => {
      render(<GroupsRanking data={mockGrupos} />)

      expect(screen.getByText('Ranking de Grupos')).toBeInTheDocument()
    })

    it('deve renderizar titulo customizado', () => {
      render(<GroupsRanking data={mockGrupos} title="Top Grupos" />)

      expect(screen.getByText('Top Grupos')).toBeInTheDocument()
    })

    it('deve renderizar skeleton quando isLoading=true', () => {
      render(<GroupsRanking data={null} isLoading />)

      expect(screen.queryByText('Ranking de Grupos')).not.toBeInTheDocument()
    })

    it('deve renderizar empty state quando data=null', () => {
      render(<GroupsRanking data={null} />)

      expect(screen.getByText(/nenhum grupo encontrado/i)).toBeInTheDocument()
    })

    it('deve renderizar empty state quando data=[]', () => {
      render(<GroupsRanking data={[]} />)

      expect(screen.getByText(/nenhum grupo encontrado/i)).toBeInTheDocument()
    })

    it('deve aplicar className customizado', () => {
      const { container } = render(<GroupsRanking data={mockGrupos} className="custom-class" />)

      expect(container.firstChild).toHaveClass('custom-class')
    })
  })

  describe('Tabela de Dados', () => {
    it('deve renderizar todos os grupos', () => {
      render(<GroupsRanking data={mockGrupos} />)

      expect(screen.getByText('Grupo Cardiologia SP')).toBeInTheDocument()
      expect(screen.getByText('Grupo Pediatria RJ')).toBeInTheDocument()
      expect(screen.getByText('Grupo Plantoes MG')).toBeInTheDocument()
    })

    it('deve exibir regioes dos grupos', () => {
      render(<GroupsRanking data={mockGrupos} />)

      expect(screen.getByText('Sao Paulo')).toBeInTheDocument()
      expect(screen.getByText('Rio de Janeiro')).toBeInTheDocument()
      expect(screen.getByText('Minas Gerais')).toBeInTheDocument()
    })

    it('deve exibir posicoes na tabela', () => {
      render(<GroupsRanking data={mockGrupos} />)

      // Posicoes 1, 2, 3
      const cells = screen.getAllByRole('cell')
      const positions = cells.filter(
        (cell) => cell.textContent === '1' || cell.textContent === '2' || cell.textContent === '3'
      )
      expect(positions.length).toBeGreaterThanOrEqual(3)
    })

    it('deve exibir scores com badges coloridos', () => {
      render(<GroupsRanking data={mockGrupos} />)

      // Score 85 (verde), 55 (amarelo), 30 (vermelho)
      // 30 aparece tanto como score quanto como vagas, usar getAllByText
      expect(screen.getByText('85')).toBeInTheDocument()
      expect(screen.getByText('55')).toBeInTheDocument()
      expect(screen.getAllByText('30').length).toBeGreaterThanOrEqual(1)
    })

    it('deve exibir vagas importadas', () => {
      render(<GroupsRanking data={mockGrupos} />)

      // Vagas: 60, 30, 10
      // 30 aparece tanto como score quanto como vagas, usar getAllByText
      expect(screen.getByText('60')).toBeInTheDocument()
      expect(screen.getAllByText('30').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('10')).toBeInTheDocument()
    })

    it('deve exibir valores medios formatados', () => {
      render(<GroupsRanking data={mockGrupos} />)

      // R$ 2.500,00 aparece como R$ 2.500
      expect(screen.getByText(/R\$\s*2\.500/)).toBeInTheDocument()
    })

    it('deve exibir datas relativas', () => {
      render(<GroupsRanking data={mockGrupos} />)

      // Verificar que algum elemento de data existe
      const dateElements = screen.getAllByText(/Hoje|Ontem|dias|sem|Nunca/)
      expect(dateElements.length).toBeGreaterThan(0)
    })
  })

  describe('Status dos Grupos', () => {
    it('deve mostrar icone de ativo para grupos ativos', () => {
      render(<GroupsRanking data={mockGrupos} />)

      // Verificar aria-labels
      const activeIcons = screen.getAllByLabelText('Grupo ativo')
      expect(activeIcons.length).toBe(2) // g1 e g2 ativos
    })

    it('deve mostrar icone de inativo para grupos inativos', () => {
      render(<GroupsRanking data={mockGrupos} />)

      const inactiveIcons = screen.getAllByLabelText('Grupo inativo')
      expect(inactiveIcons.length).toBe(1) // g3 inativo
    })
  })

  describe('Ordenacao', () => {
    it('deve ordenar por score por padrao (desc)', () => {
      render(<GroupsRanking data={mockGrupos} />)

      const rows = screen.getAllByRole('row')
      // Primeira linha e header, depois dados
      const firstDataRow = rows[1] as HTMLElement
      expect(within(firstDataRow).getByText('Grupo Cardiologia SP')).toBeInTheDocument()
    })

    it('deve alternar ordenacao ao clicar no header Score', async () => {
      const user = userEvent.setup()
      render(<GroupsRanking data={mockGrupos} />)

      const scoreButton = screen.getByRole('button', { name: /score/i })
      await user.click(scoreButton)

      // Deve inverter para asc
      const rows = screen.getAllByRole('row')
      const firstDataRow = rows[1] as HTMLElement
      expect(within(firstDataRow).getByText('Grupo Plantoes MG')).toBeInTheDocument()
    })

    it('deve ordenar por vagas ao clicar no header Vagas', async () => {
      const user = userEvent.setup()
      render(<GroupsRanking data={mockGrupos} />)

      const vagasButton = screen.getByRole('button', { name: /vagas/i })
      await user.click(vagasButton)

      // Ordenado por vagas desc
      const rows = screen.getAllByRole('row')
      const firstDataRow = rows[1] as HTMLElement
      expect(within(firstDataRow).getByText('60')).toBeInTheDocument()
    })

    it('deve ordenar por valor medio ao clicar no header', async () => {
      const user = userEvent.setup()
      render(<GroupsRanking data={mockGrupos} />)

      const valorButton = screen.getByRole('button', { name: /valor/i })
      await user.click(valorButton)

      // Ordenado por valor desc
      const rows = screen.getAllByRole('row')
      const firstDataRow = rows[1] as HTMLElement
      // Maior valor e R$ 2.500
      expect(within(firstDataRow).getByText(/R\$\s*2\.500/)).toBeInTheDocument()
    })

    it('deve ordenar por ultima vaga ao clicar no header', async () => {
      const user = userEvent.setup()
      render(<GroupsRanking data={mockGrupos} />)

      const dataButton = screen.getByRole('button', { name: /ult\. vaga/i })
      await user.click(dataButton)

      // Ordenado por data desc (mais recente primeiro)
      const rows = screen.getAllByRole('row')
      const firstDataRow = rows[1] as HTMLElement
      expect(within(firstDataRow).getByText('Grupo Cardiologia SP')).toBeInTheDocument()
    })
  })

  describe('Paginacao', () => {
    it('nao deve mostrar paginacao quando limit esta definido', () => {
      const manyGrupos = generateMockGrupos(25)
      render(<GroupsRanking data={manyGrupos} limit={5} />)

      expect(screen.queryByText(/mostrando/i)).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /anterior/i })).not.toBeInTheDocument()
    })

    it('deve mostrar paginacao quando ha mais de 10 itens', () => {
      const manyGrupos = generateMockGrupos(25)
      render(<GroupsRanking data={manyGrupos} />)

      expect(screen.getByText(/mostrando/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /anterior/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /proximo/i })).toBeInTheDocument()
    })

    it('deve navegar para proxima pagina', async () => {
      const user = userEvent.setup()
      const manyGrupos = generateMockGrupos(25)
      render(<GroupsRanking data={manyGrupos} />)

      const nextButton = screen.getByRole('button', { name: /proximo/i })
      await user.click(nextButton)

      expect(screen.getByText(/mostrando 11/i)).toBeInTheDocument()
    })

    it('deve navegar para pagina anterior', async () => {
      const user = userEvent.setup()
      const manyGrupos = generateMockGrupos(25)
      render(<GroupsRanking data={manyGrupos} />)

      const nextButton = screen.getByRole('button', { name: /proximo/i })
      await user.click(nextButton)

      const prevButton = screen.getByRole('button', { name: /anterior/i })
      await user.click(prevButton)

      expect(screen.getByText(/mostrando 1/i)).toBeInTheDocument()
    })

    it('deve desabilitar botao anterior na primeira pagina', () => {
      const manyGrupos = generateMockGrupos(25)
      render(<GroupsRanking data={manyGrupos} />)

      const prevButton = screen.getByRole('button', { name: /anterior/i })
      expect(prevButton).toBeDisabled()
    })

    it('deve desabilitar botao proximo na ultima pagina', async () => {
      const user = userEvent.setup()
      const manyGrupos = generateMockGrupos(15) // 2 paginas
      render(<GroupsRanking data={manyGrupos} />)

      const nextButton = screen.getByRole('button', { name: /proximo/i })
      await user.click(nextButton)

      expect(nextButton).toBeDisabled()
    })

    it('deve resetar para primeira pagina ao mudar ordenacao', async () => {
      const user = userEvent.setup()
      const manyGrupos = generateMockGrupos(25)
      render(<GroupsRanking data={manyGrupos} />)

      // Ir para pagina 2
      const nextButton = screen.getByRole('button', { name: /proximo/i })
      await user.click(nextButton)
      expect(screen.getByText(/mostrando 11/i)).toBeInTheDocument()

      // Mudar ordenacao
      const vagasButton = screen.getByRole('button', { name: /vagas/i })
      await user.click(vagasButton)

      // Deve voltar para pagina 1
      expect(screen.getByText(/mostrando 1/i)).toBeInTheDocument()
    })
  })

  describe('Limit', () => {
    it('deve limitar quantidade de itens exibidos', () => {
      render(<GroupsRanking data={mockGrupos} limit={2} />)

      const rows = screen.getAllByRole('row')
      // Header + 2 data rows
      expect(rows.length).toBe(3)
    })

    it('deve exibir todos quando limit maior que dados', () => {
      render(<GroupsRanking data={mockGrupos} limit={10} />)

      const rows = screen.getAllByRole('row')
      // Header + 3 data rows
      expect(rows.length).toBe(4)
    })
  })

  describe('Click Handler', () => {
    it('deve chamar onGroupClick ao clicar em uma linha', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()
      render(<GroupsRanking data={mockGrupos} onGroupClick={handleClick} />)

      const rows = screen.getAllByRole('row')
      await user.click(rows[1] as HTMLElement) // Primeira linha de dados

      expect(handleClick).toHaveBeenCalledWith('g1')
    })

    it('deve ter cursor pointer quando onGroupClick definido', () => {
      render(<GroupsRanking data={mockGrupos} onGroupClick={() => {}} />)

      const rows = screen.getAllByRole('row')
      expect(rows[1] as HTMLElement).toHaveClass('cursor-pointer')
    })

    it('nao deve ter cursor pointer quando onGroupClick nao definido', () => {
      render(<GroupsRanking data={mockGrupos} />)

      const rows = screen.getAllByRole('row')
      expect(rows[1] as HTMLElement).not.toHaveClass('cursor-pointer')
    })
  })

  describe('Edge Cases', () => {
    it('deve lidar com valores null em valorMedio', () => {
      const baseGrupo = mockGrupos[0]!
      const gruposSemValor: GrupoRanking[] = [
        {
          ...baseGrupo,
          valorMedio30d: null,
        },
      ]

      render(<GroupsRanking data={gruposSemValor} />)

      expect(screen.getByText('-')).toBeInTheDocument()
    })

    it('deve lidar com ultimaVagaEm null', () => {
      const baseGrupo = mockGrupos[0]!
      const gruposSemData: GrupoRanking[] = [
        {
          ...baseGrupo,
          ultimaVagaEm: null,
        },
      ]

      render(<GroupsRanking data={gruposSemData} />)

      expect(screen.getByText('Nunca')).toBeInTheDocument()
    })

    it('deve lidar com regiao null', () => {
      const baseGrupo = mockGrupos[0]!
      const gruposSemRegiao: GrupoRanking[] = [
        {
          ...baseGrupo,
          grupoRegiao: null,
        },
      ]

      render(<GroupsRanking data={gruposSemRegiao} />)

      expect(screen.getByText('Grupo Cardiologia SP')).toBeInTheDocument()
      expect(screen.queryByText('Sao Paulo')).not.toBeInTheDocument()
    })
  })

  describe('Acessibilidade', () => {
    it('deve ter estrutura de tabela semantica', () => {
      render(<GroupsRanking data={mockGrupos} />)

      expect(screen.getByRole('table')).toBeInTheDocument()
      expect(screen.getAllByRole('columnheader').length).toBeGreaterThan(0)
      expect(screen.getAllByRole('row').length).toBeGreaterThan(1)
    })

    it('deve ter aria-labels nos icones de status', () => {
      render(<GroupsRanking data={mockGrupos} />)

      expect(screen.getAllByLabelText(/grupo ativo|grupo inativo/i).length).toBe(3)
    })
  })
})
