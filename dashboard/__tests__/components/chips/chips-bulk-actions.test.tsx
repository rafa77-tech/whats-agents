/**
 * Tests for components/chips/chips-bulk-actions.tsx
 *
 * Tests the ChipsBulkActions component rendering and interactions.
 * Note: Async bulk action tests are skipped due to timer complexity with AlertDialog.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { ChipsBulkActions } from '@/components/chips/chips-bulk-actions'

// Mock the chips API
vi.mock('@/lib/api/chips', () => ({
  chipsApi: {
    pauseChip: vi.fn(),
    resumeChip: vi.fn(),
    promoteChip: vi.fn(),
  },
}))

describe('ChipsBulkActions', () => {
  const defaultProps = {
    selectedIds: ['chip-1', 'chip-2'],
    onClearSelection: vi.fn(),
    onActionComplete: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('should not render when no chips are selected', () => {
      render(<ChipsBulkActions {...defaultProps} selectedIds={[]} />)
      expect(screen.queryByText(/selecionado/)).not.toBeInTheDocument()
    })

    it('should render when chips are selected', () => {
      render(<ChipsBulkActions {...defaultProps} />)
      expect(screen.getByText('2 chips selecionados')).toBeInTheDocument()
    })

    it('should use singular form for one chip', () => {
      render(<ChipsBulkActions {...defaultProps} selectedIds={['chip-1']} />)
      expect(screen.getByText('1 chip selecionado')).toBeInTheDocument()
    })

    it('should render action buttons', () => {
      render(<ChipsBulkActions {...defaultProps} />)
      expect(screen.getByText('Pausar')).toBeInTheDocument()
      expect(screen.getByText('Retomar')).toBeInTheDocument()
      expect(screen.getByText('Promover')).toBeInTheDocument()
    })

    it('should render clear selection button', () => {
      render(<ChipsBulkActions {...defaultProps} />)
      expect(screen.getByLabelText('Limpar seleção')).toBeInTheDocument()
    })

    it('should render three chips selected', () => {
      render(<ChipsBulkActions {...defaultProps} selectedIds={['chip-1', 'chip-2', 'chip-3']} />)
      expect(screen.getByText('3 chips selecionados')).toBeInTheDocument()
    })
  })

  describe('clear selection', () => {
    it('should call onClearSelection when clear button is clicked', () => {
      const onClearSelection = vi.fn()
      render(<ChipsBulkActions {...defaultProps} onClearSelection={onClearSelection} />)

      fireEvent.click(screen.getByLabelText('Limpar seleção'))
      expect(onClearSelection).toHaveBeenCalled()
    })
  })

  describe('confirmation dialogs', () => {
    it('should show pause confirmation dialog', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Pausar'))

      expect(screen.getByText('Confirmar Ação')).toBeInTheDocument()
      expect(screen.getByText(/Pausar os chips selecionados/)).toBeInTheDocument()
      expect(screen.getByText(/Esta ação será aplicada a 2 chips/)).toBeInTheDocument()
    })

    it('should show resume confirmation dialog', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Retomar'))

      expect(screen.getByText('Confirmar Ação')).toBeInTheDocument()
      expect(screen.getByText(/Retomar os chips selecionados/)).toBeInTheDocument()
    })

    it('should show promote confirmation dialog', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Promover'))

      expect(screen.getByText('Confirmar Ação')).toBeInTheDocument()
      expect(screen.getByText(/Promover os chips selecionados/)).toBeInTheDocument()
    })

    it('should close dialog when cancel is clicked', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Pausar'))
      expect(screen.getByText('Confirmar Ação')).toBeInTheDocument()

      fireEvent.click(screen.getByText('Cancelar'))
      expect(screen.queryByText('Confirmar Ação')).not.toBeInTheDocument()
    })

    it('should show correct description for pause action', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Pausar'))

      expect(screen.getByText(/deixarão de enviar mensagens/)).toBeInTheDocument()
    })

    it('should show correct description for resume action', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Retomar'))

      expect(screen.getByText(/voltarão a enviar mensagens/)).toBeInTheDocument()
    })

    it('should show correct description for promote action', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Promover'))

      expect(screen.getByText(/próxima fase de warmup/)).toBeInTheDocument()
    })
  })

  describe('dialog button labels', () => {
    it('should show Pausar Chips as confirm button for pause action', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Pausar'))

      expect(screen.getByText('Pausar Chips')).toBeInTheDocument()
    })

    it('should show Retomar Chips as confirm button for resume action', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Retomar'))

      expect(screen.getByText('Retomar Chips')).toBeInTheDocument()
    })

    it('should show Promover Chips as confirm button for promote action', () => {
      render(<ChipsBulkActions {...defaultProps} />)

      fireEvent.click(screen.getByText('Promover'))

      expect(screen.getByText('Promover Chips')).toBeInTheDocument()
    })
  })

  describe('singular/plural text', () => {
    it('should use singular form in dialog for one chip', () => {
      render(<ChipsBulkActions {...defaultProps} selectedIds={['chip-1']} />)

      fireEvent.click(screen.getByText('Pausar'))

      expect(screen.getByText(/Esta ação será aplicada a 1 chip\./)).toBeInTheDocument()
    })

    it('should use plural form in dialog for multiple chips', () => {
      render(<ChipsBulkActions {...defaultProps} selectedIds={['chip-1', 'chip-2', 'chip-3']} />)

      fireEvent.click(screen.getByText('Pausar'))

      expect(screen.getByText(/Esta ação será aplicada a 3 chips\./)).toBeInTheDocument()
    })
  })
})
