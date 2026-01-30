/**
 * Testes para ChipActionsPanel - Sprint 36 + Sprint 41
 *
 * Testa ações disponíveis para chips (pause, resume, promote, reactivate, QR code).
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChipActionsPanel } from '@/components/chips/chip-actions-panel'
import { chipsApi } from '@/lib/api/chips'
import { ChipFullDetail } from '@/types/chips'
import { vi, describe, it, expect, beforeEach } from 'vitest'

// Mock da API
vi.mock('@/lib/api/chips', () => ({
  chipsApi: {
    pauseChip: vi.fn(),
    resumeChip: vi.fn(),
    promoteChip: vi.fn(),
    reactivateChip: vi.fn(),
    checkChipConnection: vi.fn(),
    getInstanceQRCode: vi.fn(),
  },
}))

const mockOnActionComplete = vi.fn()

// Factory para criar chip mock
function createMockChip(overrides: Partial<ChipFullDetail> = {}): ChipFullDetail {
  return {
    id: 'chip-123',
    telefone: '5511999999999',
    instanceName: 'julia_01',
    status: 'active',
    trustScore: 85,
    trustLevel: 'verde',
    warmupPhase: 'operacao',
    warmingDay: 30,
    messagesToday: 50,
    dailyLimit: 100,
    responseRate: 0.65,
    errorsLast24h: 2,
    hasActiveAlert: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ddd: '11',
    region: 'SP',
    deliveryRate: 0.95,
    blockRate: 0.01,
    lastActivityAt: new Date().toISOString(),
    totalMessagesSent: 500,
    totalConversations: 100,
    totalBidirectional: 80,
    groupsJoined: 5,
    mediaTypesSent: ['image', 'audio'],
    ...overrides,
  }
}

describe('ChipActionsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Renderização condicional de ações', () => {
    it('mostra botão "Pausar" para chip ativo', () => {
      const chip = createMockChip({ status: 'active' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText('Pausar Chip')).toBeInTheDocument()
    })

    it('mostra botão "Retomar" para chip pausado', () => {
      const chip = createMockChip({ status: 'paused' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText('Retomar Chip')).toBeInTheDocument()
    })

    it('mostra botão "Reativar" para chip banido', () => {
      const chip = createMockChip({ status: 'banned' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText('Reativar Chip')).toBeInTheDocument()
    })

    it('mostra botão "Reativar" para chip cancelado', () => {
      const chip = createMockChip({ status: 'cancelled' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText('Reativar Chip')).toBeInTheDocument()
    })

    it('mostra botão "Promover" para chip em warming com trust >= 70', () => {
      const chip = createMockChip({
        status: 'warming',
        warmupPhase: 'expansao',
        trustScore: 75,
      })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText('Promover Fase')).toBeInTheDocument()
    })

    it('NÃO mostra "Promover" para chip em warming com trust < 70', () => {
      const chip = createMockChip({
        status: 'warming',
        warmupPhase: 'expansao',
        trustScore: 60,
      })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.queryByText('Promover Fase')).not.toBeInTheDocument()
    })

    it('mostra botão "Gerar QR Code" para chip pending', () => {
      const chip = createMockChip({ status: 'pending' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText('Gerar QR Code')).toBeInTheDocument()
    })

    it('mostra botão "Verificar Conexão" para chip pending', () => {
      const chip = createMockChip({ status: 'pending' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText('Verificar Conexão')).toBeInTheDocument()
    })

    it('mostra mensagem quando nenhuma ação disponível', () => {
      // Chip em estado que não permite nenhuma ação (provisioned sem instanceName)
      const chip = createMockChip({ status: 'provisioned', instanceName: '' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(
        screen.getByText('Nenhuma ação disponível para este chip no momento.')
      ).toBeInTheDocument()
    })
  })

  describe('Ação de Pausar', () => {
    it('abre dialog de confirmação ao clicar em Pausar', async () => {
      const chip = createMockChip({ status: 'active' })
      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Pausar Chip'))

      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
      expect(screen.getByText(/deixará de enviar e receber mensagens/i)).toBeInTheDocument()
    })

    it('executa ação de pausar com sucesso', async () => {
      const chip = createMockChip({ status: 'active' })
      vi.mocked(chipsApi.pauseChip).mockResolvedValue({ success: true })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Pausar Chip'))
      await userEvent.click(screen.getByRole('button', { name: 'Pausar' }))

      await waitFor(() => {
        expect(chipsApi.pauseChip).toHaveBeenCalledWith('chip-123')
        expect(mockOnActionComplete).toHaveBeenCalled()
      })
    })
  })

  describe('Ação de Retomar', () => {
    it('executa ação de retomar com sucesso', async () => {
      const chip = createMockChip({ status: 'paused' })
      vi.mocked(chipsApi.resumeChip).mockResolvedValue({ success: true })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Retomar Chip'))
      await userEvent.click(screen.getByRole('button', { name: 'Retomar' }))

      await waitFor(() => {
        expect(chipsApi.resumeChip).toHaveBeenCalledWith('chip-123')
        expect(mockOnActionComplete).toHaveBeenCalled()
      })
    })
  })

  describe('Ação de Reativar', () => {
    it('requer motivo para reativar', async () => {
      const chip = createMockChip({ status: 'banned' })
      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Reativar Chip'))

      // Botão de confirmar deve estar desabilitado sem motivo
      const confirmButton = screen.getByRole('button', { name: 'Reativar' })
      expect(confirmButton).toBeDisabled()
    })

    it('executa reativação com motivo preenchido', async () => {
      const chip = createMockChip({ status: 'banned' })
      vi.mocked(chipsApi.reactivateChip).mockResolvedValue({ success: true })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Reativar Chip'))

      // Preencher motivo
      const textArea = screen.getByPlaceholderText(/recurso aprovado/i)
      await userEvent.type(textArea, 'Recurso aprovado pelo WhatsApp')

      // Agora pode confirmar
      await userEvent.click(screen.getByRole('button', { name: 'Reativar' }))

      await waitFor(() => {
        expect(chipsApi.reactivateChip).toHaveBeenCalledWith(
          'chip-123',
          'Recurso aprovado pelo WhatsApp'
        )
        expect(mockOnActionComplete).toHaveBeenCalled()
      })
    })

    it('mostra info sobre chip banido', () => {
      const chip = createMockChip({ status: 'banned' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText('Chip Banido')).toBeInTheDocument()
    })

    it('mostra info sobre chip cancelado', () => {
      const chip = createMockChip({ status: 'cancelled' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText('Chip Cancelado')).toBeInTheDocument()
    })
  })

  describe('Verificar Conexão', () => {
    it('verifica conexão e mostra resultado conectado', async () => {
      const chip = createMockChip({ status: 'pending' })
      vi.mocked(chipsApi.checkChipConnection).mockResolvedValue({
        success: true,
        connected: true,
        state: 'open',
        chip_id: 'chip-123',
        instance_name: 'julia_01',
        message: 'Conectado',
        status_atualizado: true,
        novo_status: 'warming',
      })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Verificar Conexão'))

      await waitFor(() => {
        expect(screen.getByText(/Conectado! Status atualizado para warming/i)).toBeInTheDocument()
        expect(mockOnActionComplete).toHaveBeenCalled()
      })
    })

    it('mostra mensagem de desconectado', async () => {
      const chip = createMockChip({ status: 'pending' })
      vi.mocked(chipsApi.checkChipConnection).mockResolvedValue({
        success: true,
        connected: false,
        state: 'close',
        chip_id: 'chip-123',
        instance_name: 'julia_01',
        message: 'Aguardando QR code',
      })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Verificar Conexão'))

      await waitFor(() => {
        expect(screen.getByText(/Desconectado/i)).toBeInTheDocument()
      })
    })
  })

  describe('QR Code', () => {
    it('abre dialog de QR code', async () => {
      const chip = createMockChip({ status: 'pending' })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Gerar QR Code'))

      expect(screen.getByText('Conectar WhatsApp')).toBeInTheDocument()
    })

    it('mostra QR code quando carregado', async () => {
      const chip = createMockChip({ status: 'pending' })
      vi.mocked(chipsApi.getInstanceQRCode).mockResolvedValue({
        qrCode: 'data:image/png;base64,abc123',
        state: 'close',
        pairingCode: '1234-5678',
      })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Gerar QR Code'))

      await waitFor(() => {
        expect(screen.getByAltText('QR Code WhatsApp')).toBeInTheDocument()
        expect(screen.getByText('1234-5678')).toBeInTheDocument()
      })
    })

    it('mostra estado conectado no dialog', async () => {
      const chip = createMockChip({ status: 'pending' })
      vi.mocked(chipsApi.getInstanceQRCode).mockResolvedValue({
        qrCode: null,
        state: 'open',
        pairingCode: null,
      })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Gerar QR Code'))

      await waitFor(() => {
        expect(screen.getByText('Conectado!')).toBeInTheDocument()
      })
    })
  })

  describe('Estados de erro', () => {
    it('mostra erro quando ação falha', async () => {
      const chip = createMockChip({ status: 'active' })
      vi.mocked(chipsApi.pauseChip).mockResolvedValue({
        success: false,
        message: 'Chip não pode ser pausado',
      })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Pausar Chip'))
      await userEvent.click(screen.getByRole('button', { name: 'Pausar' }))

      await waitFor(() => {
        expect(screen.getByText('Chip não pode ser pausado')).toBeInTheDocument()
      })
    })

    it('mostra erro genérico quando API lança exceção', async () => {
      const chip = createMockChip({ status: 'active' })
      vi.mocked(chipsApi.pauseChip).mockRejectedValue(new Error('Network error'))

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      await userEvent.click(screen.getByText('Pausar Chip'))
      await userEvent.click(screen.getByRole('button', { name: 'Pausar' }))

      await waitFor(() => {
        expect(screen.getByText('Erro ao executar ação')).toBeInTheDocument()
      })
    })
  })

  describe('Warmup info', () => {
    it('mostra informação de warming com dia atual', () => {
      const chip = createMockChip({
        status: 'warming',
        warmupPhase: 'primeiros_contatos',
        warmingDay: 5,
        trustScore: 65,
      })

      render(<ChipActionsPanel chip={chip} onActionComplete={mockOnActionComplete} />)

      expect(screen.getByText(/Em aquecimento - Dia 5/i)).toBeInTheDocument()
      expect(screen.getByText(/Trust score precisa ser ≥ 70/i)).toBeInTheDocument()
    })
  })
})
