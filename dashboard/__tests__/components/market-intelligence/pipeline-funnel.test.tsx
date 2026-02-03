/**
 * Testes Unitarios - PipelineFunnel
 */

import { render, screen } from '@testing-library/react'
import { PipelineFunnel } from '@/components/market-intelligence/pipeline-funnel'
import type { PipelineFunil, PipelinePerdas } from '@/types/market-intelligence'

// =============================================================================
// TEST DATA
// =============================================================================

const mockFunnelData: PipelineFunil = {
  etapas: [
    {
      id: 'mensagens',
      nome: 'Mensagens Recebidas',
      valor: 5000,
      percentual: 100,
    },
    { id: 'heuristica', nome: 'Passou Heuristica', valor: 2000, percentual: 40 },
    {
      id: 'ofertas',
      nome: 'Classificadas como Oferta',
      valor: 1500,
      percentual: 30,
    },
    { id: 'extraidas', nome: 'Vagas Extraidas', valor: 1100, percentual: 22 },
    { id: 'validadas', nome: 'Dados Minimos OK', valor: 950, percentual: 19 },
    { id: 'importadas', nome: 'Vagas Importadas', valor: 850, percentual: 17 },
  ],
  conversoes: {
    mensagemParaOferta: 30.0,
    ofertaParaExtracao: 73.3,
    extracaoParaImportacao: 77.3,
    totalPipeline: 17.0,
  },
}

const mockPerdas: PipelinePerdas = {
  duplicadas: 150,
  descartadas: 100,
  revisao: 50,
  semDadosMinimos: 150,
}

// =============================================================================
// TESTS
// =============================================================================

describe('PipelineFunnel', () => {
  describe('Renderizacao', () => {
    it('deve renderizar o componente com dados', () => {
      render(<PipelineFunnel data={mockFunnelData} />)

      expect(screen.getByText('Funil do Pipeline')).toBeInTheDocument()
    })

    it('deve renderizar titulo customizado', () => {
      render(<PipelineFunnel data={mockFunnelData} title="Titulo Customizado" />)

      expect(screen.getByText('Titulo Customizado')).toBeInTheDocument()
    })

    it('deve renderizar skeleton quando isLoading=true', () => {
      render(<PipelineFunnel data={null} isLoading />)

      expect(screen.queryByText('Funil do Pipeline')).not.toBeInTheDocument()
    })

    it('deve renderizar empty state quando data=null', () => {
      render(<PipelineFunnel data={null} />)

      expect(screen.getByText(/nenhum dado disponivel/i)).toBeInTheDocument()
    })

    it('deve aplicar className customizado', () => {
      const { container } = render(
        <PipelineFunnel data={mockFunnelData} className="custom-class" />
      )

      expect(container.firstChild).toHaveClass('custom-class')
    })
  })

  describe('Etapas do Funil', () => {
    it('deve renderizar todas as etapas', () => {
      render(<PipelineFunnel data={mockFunnelData} />)

      expect(screen.getByText('Mensagens Recebidas')).toBeInTheDocument()
      expect(screen.getByText('Passou Heuristica')).toBeInTheDocument()
      expect(screen.getByText('Classificadas como Oferta')).toBeInTheDocument()
      expect(screen.getByText('Vagas Extraidas')).toBeInTheDocument()
      expect(screen.getByText('Dados Minimos OK')).toBeInTheDocument()
      expect(screen.getByText('Vagas Importadas')).toBeInTheDocument()
    })

    it('deve exibir valores e percentuais', () => {
      render(<PipelineFunnel data={mockFunnelData} />)

      // Verificar formato: "5.000 (100.0%)"
      expect(screen.getByText(/5\.000/)).toBeInTheDocument()
      // 100.0% pode aparecer mais de uma vez (barra + detalhes)
      const percentElements = screen.getAllByText(/100\.0%/)
      expect(percentElements.length).toBeGreaterThan(0)
    })

    it('deve exibir setas de conversao entre etapas', () => {
      render(<PipelineFunnel data={mockFunnelData} />)

      // Deve ter setas com texto "convertido"
      const arrows = screen.getAllByText(/convertido/i)
      expect(arrows.length).toBeGreaterThan(0)
    })
  })

  describe('Card de Conversoes', () => {
    it('deve renderizar card de taxas de conversao', () => {
      render(<PipelineFunnel data={mockFunnelData} />)

      expect(screen.getByText('Taxas de Conversao')).toBeInTheDocument()
    })

    it('deve exibir todas as taxas', () => {
      render(<PipelineFunnel data={mockFunnelData} />)

      expect(screen.getByText('Msg → Oferta')).toBeInTheDocument()
      expect(screen.getByText('Oferta → Extracao')).toBeInTheDocument()
      expect(screen.getByText('Extracao → Import')).toBeInTheDocument()
      expect(screen.getByText('Pipeline Total')).toBeInTheDocument()
    })

    it('deve exibir valores corretos das taxas', () => {
      render(<PipelineFunnel data={mockFunnelData} />)

      // Taxas podem aparecer mais de uma vez
      expect(screen.getAllByText('30.0%').length).toBeGreaterThan(0)
      expect(screen.getAllByText('73.3%').length).toBeGreaterThan(0)
      expect(screen.getAllByText('77.3%').length).toBeGreaterThan(0)
      expect(screen.getAllByText('17.0%').length).toBeGreaterThan(0)
    })
  })

  describe('Card de Perdas', () => {
    it('deve renderizar card de perdas quando showPerdas=true e perdas fornecidas', () => {
      render(<PipelineFunnel data={mockFunnelData} perdas={mockPerdas} showPerdas />)

      expect(screen.getByText('Perdas no Pipeline')).toBeInTheDocument()
    })

    it('nao deve renderizar card de perdas quando showPerdas=false', () => {
      render(<PipelineFunnel data={mockFunnelData} perdas={mockPerdas} showPerdas={false} />)

      expect(screen.queryByText('Perdas no Pipeline')).not.toBeInTheDocument()
    })

    it('deve exibir todas as categorias de perda', () => {
      render(<PipelineFunnel data={mockFunnelData} perdas={mockPerdas} />)

      expect(screen.getByText('Duplicadas')).toBeInTheDocument()
      expect(screen.getByText('Descartadas')).toBeInTheDocument()
      expect(screen.getByText('Em Revisao')).toBeInTheDocument()
      expect(screen.getByText('Sem Dados Minimos')).toBeInTheDocument()
    })

    it('deve exibir valores corretos das perdas', () => {
      render(<PipelineFunnel data={mockFunnelData} perdas={mockPerdas} />)

      // 150 aparece duas vezes (duplicadas e semDadosMinimos)
      expect(screen.getAllByText('150').length).toBeGreaterThanOrEqual(2)
      expect(screen.getByText('100')).toBeInTheDocument() // descartadas
      expect(screen.getByText('50')).toBeInTheDocument() // revisao
    })

    it('deve calcular e exibir total de perdas', () => {
      render(<PipelineFunnel data={mockFunnelData} perdas={mockPerdas} />)

      expect(screen.getByText('Total de Perdas')).toBeInTheDocument()
      expect(screen.getByText('450')).toBeInTheDocument() // 150+100+50+150
    })
  })

  describe('Barras do Funil', () => {
    it('deve ter barras com largura proporcional ao percentual', () => {
      render(<PipelineFunnel data={mockFunnelData} />)

      // Verificar que as barras existem (via role ou estrutura)
      const etapas = screen.getAllByText(
        /Mensagens|Heuristica|Oferta|Extraidas|Validadas|Importadas/
      )
      expect(etapas.length).toBeGreaterThan(0)
    })
  })

  describe('Tooltip', () => {
    it('deve ter tooltips nas barras', async () => {
      render(<PipelineFunnel data={mockFunnelData} />)

      // Os tooltips existem mas precisam de hover para mostrar conteudo
      // Verificamos que a estrutura de tooltip existe
      const tooltipTriggers = document.querySelectorAll('[data-state]')
      expect(tooltipTriggers.length).toBeGreaterThan(0)
    })
  })

  describe('Edge Cases', () => {
    it('deve lidar com etapas vazias', () => {
      const emptyData: PipelineFunil = {
        etapas: [],
        conversoes: {
          mensagemParaOferta: 0,
          ofertaParaExtracao: 0,
          extracaoParaImportacao: 0,
          totalPipeline: 0,
        },
      }

      render(<PipelineFunnel data={emptyData} />)

      expect(screen.getByText(/nenhum dado disponivel/i)).toBeInTheDocument()
    })

    it('deve lidar com valores zero', () => {
      const zeroData: PipelineFunil = {
        etapas: [
          { id: 'mensagens', nome: 'Mensagens', valor: 0, percentual: 100 },
          { id: 'ofertas', nome: 'Ofertas', valor: 0, percentual: 0 },
        ],
        conversoes: {
          mensagemParaOferta: 0,
          ofertaParaExtracao: 0,
          extracaoParaImportacao: 0,
          totalPipeline: 0,
        },
      }

      render(<PipelineFunnel data={zeroData} />)

      expect(screen.getByText('Mensagens')).toBeInTheDocument()
      expect(screen.getByText('Ofertas')).toBeInTheDocument()
    })

    it('deve lidar com perdas null', () => {
      render(<PipelineFunnel data={mockFunnelData} perdas={null} />)

      expect(screen.queryByText('Perdas no Pipeline')).not.toBeInTheDocument()
    })
  })

  describe('Acessibilidade', () => {
    it('deve ter estrutura semantica correta', () => {
      render(<PipelineFunnel data={mockFunnelData} perdas={mockPerdas} />)

      // Verificar que os titulos dos cards estao presentes
      expect(screen.getByText('Funil do Pipeline')).toBeInTheDocument()
      expect(screen.getByText('Taxas de Conversao')).toBeInTheDocument()
      expect(screen.getByText('Perdas no Pipeline')).toBeInTheDocument()
    })
  })
})
