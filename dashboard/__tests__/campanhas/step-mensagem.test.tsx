/**
 * Testes do Step 3 - Mensagem do wizard de campanhas
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { StepMensagem } from '@/components/campanhas/wizard/step-mensagem'
import { type CampanhaFormData, INITIAL_FORM_DATA } from '@/components/campanhas/wizard/types'

describe('StepMensagem', () => {
  const mockUpdateField = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('para tipos com mensagem automática', () => {
    it('mostra card de mensagem automática para descoberta', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'descoberta',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Mensagem automática disponível')).toBeInTheDocument()
      expect(
        screen.getByText(/mensagem será gerada automaticamente usando aberturas dinâmicas/i)
      ).toBeInTheDocument()
    })

    it('mostra card de mensagem automática para reativacao', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'reativacao',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Mensagem automática disponível')).toBeInTheDocument()
      expect(screen.getByText(/Faz tempo que a gente nao se fala/i)).toBeInTheDocument()
    })

    it('mostra card de mensagem automática para followup', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'followup',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Mensagem automática disponível')).toBeInTheDocument()
      expect(screen.getByText(/Lembrei de vc/i)).toBeInTheDocument()
    })

    it('mostra label "(opcional)" para tipos com mensagem automática', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'descoberta',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText(/Mensagem \(opcional\)/)).toBeInTheDocument()
    })

    it('mostra indicação de mensagem automática quando corpo vazio', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'descoberta',
        corpo: '',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Será usada a mensagem automática do sistema')).toBeInTheDocument()
    })

    it('não mostra indicação de mensagem automática quando corpo preenchido', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'descoberta',
        corpo: 'Minha mensagem customizada',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(
        screen.queryByText('Será usada a mensagem automática do sistema')
      ).not.toBeInTheDocument()
    })
  })

  describe('para tipos que requerem mensagem', () => {
    it('não mostra card de mensagem automática para oferta_plantao', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.queryByText('Mensagem automática disponível')).not.toBeInTheDocument()
    })

    it('mostra label obrigatório "*" para oferta_plantao', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Mensagem *')).toBeInTheDocument()
    })

    it('não mostra indicação de mensagem automática para oferta_plantao', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
        corpo: '',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(
        screen.queryByText('Será usada a mensagem automática do sistema')
      ).not.toBeInTheDocument()
    })
  })

  describe('preview de mensagem', () => {
    it('mostra preview quando corpo está preenchido', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
        corpo: 'Oi {{nome}}! Tudo bem?',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Preview:')).toBeInTheDocument()
      expect(screen.getByText(/Oi Dr. Carlos! Tudo bem\?/)).toBeInTheDocument()
    })

    it('substitui variáveis no preview', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
        corpo: 'Oi {{nome}}! Vaga de {{especialidade}} no {{hospital}} por {{valor}}',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      const previewText = screen.getByText(/Oi Dr. Carlos!/i).textContent
      expect(previewText).toContain('Dr. Carlos')
      expect(previewText).toContain('Cardiologia')
      expect(previewText).toContain('Hospital Sao Luiz')
      expect(previewText).toContain('R$ 2.500')
    })

    it('não mostra preview quando corpo vazio', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
        corpo: '',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.queryByText('Preview:')).not.toBeInTheDocument()
    })
  })

  describe('interações', () => {
    it('chama updateField ao digitar no textarea', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
        corpo: '',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      const textarea = screen.getByRole('textbox')
      fireEvent.change(textarea, { target: { value: 'Nova mensagem' } })

      expect(mockUpdateField).toHaveBeenCalledWith('corpo', 'Nova mensagem')
    })

    it('mostra variáveis disponíveis', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText(/{{nome}}/)).toBeInTheDocument()
      expect(screen.getByText(/{{especialidade}}/)).toBeInTheDocument()
      expect(screen.getByText(/{{hospital}}/)).toBeInTheDocument()
      expect(screen.getByText(/{{valor}}/)).toBeInTheDocument()
    })
  })

  describe('seletor de tom', () => {
    it('renderiza select de tom', () => {
      const formData: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        tipo_campanha: 'oferta_plantao',
        tom: 'amigavel',
      }

      render(<StepMensagem formData={formData} updateField={mockUpdateField} />)

      expect(screen.getByText('Tom da Mensagem')).toBeInTheDocument()
    })
  })
})
