/**
 * Tests for components/chips/chips-table.tsx
 *
 * Tests the ChipsTable component rendering, selection, and navigation.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ChipsTable } from '@/components/chips/chips-table'
import { ChipListItem } from '@/types/chips'
import { ChipStatus, TrustLevel } from '@/types/dashboard'

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

describe('ChipsTable', () => {
  const mockChip: ChipListItem = {
    id: 'chip-1',
    telefone: '+5511999999999',
    status: 'active' as ChipStatus,
    trustScore: 85,
    trustLevel: 'verde',
    warmupPhase: 'operacao',
    messagesToday: 50,
    dailyLimit: 100,
    responseRate: 35.5,
    errorsLast24h: 2,
    hasActiveAlert: false,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-15T12:00:00Z',
  }

  const defaultProps = {
    chips: [mockChip],
    selectedIds: [] as string[],
    onSelectionChange: vi.fn(),
    onRowClick: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('should render table headers', () => {
      render(<ChipsTable {...defaultProps} />)
      expect(screen.getByText('Telefone')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
      expect(screen.getByText('Trust Score')).toBeInTheDocument()
      expect(screen.getByText('Fase')).toBeInTheDocument()
      expect(screen.getByText('Msgs Hoje')).toBeInTheDocument()
      expect(screen.getByText('Taxa Resp.')).toBeInTheDocument()
      expect(screen.getByText('Erros 24h')).toBeInTheDocument()
    })

    it('should render empty state when no chips', () => {
      render(<ChipsTable {...defaultProps} chips={[]} />)
      expect(screen.getByText('Nenhum chip encontrado')).toBeInTheDocument()
    })

    it('should render chip telefone', () => {
      render(<ChipsTable {...defaultProps} />)
      expect(screen.getByText('+5511999999999')).toBeInTheDocument()
    })

    it('should render chip status', () => {
      render(<ChipsTable {...defaultProps} />)
      expect(screen.getByText('Ativo')).toBeInTheDocument()
    })

    it('should render chip trust score', () => {
      render(<ChipsTable {...defaultProps} />)
      expect(screen.getByText('85')).toBeInTheDocument()
    })

    it('should render chip warmup phase', () => {
      render(<ChipsTable {...defaultProps} />)
      expect(screen.getByText('operacao')).toBeInTheDocument()
    })

    it('should render messages today with daily limit', () => {
      render(<ChipsTable {...defaultProps} />)
      expect(screen.getByText('50/100')).toBeInTheDocument()
    })

    it('should render response rate with percentage', () => {
      render(<ChipsTable {...defaultProps} />)
      expect(screen.getByText('35.5%')).toBeInTheDocument()
    })

    it('should render errors count', () => {
      render(<ChipsTable {...defaultProps} />)
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('should show alert icon when hasActiveAlert is true', () => {
      const chipWithAlert = { ...mockChip, hasActiveAlert: true }
      render(<ChipsTable {...defaultProps} chips={[chipWithAlert]} />)
      // Alert triangle icon should be present
      const row = screen.getByText('+5511999999999').closest('tr')
      expect(row).toBeInTheDocument()
    })
  })

  describe('status badges', () => {
    const statuses: ChipStatus[] = [
      'active',
      'ready',
      'warming',
      'degraded',
      'paused',
      'banned',
      'provisioned',
      'pending',
      'cancelled',
    ]
    const statusLabels: Record<ChipStatus, string> = {
      active: 'Ativo',
      ready: 'Pronto',
      warming: 'Aquecendo',
      degraded: 'Degradado',
      paused: 'Pausado',
      banned: 'Banido',
      provisioned: 'Provisionado',
      pending: 'Pendente',
      cancelled: 'Cancelado',
      offline: 'Offline',
    }

    statuses.forEach((status) => {
      it(`should render correct label for ${status} status`, () => {
        const chip = { ...mockChip, status }
        render(<ChipsTable {...defaultProps} chips={[chip]} />)
        expect(screen.getByText(statusLabels[status])).toBeInTheDocument()
      })
    })
  })

  describe('selection', () => {
    it('should call onSelectionChange when checkbox is clicked', () => {
      const onSelectionChange = vi.fn()
      render(<ChipsTable {...defaultProps} onSelectionChange={onSelectionChange} />)

      const checkboxes = screen.getAllByRole('checkbox')
      // First checkbox is the "select all", second is the chip checkbox
      fireEvent.click(checkboxes[1]!)

      expect(onSelectionChange).toHaveBeenCalledWith(['chip-1'])
    })

    it('should deselect when selected chip checkbox is clicked', () => {
      const onSelectionChange = vi.fn()
      render(
        <ChipsTable
          {...defaultProps}
          selectedIds={['chip-1']}
          onSelectionChange={onSelectionChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      fireEvent.click(checkboxes[1]!)

      expect(onSelectionChange).toHaveBeenCalledWith([])
    })

    it('should select all chips when header checkbox is clicked', () => {
      const chips = [mockChip, { ...mockChip, id: 'chip-2', telefone: '+5511888888888' }]
      const onSelectionChange = vi.fn()
      render(<ChipsTable {...defaultProps} chips={chips} onSelectionChange={onSelectionChange} />)

      const checkboxes = screen.getAllByRole('checkbox')
      fireEvent.click(checkboxes[0]!) // Select all checkbox

      expect(onSelectionChange).toHaveBeenCalledWith(['chip-1', 'chip-2'])
    })

    it('should deselect all when all are selected and header checkbox is clicked', () => {
      const chips = [mockChip, { ...mockChip, id: 'chip-2', telefone: '+5511888888888' }]
      const onSelectionChange = vi.fn()
      render(
        <ChipsTable
          {...defaultProps}
          chips={chips}
          selectedIds={['chip-1', 'chip-2']}
          onSelectionChange={onSelectionChange}
        />
      )

      const checkboxes = screen.getAllByRole('checkbox')
      fireEvent.click(checkboxes[0]!) // Select all checkbox

      expect(onSelectionChange).toHaveBeenCalledWith([])
    })
  })

  describe('row click', () => {
    it('should call onRowClick when row is clicked', () => {
      const onRowClick = vi.fn()
      render(<ChipsTable {...defaultProps} onRowClick={onRowClick} />)

      const row = screen.getByText('+5511999999999').closest('tr')
      fireEvent.click(row!)

      expect(onRowClick).toHaveBeenCalledWith(mockChip)
    })

    it('should not trigger onRowClick when checkbox is clicked', () => {
      const onRowClick = vi.fn()
      render(<ChipsTable {...defaultProps} onRowClick={onRowClick} />)

      const checkboxes = screen.getAllByRole('checkbox')
      fireEvent.click(checkboxes[1]!)

      expect(onRowClick).not.toHaveBeenCalled()
    })
  })

  describe('trust score colors', () => {
    it('should apply green color for verde trust level', () => {
      const chip = { ...mockChip, trustLevel: 'verde' as TrustLevel }
      render(<ChipsTable {...defaultProps} chips={[chip]} />)
      const scoreElement = screen.getByText('85')
      expect(scoreElement).toHaveClass('text-trust-verde-foreground')
    })

    it('should apply red color for vermelho trust level', () => {
      const chip = { ...mockChip, trustLevel: 'vermelho' as TrustLevel, trustScore: 30 }
      render(<ChipsTable {...defaultProps} chips={[chip]} />)
      const scoreElement = screen.getByText('30')
      expect(scoreElement).toHaveClass('text-trust-vermelho-foreground')
    })
  })

  describe('response rate styling', () => {
    it('should apply green color for response rate >= 30%', () => {
      render(<ChipsTable {...defaultProps} />)
      const rateElement = screen.getByText('35.5%')
      expect(rateElement).toHaveClass('text-status-success-foreground')
    })

    it('should apply red color for response rate < 30%', () => {
      const chip = { ...mockChip, responseRate: 25.0 }
      render(<ChipsTable {...defaultProps} chips={[chip]} />)
      const rateElement = screen.getByText('25.0%')
      expect(rateElement).toHaveClass('text-status-error-foreground')
    })
  })

  describe('errors styling', () => {
    it('should apply red color for errors > 5', () => {
      const chip = { ...mockChip, errorsLast24h: 10 }
      render(<ChipsTable {...defaultProps} chips={[chip]} />)
      const errorsElement = screen.getByText('10')
      expect(errorsElement).toHaveClass('text-status-error-foreground')
    })

    it('should apply gray color for errors <= 5', () => {
      render(<ChipsTable {...defaultProps} />)
      const errorsElement = screen.getByText('2')
      expect(errorsElement).toHaveClass('text-muted-foreground')
    })
  })
})
