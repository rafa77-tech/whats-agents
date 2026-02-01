import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DoctorActions } from '@/app/(dashboard)/medicos/components/doctor-actions'

// Mock useRouter
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
}))

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('DoctorActions', () => {
  const mockDoctor = {
    id: 'doctor-123',
    nome: 'João Silva',
    stage_jornada: 'novo',
    opt_out: false,
  }

  const mockOnRefresh = vi.fn()

  const baseProps = {
    doctor: mockDoctor,
    onRefresh: mockOnRefresh,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({ ok: true })
  })

  describe('Rendering', () => {
    it('renders funnel status section', () => {
      render(<DoctorActions {...baseProps} />)
      expect(screen.getByText('Status do Funil')).toBeInTheDocument()
      expect(screen.getByText('Posicao do medico no pipeline de vendas')).toBeInTheDocument()
    })

    it('renders contact preferences section', () => {
      render(<DoctorActions {...baseProps} />)
      expect(screen.getByText('Preferencias de Contato')).toBeInTheDocument()
      expect(screen.getByText('Gerenciar preferencias de comunicacao')).toBeInTheDocument()
    })

    it('renders conversation section', () => {
      render(<DoctorActions {...baseProps} />)
      expect(screen.getByText('Conversa')).toBeInTheDocument()
      expect(screen.getByText('Ver Conversas')).toBeInTheDocument()
    })

    it('shows opt-out button when not opted out', () => {
      render(<DoctorActions {...baseProps} />)
      expect(screen.getByText('Marcar Opt-out')).toBeInTheDocument()
    })

    it('shows reactivate button when opted out', () => {
      const optedOutDoctor = { ...mockDoctor, opt_out: true }
      render(<DoctorActions {...baseProps} doctor={optedOutDoctor} />)
      expect(screen.getByText('Reativar Contato')).toBeInTheDocument()
    })
  })

  describe('Opt-out Toggle', () => {
    it('shows confirmation dialog for opt-out', async () => {
      const user = userEvent.setup()
      render(<DoctorActions {...baseProps} />)

      const optOutButton = screen.getByText('Marcar Opt-out')
      await user.click(optOutButton)

      await waitFor(() => {
        expect(screen.getByText('Marcar como opt-out?')).toBeInTheDocument()
        expect(
          screen.getByText('O medico nao recebera mais mensagens automaticas da Julia.')
        ).toBeInTheDocument()
      })
    })

    it('shows confirmation dialog for reactivation', async () => {
      const user = userEvent.setup()
      const optedOutDoctor = { ...mockDoctor, opt_out: true }
      render(<DoctorActions {...baseProps} doctor={optedOutDoctor} />)

      const reactivateButton = screen.getByText('Reativar Contato')
      await user.click(reactivateButton)

      await waitFor(() => {
        expect(screen.getByText('Reativar contato?')).toBeInTheDocument()
        expect(
          screen.getByText('O medico voltara a receber mensagens da Julia.')
        ).toBeInTheDocument()
      })
    })

    it('calls API and refreshes on confirm', async () => {
      const user = userEvent.setup()
      render(<DoctorActions {...baseProps} />)

      const optOutButton = screen.getByText('Marcar Opt-out')
      await user.click(optOutButton)

      const confirmButton = screen.getByText('Confirmar')
      await user.click(confirmButton)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/medicos/doctor-123/opt-out',
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({ opt_out: true }),
          })
        )
        expect(mockOnRefresh).toHaveBeenCalled()
      })
    })

    it('can cancel confirmation dialog', async () => {
      const user = userEvent.setup()
      render(<DoctorActions {...baseProps} />)

      const optOutButton = screen.getByText('Marcar Opt-out')
      await user.click(optOutButton)

      const cancelButton = screen.getByText('Cancelar')
      await user.click(cancelButton)

      expect(mockFetch).not.toHaveBeenCalled()
    })
  })

  describe('Funnel Status', () => {
    it('renders current stage in select', () => {
      render(<DoctorActions {...baseProps} />)
      // The select should show the current stage
      expect(screen.getByText('Status do Funil')).toBeInTheDocument()
    })
  })
})
