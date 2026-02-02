import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueueStatusPanel } from '@/components/health/queue-status-panel'

describe('QueueStatusPanel', () => {
  const mockQueue = {
    pendentes: 5,
    processando: 2,
    processadasPorHora: 120,
    tempoMedioMs: 1500,
  }

  describe('Rendering', () => {
    it('renders panel title', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('Fila de Mensagens')).toBeInTheDocument()
    })

    it('renders panel description', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('Status da fila de processamento')).toBeInTheDocument()
    })
  })

  describe('Pendentes', () => {
    it('displays pendentes label', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('Pendentes')).toBeInTheDocument()
    })

    it('displays pendentes count', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('displays 0 when pendentes is 0', () => {
      const emptyQueue = { ...mockQueue, pendentes: 0 }
      render(<QueueStatusPanel queue={emptyQueue} />)
      const zeros = screen.getAllByText('0')
      expect(zeros.length).toBeGreaterThanOrEqual(1)
    })
  })

  describe('Processando', () => {
    it('displays processando label', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('Processando')).toBeInTheDocument()
    })

    it('displays processando count', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })

  describe('Processadas/h', () => {
    it('displays processadas por hora label', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('Processadas/h')).toBeInTheDocument()
    })

    it('displays processadas por hora value', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('120')).toBeInTheDocument()
    })

    it('displays dash when processadasPorHora is undefined', () => {
      const { processadasPorHora: _, ...queueNoProcessadas } = mockQueue
      render(<QueueStatusPanel queue={queueNoProcessadas} />)
      expect(screen.getByText('-')).toBeInTheDocument()
    })
  })

  describe('Tempo Medio', () => {
    it('displays tempo medio label', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('Tempo Medio')).toBeInTheDocument()
    })

    it('formats tempo medio in seconds', () => {
      render(<QueueStatusPanel queue={mockQueue} />)
      expect(screen.getByText('1.5s')).toBeInTheDocument()
    })

    it('formats tempo medio in milliseconds', () => {
      const fastQueue = { ...mockQueue, tempoMedioMs: 150 }
      render(<QueueStatusPanel queue={fastQueue} />)
      expect(screen.getByText('150ms')).toBeInTheDocument()
    })

    it('formats tempo medio in minutes', () => {
      const slowQueue = { ...mockQueue, tempoMedioMs: 120000 }
      render(<QueueStatusPanel queue={slowQueue} />)
      expect(screen.getByText('2.0m')).toBeInTheDocument()
    })

    it('displays dash when tempoMedioMs is null', () => {
      const queueNullTime = { ...mockQueue, tempoMedioMs: null }
      render(<QueueStatusPanel queue={queueNullTime} />)
      const dashes = screen.getAllByText('-')
      expect(dashes.length).toBeGreaterThanOrEqual(1)
    })

    it('displays dash when tempoMedioMs is undefined', () => {
      const { tempoMedioMs: _, ...queueNoTime } = mockQueue
      render(<QueueStatusPanel queue={queueNoTime} />)
      const dashes = screen.getAllByText('-')
      expect(dashes.length).toBeGreaterThanOrEqual(1)
    })
  })

  describe('Default Values', () => {
    it('handles undefined queue', () => {
      render(<QueueStatusPanel queue={undefined} />)
      expect(screen.getByText('Pendentes')).toBeInTheDocument()
      expect(screen.getByText('Processando')).toBeInTheDocument()
    })

    it('shows 0 for pendentes when queue is undefined', () => {
      render(<QueueStatusPanel queue={undefined} />)
      const zeros = screen.getAllByText('0')
      expect(zeros.length).toBeGreaterThanOrEqual(2)
    })
  })

  describe('Grid Layout', () => {
    it('renders 4 stat cards', () => {
      const { container } = render(<QueueStatusPanel queue={mockQueue} />)
      const statCards = container.querySelectorAll('.rounded-lg.p-4')
      expect(statCards).toHaveLength(4)
    })

    it('has neutral background for pendentes and tempo medio cards', () => {
      const { container } = render(<QueueStatusPanel queue={mockQueue} />)
      // Component uses bg-status-neutral for pendentes and tempo medio cards
      const neutralCards = container.querySelectorAll('.bg-status-neutral')
      expect(neutralCards.length).toBeGreaterThanOrEqual(2)
    })

    it('has info background for processando card', () => {
      const { container } = render(<QueueStatusPanel queue={mockQueue} />)
      const infoCard = container.querySelector('.bg-status-info')
      expect(infoCard).toBeInTheDocument()
    })

    it('has success background for processadas card', () => {
      const { container } = render(<QueueStatusPanel queue={mockQueue} />)
      const successCard = container.querySelector('.bg-status-success')
      expect(successCard).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles very large numbers', () => {
      const largeQueue = {
        pendentes: 10000,
        processando: 500,
        processadasPorHora: 50000,
        tempoMedioMs: 50,
      }
      render(<QueueStatusPanel queue={largeQueue} />)
      expect(screen.getByText('10000')).toBeInTheDocument()
      expect(screen.getByText('500')).toBeInTheDocument()
      expect(screen.getByText('50000')).toBeInTheDocument()
    })

    it('handles 0 values', () => {
      const zeroQueue = {
        pendentes: 0,
        processando: 0,
        processadasPorHora: 0,
        tempoMedioMs: 0,
      }
      render(<QueueStatusPanel queue={zeroQueue} />)
      const zeros = screen.getAllByText('0')
      expect(zeros.length).toBeGreaterThanOrEqual(3)
      expect(screen.getByText('0ms')).toBeInTheDocument()
    })
  })
})
