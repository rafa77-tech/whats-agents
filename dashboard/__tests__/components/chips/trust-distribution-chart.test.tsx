/**
 * Tests for components/chips/trust-distribution-chart.tsx
 *
 * Tests the TrustDistributionChart component rendering and calculations.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TrustDistributionChart } from '@/components/chips/trust-distribution-chart'
import { TrustLevelExtended } from '@/types/chips'

describe('TrustDistributionChart', () => {
  const defaultDistribution: Record<TrustLevelExtended, number> = {
    verde: 50,
    amarelo: 20,
    laranja: 15,
    vermelho: 10,
    critico: 5,
  }

  const defaultProps = {
    distribution: defaultDistribution,
    total: 100,
  }

  describe('rendering', () => {
    it('should render title', () => {
      render(<TrustDistributionChart {...defaultProps} />)
      expect(screen.getByText('Distribuicao de Trust Score')).toBeInTheDocument()
    })

    it('should render healthy percentage', () => {
      render(<TrustDistributionChart {...defaultProps} />)
      // verde (50) + amarelo (20) = 70%
      expect(screen.getByText('70.0% saudaveis')).toBeInTheDocument()
    })

    it('should render counts for each level', () => {
      render(<TrustDistributionChart {...defaultProps} />)
      expect(screen.getByText('50')).toBeInTheDocument() // verde
      expect(screen.getByText('20')).toBeInTheDocument() // amarelo
      expect(screen.getByText('15')).toBeInTheDocument() // laranja
      expect(screen.getByText('10')).toBeInTheDocument() // vermelho
      expect(screen.getByText('5')).toBeInTheDocument() // critico
    })

    it('should render level labels', () => {
      render(<TrustDistributionChart {...defaultProps} />)
      expect(screen.getByText('Verde')).toBeInTheDocument()
      expect(screen.getByText('Amarelo')).toBeInTheDocument()
      expect(screen.getByText('Laranja')).toBeInTheDocument()
      expect(screen.getByText('Vermelho')).toBeInTheDocument()
      expect(screen.getByText('Critico')).toBeInTheDocument()
    })
  })

  describe('healthy percentage calculation', () => {
    it('should calculate 100% healthy when all chips are verde', () => {
      const distribution: Record<TrustLevelExtended, number> = {
        verde: 100,
        amarelo: 0,
        laranja: 0,
        vermelho: 0,
        critico: 0,
      }
      render(<TrustDistributionChart distribution={distribution} total={100} />)
      expect(screen.getByText('100.0% saudaveis')).toBeInTheDocument()
    })

    it('should calculate 0% healthy when no verde or amarelo', () => {
      const distribution: Record<TrustLevelExtended, number> = {
        verde: 0,
        amarelo: 0,
        laranja: 30,
        vermelho: 40,
        critico: 30,
      }
      render(<TrustDistributionChart distribution={distribution} total={100} />)
      expect(screen.getByText('0.0% saudaveis')).toBeInTheDocument()
    })

    it('should handle partial healthy distribution', () => {
      const distribution: Record<TrustLevelExtended, number> = {
        verde: 30,
        amarelo: 20,
        laranja: 25,
        vermelho: 15,
        critico: 10,
      }
      render(<TrustDistributionChart distribution={distribution} total={100} />)
      // 30 + 20 = 50%
      expect(screen.getByText('50.0% saudaveis')).toBeInTheDocument()
    })
  })

  describe('healthy percentage styling', () => {
    it('should apply green color when >= 70%', () => {
      const distribution: Record<TrustLevelExtended, number> = {
        verde: 60,
        amarelo: 20,
        laranja: 10,
        vermelho: 5,
        critico: 5,
      }
      render(<TrustDistributionChart distribution={distribution} total={100} />)
      const healthyElement = screen.getByText('80.0% saudaveis')
      expect(healthyElement).toHaveClass('text-green-600')
    })

    it('should apply yellow color when >= 50% and < 70%', () => {
      const distribution: Record<TrustLevelExtended, number> = {
        verde: 40,
        amarelo: 20,
        laranja: 20,
        vermelho: 10,
        critico: 10,
      }
      render(<TrustDistributionChart distribution={distribution} total={100} />)
      const healthyElement = screen.getByText('60.0% saudaveis')
      expect(healthyElement).toHaveClass('text-yellow-600')
    })

    it('should apply red color when < 50%', () => {
      const distribution: Record<TrustLevelExtended, number> = {
        verde: 20,
        amarelo: 20,
        laranja: 30,
        vermelho: 20,
        critico: 10,
      }
      render(<TrustDistributionChart distribution={distribution} total={100} />)
      const healthyElement = screen.getByText('40.0% saudaveis')
      expect(healthyElement).toHaveClass('text-red-600')
    })
  })

  describe('edge cases', () => {
    it('should handle zero total', () => {
      const emptyDistribution: Record<TrustLevelExtended, number> = {
        verde: 0,
        amarelo: 0,
        laranja: 0,
        vermelho: 0,
        critico: 0,
      }
      render(<TrustDistributionChart distribution={emptyDistribution} total={0} />)
      expect(screen.getByText('0.0% saudaveis')).toBeInTheDocument()
    })

    it('should handle missing distribution values', () => {
      const partialDistribution = {
        verde: 50,
        amarelo: 0,
        laranja: 0,
        vermelho: 0,
        critico: 0,
      } as Record<TrustLevelExtended, number>
      render(<TrustDistributionChart distribution={partialDistribution} total={50} />)
      expect(screen.getByText('100.0% saudaveis')).toBeInTheDocument()
    })
  })
})
