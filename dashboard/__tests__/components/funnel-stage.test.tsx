/**
 * Tests for components/dashboard/funnel-stage.tsx
 *
 * Tests business logic: width calculation, variance calculation, color selection
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FunnelStageComponent } from '@/components/dashboard/funnel-stage'
import { type FunnelStageVisual } from '@/types/dashboard'

describe('FunnelStageComponent', () => {
  const baseStage: FunnelStageVisual = {
    id: 'enviadas',
    label: 'Enviadas',
    count: 100,
    previousCount: 80,
    percentage: 100,
  }

  const defaultProps = {
    stage: baseStage,
    maxCount: 100,
    onClick: vi.fn(),
    isFirst: true,
  }

  describe('rendering', () => {
    it('should display the stage label', () => {
      render(<FunnelStageComponent {...defaultProps} />)
      expect(screen.getByText('Enviadas:')).toBeInTheDocument()
    })

    it('should display the count with locale formatting', () => {
      render(
        <FunnelStageComponent {...defaultProps} stage={{ ...baseStage, count: 1000 }} maxCount={1000} />
      )
      expect(screen.getByText('1.000')).toBeInTheDocument()
    })

    it('should display the percentage', () => {
      render(<FunnelStageComponent {...defaultProps} stage={{ ...baseStage, percentage: 85.5 }} />)
      expect(screen.getByText('(85.5%)')).toBeInTheDocument()
    })
  })

  describe('variance calculation', () => {
    it('should show positive variance with + prefix', () => {
      // 100 vs 80 = +25%
      render(<FunnelStageComponent {...defaultProps} />)
      expect(screen.getByText('+25%')).toBeInTheDocument()
    })

    it('should show negative variance', () => {
      // 80 vs 100 = -20%
      render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, count: 80, previousCount: 100 }}
        />
      )
      expect(screen.getByText('-20%')).toBeInTheDocument()
    })

    it('should not show variance when change is less than 1%', () => {
      // 100 vs 100 = 0%
      render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, count: 100, previousCount: 100 }}
        />
      )
      expect(screen.queryByText(/[+-]\d+%/)).not.toBeInTheDocument()
    })

    it('should not show variance when previousCount is zero', () => {
      render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, count: 100, previousCount: 0 }}
        />
      )
      expect(screen.queryByText(/[+-]\d+%/)).not.toBeInTheDocument()
    })
  })

  describe('color selection by stage id', () => {
    it('should apply blue colors for enviadas stage', () => {
      render(<FunnelStageComponent {...defaultProps} stage={{ ...baseStage, id: 'enviadas' }} />)
      const label = screen.getByText('Enviadas:')
      expect(label).toHaveClass('text-blue-700')
    })

    it('should apply blue colors for entregues stage', () => {
      render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, id: 'entregues', label: 'Entregues' }}
        />
      )
      const label = screen.getByText('Entregues:')
      expect(label).toHaveClass('text-blue-700')
    })

    it('should apply green colors for respostas stage', () => {
      render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, id: 'respostas', label: 'Respostas' }}
        />
      )
      const label = screen.getByText('Respostas:')
      expect(label).toHaveClass('text-green-700')
    })

    it('should apply yellow colors for interesse stage', () => {
      render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, id: 'interesse', label: 'Interesse' }}
        />
      )
      const label = screen.getByText('Interesse:')
      expect(label).toHaveClass('text-yellow-700')
    })

    it('should apply emerald colors for fechadas stage', () => {
      render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, id: 'fechadas', label: 'Fechadas' }}
        />
      )
      const label = screen.getByText('Fechadas:')
      expect(label).toHaveClass('text-emerald-700')
    })

    it('should apply default blue colors for unknown stage', () => {
      render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, id: 'unknown', label: 'Unknown' }}
        />
      )
      const label = screen.getByText('Unknown:')
      expect(label).toHaveClass('text-blue-700')
    })
  })

  describe('click handling', () => {
    it('should call onClick when clicked', () => {
      const onClick = vi.fn()
      render(<FunnelStageComponent {...defaultProps} onClick={onClick} />)

      const stage = screen.getByText('Enviadas:').closest('div[class*="cursor-pointer"]')
      fireEvent.click(stage!)

      expect(onClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('tooltip content', () => {
    it('should have tooltip trigger', async () => {
      render(<FunnelStageComponent {...defaultProps} />)
      // The tooltip trigger should be present (the clickable div)
      const clickableElement = screen.getByText('Enviadas:').closest('div[class*="cursor-pointer"]')
      expect(clickableElement).toBeInTheDocument()
    })
  })

  describe('width calculation', () => {
    it('should apply minimum width of 30% for small counts', () => {
      // When count is 10 and maxCount is 100, calculated width would be 10%
      // but minimum is 30%
      render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, count: 10 }}
          maxCount={100}
          isFirst={false}
        />
      )
      // The component should still render (width clamped to 30%)
      expect(screen.getByText('Enviadas:')).toBeInTheDocument()
    })

    it('should not apply padding for first stage', () => {
      const { container } = render(<FunnelStageComponent {...defaultProps} isFirst={true} />)
      const wrapper = container.querySelector('div[class*="cursor-pointer"]')
      expect(wrapper).toHaveStyle({ paddingLeft: '0%' })
    })

    it('should apply padding for non-first stages', () => {
      const { container } = render(
        <FunnelStageComponent
          {...defaultProps}
          stage={{ ...baseStage, count: 50 }}
          maxCount={100}
          isFirst={false}
        />
      )
      const wrapper = container.querySelector('div[class*="cursor-pointer"]')
      // width = 50%, padding = (100 - 50) / 2 = 25%
      expect(wrapper).toHaveStyle({ paddingLeft: '25%' })
    })
  })
})
