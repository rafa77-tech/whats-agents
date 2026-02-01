import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AnomalyDetailModal } from '@/components/integridade/anomaly-detail-modal'
import type { Anomaly } from '@/lib/integridade'

describe('AnomalyDetailModal', () => {
  const mockAnomaly: Anomaly = {
    id: 'abc12345-6789-0123-4567-890123456789',
    tipo: 'duplicata_medico',
    entidade: 'medico',
    entidadeId: 'medico-123',
    severidade: 'high',
    mensagem: 'Medico duplicado no sistema',
    criadaEm: '2026-01-15T10:30:00Z',
    resolvida: false,
  }

  const mockOnClose = vi.fn()
  const mockOnResolve = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockOnResolve.mockResolvedValue(undefined)
  })

  describe('Rendering', () => {
    it('renders modal title with truncated ID', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText(/Anomalia #abc12345/)).toBeInTheDocument()
    })

    it('renders modal description', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Detalhes e resolucao da anomalia')).toBeInTheDocument()
    })

    it('renders anomaly type', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Tipo')).toBeInTheDocument()
      expect(screen.getByText('duplicata_medico')).toBeInTheDocument()
    })

    it('renders entity info', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Entidade')).toBeInTheDocument()
      expect(screen.getByText('medico')).toBeInTheDocument()
    })

    it('renders entity ID', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('ID')).toBeInTheDocument()
      expect(screen.getByText('medico-123')).toBeInTheDocument()
    })

    it('renders message', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Detalhes')).toBeInTheDocument()
      expect(screen.getByText('Medico duplicado no sistema')).toBeInTheDocument()
    })

    it('renders default message when empty', () => {
      const noMessageAnomaly = { ...mockAnomaly, mensagem: '' }
      render(
        <AnomalyDetailModal
          anomaly={noMessageAnomaly}
          onClose={mockOnClose}
          onResolve={mockOnResolve}
        />
      )
      expect(screen.getByText('Sem detalhes adicionais')).toBeInTheDocument()
    })
  })

  describe('Severity Badge', () => {
    it('shows Alta badge for high severity', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Alta')).toBeInTheDocument()
    })

    it('shows Media badge for medium severity', () => {
      const mediumAnomaly = { ...mockAnomaly, severidade: 'medium' as const }
      render(
        <AnomalyDetailModal
          anomaly={mediumAnomaly}
          onClose={mockOnClose}
          onResolve={mockOnResolve}
        />
      )
      expect(screen.getByText('Media')).toBeInTheDocument()
    })

    it('shows Baixa badge for low severity', () => {
      const lowAnomaly = { ...mockAnomaly, severidade: 'low' as const }
      render(
        <AnomalyDetailModal anomaly={lowAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Baixa')).toBeInTheDocument()
    })
  })

  describe('Resolved State', () => {
    it('shows resolved message when anomaly is resolved', () => {
      const resolvedAnomaly = { ...mockAnomaly, resolvida: true }
      render(
        <AnomalyDetailModal
          anomaly={resolvedAnomaly}
          onClose={mockOnClose}
          onResolve={mockOnResolve}
        />
      )
      expect(screen.getByText('Esta anomalia ja foi resolvida')).toBeInTheDocument()
    })

    it('does not show resolution buttons when resolved', () => {
      const resolvedAnomaly = { ...mockAnomaly, resolvida: true }
      render(
        <AnomalyDetailModal
          anomaly={resolvedAnomaly}
          onClose={mockOnClose}
          onResolve={mockOnResolve}
        />
      )
      expect(screen.queryByText('Falso Positivo')).not.toBeInTheDocument()
      expect(screen.queryByText('Marcar Corrigido')).not.toBeInTheDocument()
    })

    it('does not show textarea when resolved', () => {
      const resolvedAnomaly = { ...mockAnomaly, resolvida: true }
      render(
        <AnomalyDetailModal
          anomaly={resolvedAnomaly}
          onClose={mockOnClose}
          onResolve={mockOnResolve}
        />
      )
      expect(screen.queryByPlaceholderText(/Descreva a causa/)).not.toBeInTheDocument()
    })
  })

  describe('Open State', () => {
    it('shows resolution textarea when not resolved', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByPlaceholderText(/Descreva a causa/)).toBeInTheDocument()
    })

    it('shows Falso Positivo button', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Falso Positivo')).toBeInTheDocument()
    })

    it('shows Marcar Corrigido button', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Marcar Corrigido')).toBeInTheDocument()
    })
  })

  describe('Actions', () => {
    it('calls onClose when Fechar button clicked', async () => {
      const user = userEvent.setup()
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )

      await user.click(screen.getByText('Fechar'))

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('calls onResolve with corrigido type', async () => {
      const user = userEvent.setup()
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )

      const textarea = screen.getByPlaceholderText(/Descreva a causa/)
      await user.type(textarea, 'Fixed the issue')
      await user.click(screen.getByText('Marcar Corrigido'))

      await waitFor(() => {
        expect(mockOnResolve).toHaveBeenCalledWith(
          mockAnomaly.id,
          '[Corrigido] Fixed the issue'
        )
      })
    })

    it('calls onResolve with falso_positivo type', async () => {
      const user = userEvent.setup()
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )

      const textarea = screen.getByPlaceholderText(/Descreva a causa/)
      await user.type(textarea, 'Not a real issue')
      await user.click(screen.getByText('Falso Positivo'))

      await waitFor(() => {
        expect(mockOnResolve).toHaveBeenCalledWith(
          mockAnomaly.id,
          '[Falso Positivo] Not a real issue'
        )
      })
    })
  })

  describe('Different Severities', () => {
    it('renders correctly for high severity', () => {
      render(
        <AnomalyDetailModal anomaly={mockAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Alta')).toBeInTheDocument()
    })

    it('renders correctly for medium severity', () => {
      const mediumAnomaly = { ...mockAnomaly, severidade: 'medium' as const }
      render(
        <AnomalyDetailModal
          anomaly={mediumAnomaly}
          onClose={mockOnClose}
          onResolve={mockOnResolve}
        />
      )
      expect(screen.getByText('Media')).toBeInTheDocument()
    })

    it('renders correctly for low severity', () => {
      const lowAnomaly = { ...mockAnomaly, severidade: 'low' as const }
      render(
        <AnomalyDetailModal anomaly={lowAnomaly} onClose={mockOnClose} onResolve={mockOnResolve} />
      )
      expect(screen.getByText('Baixa')).toBeInTheDocument()
    })
  })
})
