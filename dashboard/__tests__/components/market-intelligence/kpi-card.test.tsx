/**
 * Testes Unitarios - KPICard
 */

import { render, screen } from '@testing-library/react'
import { KPICard, KPICardSkeleton } from '@/components/market-intelligence/kpi-card'
import { Activity } from 'lucide-react'

describe('KPICard', () => {
  const defaultProps = {
    titulo: 'Grupos Ativos',
    valor: 50,
    icone: <Activity data-testid="icon" />,
  }

  describe('Renderizacao Basica', () => {
    it('deve renderizar titulo', () => {
      render(<KPICard {...defaultProps} />)
      expect(screen.getByText('Grupos Ativos')).toBeInTheDocument()
    })

    it('deve renderizar valor numerico', () => {
      render(<KPICard {...defaultProps} valor={1234} />)
      expect(screen.getByText('1234')).toBeInTheDocument()
    })

    it('deve renderizar valor string', () => {
      render(<KPICard {...defaultProps} valor="R$ 1.500" />)
      expect(screen.getByText('R$ 1.500')).toBeInTheDocument()
    })

    it('deve usar valorFormatado quando fornecido', () => {
      render(<KPICard {...defaultProps} valor={1500} valorFormatado="1.5K" />)
      expect(screen.getByText('1.5K')).toBeInTheDocument()
      expect(screen.queryByText('1500')).not.toBeInTheDocument()
    })

    it('deve renderizar icone', () => {
      render(<KPICard {...defaultProps} />)
      expect(screen.getByTestId('icon')).toBeInTheDocument()
    })

    it('deve renderizar subtitulo quando fornecido', () => {
      render(<KPICard {...defaultProps} subtitulo="vs periodo anterior" />)
      expect(screen.getByText('vs periodo anterior')).toBeInTheDocument()
    })

    it('nao deve renderizar subtitulo quando nao fornecido', () => {
      render(<KPICard {...defaultProps} />)
      expect(screen.queryByText('vs periodo anterior')).not.toBeInTheDocument()
    })
  })

  describe('Variacao', () => {
    it('deve renderizar variacao positiva com icone up', () => {
      render(<KPICard {...defaultProps} variacao={12.5} variacaoTipo="up" />)
      expect(screen.getByText('+12.5%')).toBeInTheDocument()
      expect(screen.getByRole('status', { name: /aumento/i })).toBeInTheDocument()
    })

    it('deve renderizar variacao negativa com icone down', () => {
      render(<KPICard {...defaultProps} variacao={-8.3} variacaoTipo="down" />)
      expect(screen.getByText('-8.3%')).toBeInTheDocument()
      expect(screen.getByRole('status', { name: /reducao/i })).toBeInTheDocument()
    })

    it('deve renderizar variacao estavel', () => {
      render(<KPICard {...defaultProps} variacao={0.5} variacaoTipo="stable" />)
      expect(screen.getByText('+0.5%')).toBeInTheDocument()
      expect(screen.getByRole('status', { name: /estavel/i })).toBeInTheDocument()
    })

    it('nao deve renderizar variacao quando null', () => {
      render(<KPICard {...defaultProps} variacao={null} variacaoTipo={null} />)
      expect(screen.queryByText('%')).not.toBeInTheDocument()
    })

    it('nao deve renderizar variacao quando nao fornecido', () => {
      render(<KPICard {...defaultProps} />)
      // Should only find the status indicator, not the variation percentage
      const statusElements = screen.getAllByRole('status')
      expect(statusElements.length).toBe(1) // Only the status indicator
    })
  })

  describe('Sparkline (Tendencia)', () => {
    it('deve renderizar sparkline quando tendencia fornecida', () => {
      render(<KPICard {...defaultProps} tendencia={[10, 20, 30, 40, 50]} />)
      expect(screen.getByRole('img', { name: /tendencia/i })).toBeInTheDocument()
    })

    it('nao deve renderizar sparkline com menos de 2 pontos', () => {
      render(<KPICard {...defaultProps} tendencia={[10]} />)
      expect(screen.queryByRole('img', { name: /tendencia/i })).not.toBeInTheDocument()
    })

    it('nao deve renderizar sparkline quando array vazio', () => {
      render(<KPICard {...defaultProps} tendencia={[]} />)
      expect(screen.queryByRole('img', { name: /tendencia/i })).not.toBeInTheDocument()
    })

    it('nao deve renderizar sparkline quando nao fornecido', () => {
      render(<KPICard {...defaultProps} />)
      expect(screen.queryByRole('img', { name: /tendencia/i })).not.toBeInTheDocument()
    })
  })

  describe('Status', () => {
    it('deve renderizar indicador de status success', () => {
      render(<KPICard {...defaultProps} status="success" />)
      expect(screen.getByRole('status', { name: /success/i })).toBeInTheDocument()
    })

    it('deve renderizar indicador de status warning', () => {
      render(<KPICard {...defaultProps} status="warning" />)
      expect(screen.getByRole('status', { name: /warning/i })).toBeInTheDocument()
    })

    it('deve renderizar indicador de status danger', () => {
      render(<KPICard {...defaultProps} status="danger" />)
      expect(screen.getByRole('status', { name: /danger/i })).toBeInTheDocument()
    })

    it('deve usar neutral como default', () => {
      render(<KPICard {...defaultProps} />)
      expect(screen.getByRole('status', { name: /neutral/i })).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('deve renderizar skeleton quando loading=true', () => {
      render(<KPICard {...defaultProps} loading={true} />)

      // Nao deve mostrar conteudo real
      expect(screen.queryByText('Grupos Ativos')).not.toBeInTheDocument()
      expect(screen.queryByText('50')).not.toBeInTheDocument()
    })

    it('deve renderizar conteudo quando loading=false', () => {
      render(<KPICard {...defaultProps} loading={false} />)
      expect(screen.getByText('Grupos Ativos')).toBeInTheDocument()
      expect(screen.getByText('50')).toBeInTheDocument()
    })
  })

  describe('Acessibilidade', () => {
    it('deve ter label acessivel no sparkline', () => {
      render(<KPICard {...defaultProps} tendencia={[10, 20, 30]} />)
      expect(screen.getByRole('img')).toHaveAccessibleName(/tendencia/i)
    })

    it('deve ter label acessivel na variacao', () => {
      render(<KPICard {...defaultProps} variacao={10} variacaoTipo="up" />)
      expect(screen.getByRole('status', { name: /aumento de 10%/i })).toBeInTheDocument()
    })

    it('deve ter label acessivel no status', () => {
      render(<KPICard {...defaultProps} status="success" />)
      expect(screen.getByRole('status', { name: /status: success/i })).toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('deve aplicar className customizado', () => {
      const { container } = render(<KPICard {...defaultProps} className="custom-class" />)
      expect(container.firstChild).toHaveClass('custom-class')
    })
  })
})

describe('KPICardSkeleton', () => {
  it('deve renderizar skeleton', () => {
    render(<KPICardSkeleton />)
    // Skeleton nao tem texto visivel, verificar estrutura
    const card = document.querySelector('[class*="card"]')
    expect(card).toBeInTheDocument()
  })
})
