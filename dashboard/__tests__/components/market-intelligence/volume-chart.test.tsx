/**
 * Testes Unitarios - VolumeChart
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { VolumeChart } from '@/components/market-intelligence/volume-chart'
import type { VolumeDataPoint } from '@/types/market-intelligence'
import React from 'react'

// Mock do Recharts para evitar problemas com ResponsiveContainer
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  AreaChart: ({ children, data }: { children: React.ReactNode; data: unknown[] }) => (
    <div data-testid="area-chart" data-points={data.length}>
      {children}
    </div>
  ),
  Area: ({ dataKey, name }: { dataKey: string; name: string }) => (
    <div data-testid={`area-${dataKey}`} data-name={name} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}))

// =============================================================================
// TEST DATA
// =============================================================================

const mockData: VolumeDataPoint[] = [
  {
    data: '2024-01-01',
    mensagens: 100,
    ofertas: 30,
    vagasExtraidas: 20,
    vagasImportadas: 15,
  },
  {
    data: '2024-01-02',
    mensagens: 150,
    ofertas: 45,
    vagasExtraidas: 30,
    vagasImportadas: 22,
  },
  {
    data: '2024-01-03',
    mensagens: 120,
    ofertas: 36,
    vagasExtraidas: 25,
    vagasImportadas: 18,
  },
]

// =============================================================================
// TESTS
// =============================================================================

describe('VolumeChart', () => {
  describe('Renderizacao', () => {
    it('deve renderizar o componente com dados', () => {
      render(<VolumeChart data={mockData} />)

      expect(screen.getByText('Volume ao Longo do Tempo')).toBeInTheDocument()
      expect(screen.getByTestId('area-chart')).toBeInTheDocument()
    })

    it('deve renderizar titulo customizado', () => {
      render(<VolumeChart data={mockData} title="Titulo Customizado" />)

      expect(screen.getByText('Titulo Customizado')).toBeInTheDocument()
    })

    it('deve renderizar skeleton quando isLoading=true', () => {
      render(<VolumeChart data={null} isLoading />)

      // Skeleton nao tem o titulo
      expect(screen.queryByText('Volume ao Longo do Tempo')).not.toBeInTheDocument()
    })

    it('deve renderizar empty state quando data=null', () => {
      render(<VolumeChart data={null} />)

      expect(screen.getByText(/nenhum dado disponivel/i)).toBeInTheDocument()
    })

    it('deve renderizar empty state quando data=[]', () => {
      render(<VolumeChart data={[]} />)

      expect(screen.getByText(/nenhum dado disponivel/i)).toBeInTheDocument()
    })

    it('deve aplicar className customizado', () => {
      const { container } = render(<VolumeChart data={mockData} className="custom-class" />)

      expect(container.firstChild).toHaveClass('custom-class')
    })
  })

  describe('Legenda Interativa', () => {
    it('deve renderizar botoes de legenda para cada serie', () => {
      render(<VolumeChart data={mockData} />)

      expect(screen.getByRole('button', { name: /mensagens/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /ofertas/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /vagas extraidas/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /vagas importadas/i })).toBeInTheDocument()
    })

    it('deve ter aria-pressed correto nos botoes de legenda', () => {
      render(<VolumeChart data={mockData} />)

      // Mensagens deve estar visivel por default
      const mensagensBtn = screen.getByRole('button', {
        name: /mostrar mensagens|ocultar mensagens/i,
      })
      expect(mensagensBtn).toHaveAttribute('aria-pressed', 'true')
    })

    it('deve toggle visibilidade ao clicar na legenda', () => {
      render(<VolumeChart data={mockData} />)

      // Inicialmente mensagens visivel
      const mensagensBtn = screen.getByRole('button', {
        name: /ocultar mensagens/i,
      })
      expect(mensagensBtn).toHaveAttribute('aria-pressed', 'true')

      // Clicar para ocultar
      fireEvent.click(mensagensBtn)

      // Agora deve estar oculto
      expect(mensagensBtn).toHaveAttribute('aria-pressed', 'false')
    })

    it('nao deve permitir ocultar todas as series', () => {
      render(<VolumeChart data={mockData} />)

      // Ocultar series ate ficar so uma
      const ofertasBtn = screen.getByRole('button', {
        name: /ocultar ofertas/i,
      })
      const importadasBtn = screen.getByRole('button', {
        name: /ocultar vagas importadas/i,
      })

      fireEvent.click(ofertasBtn)
      fireEvent.click(importadasBtn)

      // Agora so mensagens esta visivel
      const mensagensBtn = screen.getByRole('button', {
        name: /ocultar mensagens/i,
      })
      expect(mensagensBtn).toHaveAttribute('aria-pressed', 'true')

      // Tentar ocultar a ultima - nao deve funcionar
      fireEvent.click(mensagensBtn)
      expect(mensagensBtn).toHaveAttribute('aria-pressed', 'true')
    })
  })

  describe('Grafico', () => {
    it('deve passar dados corretos para o grafico', () => {
      render(<VolumeChart data={mockData} />)

      const chart = screen.getByTestId('area-chart')
      expect(chart).toHaveAttribute('data-points', '3')
    })

    it('deve renderizar areas para series visiveis', () => {
      render(<VolumeChart data={mockData} />)

      // Series visiveis por default: mensagens, ofertas, vagasImportadas
      expect(screen.getByTestId('area-mensagens')).toBeInTheDocument()
      expect(screen.getByTestId('area-ofertas')).toBeInTheDocument()
      expect(screen.getByTestId('area-vagasImportadas')).toBeInTheDocument()

      // vagasExtraidas nao e visivel por default
      expect(screen.queryByTestId('area-vagasExtraidas')).not.toBeInTheDocument()
    })

    it('deve renderizar eixos', () => {
      render(<VolumeChart data={mockData} />)

      expect(screen.getByTestId('x-axis')).toBeInTheDocument()
      expect(screen.getByTestId('y-axis')).toBeInTheDocument()
    })

    it('deve renderizar grid', () => {
      render(<VolumeChart data={mockData} />)

      expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument()
    })

    it('deve renderizar tooltip', () => {
      render(<VolumeChart data={mockData} />)

      expect(screen.getByTestId('tooltip')).toBeInTheDocument()
    })
  })

  describe('Acessibilidade', () => {
    it('deve ter labels descritivos nos botoes de legenda', () => {
      render(<VolumeChart data={mockData} />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((btn) => {
        expect(btn).toHaveAttribute('aria-label')
      })
    })

    it('deve ter aria-pressed em todos botoes de toggle', () => {
      render(<VolumeChart data={mockData} />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((btn) => {
        expect(btn).toHaveAttribute('aria-pressed')
      })
    })
  })

  describe('Responsividade', () => {
    it('deve usar ResponsiveContainer', () => {
      render(<VolumeChart data={mockData} />)

      expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    })
  })
})
