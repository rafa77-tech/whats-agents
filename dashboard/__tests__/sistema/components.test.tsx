/**
 * Testes para componentes de Sistema
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { EditRateLimitModal } from '@/components/sistema/edit-rate-limit-modal'
import { EditScheduleModal } from '@/components/sistema/edit-schedule-modal'
import { SafeModeCard } from '@/components/sistema/safe-mode-card'

const mockFetch = vi.fn()

describe('EditRateLimitModal', () => {
  const defaultProps = {
    currentConfig: {
      msgs_por_hora: 20,
      msgs_por_dia: 100,
      intervalo_min: 45,
      intervalo_max: 180,
    },
    onClose: vi.fn(),
    onSave: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = mockFetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve renderizar o modal com valores atuais', () => {
    render(<EditRateLimitModal {...defaultProps} />)

    expect(screen.getByText('Editar Rate Limiting')).toBeInTheDocument()
    expect(screen.getByLabelText('Mensagens por hora')).toHaveValue(20)
    expect(screen.getByLabelText('Mensagens por dia')).toHaveValue(100)
    expect(screen.getByLabelText('Intervalo min (s)')).toHaveValue(45)
    expect(screen.getByLabelText('Intervalo max (s)')).toHaveValue(180)
  })

  it('deve mostrar botao Cancelar', () => {
    render(<EditRateLimitModal {...defaultProps} />)

    expect(screen.getByText('Cancelar')).toBeInTheDocument()
  })

  it('deve mostrar botao Salvar Alteracoes', () => {
    render(<EditRateLimitModal {...defaultProps} />)

    expect(screen.getByText('Salvar Alteracoes')).toBeInTheDocument()
  })

  it('deve chamar onClose ao clicar em Cancelar', async () => {
    const onClose = vi.fn()
    render(<EditRateLimitModal {...defaultProps} onClose={onClose} />)

    fireEvent.click(screen.getByText('Cancelar'))

    expect(onClose).toHaveBeenCalled()
  })

  it('deve permitir alterar valores', async () => {
    render(<EditRateLimitModal {...defaultProps} />)

    const msgsHoraInput = screen.getByLabelText('Mensagens por hora')
    fireEvent.change(msgsHoraInput, { target: { value: '25' } })

    expect(msgsHoraInput).toHaveValue(25)
  })

  it('deve mostrar alerta quando valores sao de alto risco', async () => {
    const user = userEvent.setup()
    render(<EditRateLimitModal {...defaultProps} />)

    const msgsHoraInput = screen.getByLabelText('Mensagens por hora')
    await user.clear(msgsHoraInput)
    await user.type(msgsHoraInput, '30')

    await waitFor(() => {
      expect(screen.getByText('Atencao')).toBeInTheDocument()
    })
  })

  it('deve chamar API e onSave ao salvar', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })

    render(<EditRateLimitModal {...defaultProps} onSave={onSave} />)

    await user.click(screen.getByText('Salvar Alteracoes'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sistema/config',
        expect.objectContaining({
          method: 'PATCH',
        })
      )
      expect(onSave).toHaveBeenCalled()
    })
  })
})

describe('EditScheduleModal', () => {
  const defaultProps = {
    currentConfig: {
      inicio: 8,
      fim: 20,
      dias: 'Segunda a Sexta',
    },
    onClose: vi.fn(),
    onSave: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = mockFetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve renderizar o modal com valores atuais', () => {
    render(<EditScheduleModal {...defaultProps} />)

    expect(screen.getByText('Editar Horario de Operacao')).toBeInTheDocument()
    expect(screen.getByLabelText('Hora de inicio')).toHaveValue(8)
    expect(screen.getByLabelText('Hora de fim')).toHaveValue(20)
  })

  it('deve mostrar todos os dias da semana', () => {
    render(<EditScheduleModal {...defaultProps} />)

    expect(screen.getByText('Seg')).toBeInTheDocument()
    expect(screen.getByText('Ter')).toBeInTheDocument()
    expect(screen.getByText('Qua')).toBeInTheDocument()
    expect(screen.getByText('Qui')).toBeInTheDocument()
    expect(screen.getByText('Sex')).toBeInTheDocument()
    expect(screen.getByText('Sab')).toBeInTheDocument()
    expect(screen.getByText('Dom')).toBeInTheDocument()
  })

  it('deve mostrar nota informativa', () => {
    render(<EditScheduleModal {...defaultProps} />)

    expect(
      screen.getByText(/Julia so enviara mensagens proativas dentro deste horario/)
    ).toBeInTheDocument()
  })

  it('deve chamar onClose ao clicar em Cancelar', async () => {
    const onClose = vi.fn()
    render(<EditScheduleModal {...defaultProps} onClose={onClose} />)

    fireEvent.click(screen.getByText('Cancelar'))

    expect(onClose).toHaveBeenCalled()
  })

  it('deve permitir toggle de dias', async () => {
    const user = userEvent.setup()
    render(<EditScheduleModal {...defaultProps} />)

    // Sab deve estar deselecionado (Segunda a Sexta = seg-sex)
    const sabButton = screen.getByText('Sab')
    await user.click(sabButton)

    // Depois de clicar, deve estar selecionado (variant=default)
    // Podemos verificar visualmente pela classe ou attribute
  })

  it('deve desabilitar salvar quando nenhum dia selecionado', async () => {
    const user = userEvent.setup()
    render(<EditScheduleModal {...defaultProps} />)

    // Deselecionar todos os dias
    const dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex']
    for (const dia of dias) {
      await user.click(screen.getByText(dia))
    }

    await waitFor(() => {
      expect(screen.getByText('Salvar Alteracoes')).toBeDisabled()
    })
  })
})

describe('SafeModeCard', () => {
  const defaultProps = {
    isActive: false,
    onActivate: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = mockFetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve renderizar titulo', () => {
    render(<SafeModeCard {...defaultProps} />)

    expect(screen.getByText('Safe Mode Emergencial')).toBeInTheDocument()
    expect(screen.getByText('Para imediatamente todas as operacoes')).toBeInTheDocument()
  })

  it('deve mostrar estado inativo quando isActive=false', () => {
    render(<SafeModeCard {...defaultProps} isActive={false} />)

    expect(screen.getByText('INATIVO')).toBeInTheDocument()
    expect(screen.getByText('ATIVAR')).toBeInTheDocument()
  })

  it('deve mostrar estado ativo quando isActive=true', () => {
    render(<SafeModeCard {...defaultProps} isActive={true} />)

    expect(screen.getByText('Safe Mode ATIVO')).toBeInTheDocument()
    expect(screen.getByText('Sistema Protegido')).toBeInTheDocument()
  })

  it('deve listar operacoes afetadas quando inativo', () => {
    render(<SafeModeCard {...defaultProps} isActive={false} />)

    expect(screen.getByText('Envio de mensagens')).toBeInTheDocument()
    expect(screen.getByText('Processamento de fila')).toBeInTheDocument()
    expect(screen.getByText('Jobs autonomos')).toBeInTheDocument()
    expect(screen.getByText('Entrada em grupos')).toBeInTheDocument()
  })

  it('deve abrir dialog de confirmacao ao clicar ATIVAR', async () => {
    const user = userEvent.setup()
    render(<SafeModeCard {...defaultProps} isActive={false} />)

    await user.click(screen.getByText('ATIVAR'))

    await waitFor(() => {
      expect(screen.getByText('ATIVAR SAFE MODE?')).toBeInTheDocument()
    })
  })

  it('deve exigir motivo para confirmar', async () => {
    const user = userEvent.setup()
    render(<SafeModeCard {...defaultProps} isActive={false} />)

    await user.click(screen.getByText('ATIVAR'))

    await waitFor(() => {
      expect(screen.getByText('Motivo (obrigatorio)')).toBeInTheDocument()
    })

    // Botao de confirmar deve estar desabilitado sem motivo
    expect(screen.getByText('CONFIRMAR SAFE MODE')).toBeDisabled()
  })

  it('deve habilitar botao quando motivo preenchido', async () => {
    const user = userEvent.setup()
    render(<SafeModeCard {...defaultProps} isActive={false} />)

    await user.click(screen.getByText('ATIVAR'))

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Descreva o motivo/)).toBeInTheDocument()
    })

    await user.type(screen.getByPlaceholderText(/Descreva o motivo/), 'Problema critico')

    await waitFor(() => {
      expect(screen.getByText('CONFIRMAR SAFE MODE')).not.toBeDisabled()
    })
  })

  it('deve fechar dialog ao clicar Cancelar', async () => {
    const user = userEvent.setup()
    render(<SafeModeCard {...defaultProps} isActive={false} />)

    await user.click(screen.getByText('ATIVAR'))

    await waitFor(() => {
      expect(screen.getByText('ATIVAR SAFE MODE?')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Cancelar'))

    await waitFor(() => {
      expect(screen.queryByText('ATIVAR SAFE MODE?')).not.toBeInTheDocument()
    })
  })

  it('deve chamar APIs ao confirmar safe mode', async () => {
    const user = userEvent.setup()
    const onActivate = vi.fn()
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })

    render(<SafeModeCard {...defaultProps} isActive={false} onActivate={onActivate} />)

    await user.click(screen.getByText('ATIVAR'))

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Descreva o motivo/)).toBeInTheDocument()
    })

    await user.type(screen.getByPlaceholderText(/Descreva o motivo/), 'Problema critico')
    await user.click(screen.getByText('CONFIRMAR SAFE MODE'))

    await waitFor(() => {
      // Deve chamar pilot-mode API
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sistema/pilot-mode',
        expect.objectContaining({
          method: 'POST',
        })
      )
      // Deve chamar features APIs para desabilitar cada uma
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/sistema/features/'),
        expect.anything()
      )
      expect(onActivate).toHaveBeenCalled()
    })
  })
})
