/**
 * Tests for components/chips/alert-card.tsx
 *
 * Tests the AlertCard component rendering and interactions.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { AlertCard } from '@/components/chips/alert-card'
import { ChipAlert, ChipAlertSeverity, ChipAlertType } from '@/types/chips'

// Mock the chips API
vi.mock('@/lib/api/chips', () => ({
  chipsApi: {
    resolveAlert: vi.fn(),
  },
}))

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

import { chipsApi } from '@/lib/api/chips'

describe('AlertCard', () => {
  const mockAlert: ChipAlert = {
    id: 'alert-1',
    chipId: 'chip-1',
    chipTelefone: '+5511999999999',
    type: 'TRUST_CAINDO' as ChipAlertType,
    severity: 'alerta' as ChipAlertSeverity,
    title: 'Trust Score em Queda',
    message: 'O trust score caiu 15 pontos nas últimas 24h.',
    recommendation: 'Considere pausar o chip temporariamente.',
    createdAt: new Date().toISOString(),
  }

  const defaultProps = {
    alert: mockAlert,
    onResolved: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('should render alert title', () => {
      render(<AlertCard {...defaultProps} />)
      expect(screen.getByText('Trust Score em Queda')).toBeInTheDocument()
    })

    it('should render alert message', () => {
      render(<AlertCard {...defaultProps} />)
      expect(screen.getByText('O trust score caiu 15 pontos nas últimas 24h.')).toBeInTheDocument()
    })

    it('should render recommendation when present', () => {
      render(<AlertCard {...defaultProps} />)
      expect(screen.getByText(/Considere pausar o chip temporariamente/)).toBeInTheDocument()
    })

    it('should render chip telefone as link', () => {
      render(<AlertCard {...defaultProps} />)
      expect(screen.getByText('+5511999999999')).toBeInTheDocument()
    })

    it('should render resolve button for unresolved alerts', () => {
      render(<AlertCard {...defaultProps} />)
      expect(screen.getByText('Resolver')).toBeInTheDocument()
    })

    it('should not render resolve button for resolved alerts', () => {
      const resolvedAlert = {
        ...mockAlert,
        resolvedAt: new Date().toISOString(),
        resolvedBy: 'admin',
      }
      render(<AlertCard {...defaultProps} alert={resolvedAlert} />)
      expect(screen.queryByText('Resolver')).not.toBeInTheDocument()
    })
  })

  describe('severity badges', () => {
    const severities: ChipAlertSeverity[] = ['critico', 'alerta', 'atencao', 'info']
    const severityLabels: Record<ChipAlertSeverity, string> = {
      critico: 'Crítico',
      alerta: 'Alerta',
      atencao: 'Atenção',
      info: 'Info',
    }

    severities.forEach((severity) => {
      it(`should render correct badge for ${severity} severity`, () => {
        const alert = { ...mockAlert, severity }
        render(<AlertCard {...defaultProps} alert={alert} />)
        expect(screen.getByText(severityLabels[severity])).toBeInTheDocument()
      })
    })
  })

  describe('alert types', () => {
    const types: ChipAlertType[] = [
      'TRUST_CAINDO',
      'TAXA_BLOCK_ALTA',
      'ERROS_FREQUENTES',
      'DELIVERY_BAIXO',
      'RESPOSTA_BAIXA',
      'DESCONEXAO',
      'LIMITE_PROXIMO',
      'FASE_ESTAGNADA',
      'QUALIDADE_META',
      'COMPORTAMENTO_ANOMALO',
    ]
    const typeLabels: Record<ChipAlertType, string> = {
      TRUST_CAINDO: 'Trust Caindo',
      TAXA_BLOCK_ALTA: 'Taxa de Block Alta',
      ERROS_FREQUENTES: 'Erros Frequentes',
      DELIVERY_BAIXO: 'Delivery Baixo',
      RESPOSTA_BAIXA: 'Resposta Baixa',
      DESCONEXAO: 'Desconexão',
      LIMITE_PROXIMO: 'Limite Próximo',
      FASE_ESTAGNADA: 'Fase Estagnada',
      QUALIDADE_META: 'Qualidade Meta',
      COMPORTAMENTO_ANOMALO: 'Comportamento Anômalo',
    }

    types.forEach((type) => {
      it(`should render correct label for ${type} type`, () => {
        const alert = { ...mockAlert, type }
        render(<AlertCard {...defaultProps} alert={alert} />)
        expect(screen.getByText(typeLabels[type])).toBeInTheDocument()
      })
    })
  })

  describe('resolved alerts', () => {
    it('should show resolved timestamp', () => {
      const resolvedAlert = {
        ...mockAlert,
        resolvedAt: '2024-01-15T10:30:00Z',
        resolvedBy: 'admin',
      }
      render(<AlertCard {...defaultProps} alert={resolvedAlert} />)
      expect(screen.getByText(/Resolvido em/)).toBeInTheDocument()
      expect(screen.getByText(/por admin/)).toBeInTheDocument()
    })

    it('should show resolution notes when present', () => {
      const resolvedAlert = {
        ...mockAlert,
        resolvedAt: '2024-01-15T10:30:00Z',
        resolvedBy: 'admin',
        resolutionNotes: 'Chip foi pausado manualmente.',
      }
      render(<AlertCard {...defaultProps} alert={resolvedAlert} />)
      expect(screen.getByText(/Chip foi pausado manualmente/)).toBeInTheDocument()
    })

    it('should not show recommendation for resolved alerts', () => {
      const resolvedAlert = {
        ...mockAlert,
        resolvedAt: new Date().toISOString(),
        resolvedBy: 'admin',
      }
      render(<AlertCard {...defaultProps} alert={resolvedAlert} />)
      expect(screen.queryByText(/Recomendação/)).not.toBeInTheDocument()
    })
  })

  describe('resolve dialog', () => {
    it('should open resolve dialog when button is clicked', () => {
      render(<AlertCard {...defaultProps} />)
      fireEvent.click(screen.getByText('Resolver'))
      expect(screen.getByText('Resolver Alerta')).toBeInTheDocument()
    })

    it('should close dialog when cancel is clicked', () => {
      render(<AlertCard {...defaultProps} />)
      fireEvent.click(screen.getByText('Resolver'))
      fireEvent.click(screen.getByText('Cancelar'))
      expect(screen.queryByText('Resolver Alerta')).not.toBeInTheDocument()
    })

    it('should call API and onResolved when resolved', async () => {
      const onResolved = vi.fn()
      vi.mocked(chipsApi.resolveAlert).mockResolvedValue({ success: true })

      render(<AlertCard {...defaultProps} onResolved={onResolved} />)

      fireEvent.click(screen.getByText('Resolver'))

      const textarea = screen.getByPlaceholderText('Descreva como o alerta foi resolvido...')
      fireEvent.change(textarea, { target: { value: 'Chip foi reiniciado' } })

      fireEvent.click(screen.getByText('Marcar como Resolvido'))

      await waitFor(() => {
        expect(chipsApi.resolveAlert).toHaveBeenCalledWith('alert-1', 'Chip foi reiniciado')
        expect(onResolved).toHaveBeenCalled()
      })
    })
  })

  describe('timestamp formatting', () => {
    it('should format recent timestamps as minutes ago', () => {
      const recentAlert = {
        ...mockAlert,
        createdAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
      }
      render(<AlertCard {...defaultProps} alert={recentAlert} />)
      expect(screen.getByText('30m atrás')).toBeInTheDocument()
    })

    it('should format timestamps as hours ago', () => {
      const hoursAgoAlert = {
        ...mockAlert,
        createdAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(), // 5 hours ago
      }
      render(<AlertCard {...defaultProps} alert={hoursAgoAlert} />)
      expect(screen.getByText('5h atrás')).toBeInTheDocument()
    })

    it('should format timestamps as days ago', () => {
      const daysAgoAlert = {
        ...mockAlert,
        createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days ago
      }
      render(<AlertCard {...defaultProps} alert={daysAgoAlert} />)
      expect(screen.getByText('3d atrás')).toBeInTheDocument()
    })
  })
})
