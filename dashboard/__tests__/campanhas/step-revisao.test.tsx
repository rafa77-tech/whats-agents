/**
 * Testes do Step 4 - Revisão do wizard de campanhas
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { StepRevisao } from '@/components/campanhas/wizard/step-revisao'
import { type CampanhaFormData, INITIAL_FORM_DATA } from '@/components/campanhas/wizard/types'

describe('StepRevisao', () => {
  const mockUpdateField = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('resumo da campanha', () => {
    it('exibe nome da campanha', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        nome_template: 'Campanha Teste ABC',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Campanha Teste ABC')).toBeInTheDocument()
    })

    it('exibe tipo de campanha formatado', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Oferta de Plantao')).toBeInTheDocument()
    })

    it('exibe categoria formatada', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        categoria: 'marketing',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Marketing')).toBeInTheDocument()
    })

    it('exibe tom formatado', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tom: 'profissional',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Profissional')).toBeInTheDocument()
    })

    it('exibe objetivo quando preenchido', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        objetivo: 'Prospectar novos médicos da região',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Prospectar novos médicos da região')).toBeInTheDocument()
    })

    it('não exibe objetivo quando vazio', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        objetivo: '',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      // Verifica que o label "Objetivo:" não está presente
      expect(screen.queryByText('Objetivo:')).not.toBeInTheDocument()
    })
  })

  describe('audiência', () => {
    it('exibe "Todos os medicos" quando audiencia_tipo é todos', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        audiencia_tipo: 'todos',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Todos os medicos')).toBeInTheDocument()
    })

    it('exibe contagem de filtros quando audiencia_tipo é filtrado', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        audiencia_tipo: 'filtrado',
        especialidades: ['cardiologia', 'anestesiologia'],
        regioes: ['SP', 'RJ', 'MG'],
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText(/Filtrada.*2 especialidades.*3 regioes/)).toBeInTheDocument()
    })
  })

  describe('chips excluídos', () => {
    it('exibe info quando há chips excluídos (singular)', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        chips_excluidos: ['chip-123'],
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText(/1 chip nao sera usado/)).toBeInTheDocument()
    })

    it('exibe info quando há múltiplos chips excluídos (plural)', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        chips_excluidos: ['chip-1', 'chip-2', 'chip-3'],
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText(/3 chips nao serao usados/)).toBeInTheDocument()
    })

    it('não exibe seção de chips quando não há exclusões', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        chips_excluidos: [],
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.queryByText(/chip.*nao sera/i)).not.toBeInTheDocument()
    })
  })

  describe('mensagem', () => {
    it('exibe mensagem customizada truncada se maior que 100 chars', () => {
      const longMessage = 'A'.repeat(150)
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
        corpo: longMessage,
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      // Deve mostrar os primeiros 100 chars + "..."
      expect(screen.getByText(/^A{100}\.\.\.$/)).toBeInTheDocument()
    })

    it('exibe mensagem customizada completa se menor que 100 chars', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
        corpo: 'Oi Dr {{nome}}! Tenho uma vaga pra vc',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Oi Dr {{nome}}! Tenho uma vaga pra vc')).toBeInTheDocument()
    })

    it('exibe "Mensagem automatica do sistema" para descoberta sem corpo', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'descoberta',
        corpo: '',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Mensagem automatica do sistema')).toBeInTheDocument()
    })

    it('exibe "Mensagem automatica do sistema" para reativacao sem corpo', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'reativacao',
        corpo: '',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Mensagem automatica do sistema')).toBeInTheDocument()
    })

    it('exibe "Mensagem automatica do sistema" para followup sem corpo', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'followup',
        corpo: '',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Mensagem automatica do sistema')).toBeInTheDocument()
    })

    it('exibe "Nao definida" para oferta_plantao sem corpo', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
        corpo: '',
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Nao definida')).toBeInTheDocument()
    })
  })

  describe('agendamento', () => {
    it('mostra checkbox de agendar envio', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Agendar envio')).toBeInTheDocument()
    })

    it('mostra campo de data quando agendar está marcado', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        agendar: true,
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Data e Hora do Envio')).toBeInTheDocument()
    })

    it('não mostra campo de data quando agendar não está marcado', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        agendar: false,
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.queryByText('Data e Hora do Envio')).not.toBeInTheDocument()
    })

    it('mostra mensagem de rascunho quando não vai agendar', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        agendar: false,
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText(/campanha sera salva como rascunho/i)).toBeInTheDocument()
    })

    it('chama updateField ao clicar no checkbox', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        agendar: false,
      }

      render(<StepRevisao formData={formData} updateField={mockUpdateField} />)

      const checkbox = screen.getByRole('checkbox')
      fireEvent.click(checkbox)

      expect(mockUpdateField).toHaveBeenCalledWith('agendar', true)
    })
  })
})
