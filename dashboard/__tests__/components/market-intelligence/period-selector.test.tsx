/**
 * Testes Unitarios - PeriodSelector
 *
 * Nota: Os testes de interacao com Radix UI Select sao limitados em JSDOM.
 * Testes mais complexos devem ser feitos via E2E (Playwright/Cypress).
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PeriodSelector } from '@/components/market-intelligence/period-selector'

// Mock de funcoes DOM para JSDOM (necessario para Radix UI)
beforeAll(() => {
  HTMLElement.prototype.hasPointerCapture = vi.fn(() => false)
  HTMLElement.prototype.setPointerCapture = vi.fn()
  HTMLElement.prototype.releasePointerCapture = vi.fn()
  HTMLElement.prototype.scrollIntoView = vi.fn()
  Element.prototype.scrollIntoView = vi.fn()
})

describe('PeriodSelector', () => {
  const mockOnChange = vi.fn()
  const mockOnCustomChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Renderizacao', () => {
    it('deve renderizar com valor selecionado', () => {
      render(<PeriodSelector value="30d" onChange={mockOnChange} />)

      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    it('deve exibir texto do periodo selecionado 30d', () => {
      render(<PeriodSelector value="30d" onChange={mockOnChange} />)

      expect(screen.getByText('Ultimos 30 dias')).toBeInTheDocument()
    })

    it('deve exibir texto do periodo selecionado 7d', () => {
      render(<PeriodSelector value="7d" onChange={mockOnChange} />)

      expect(screen.getByText('Ultimos 7 dias')).toBeInTheDocument()
    })

    it('deve exibir texto do periodo selecionado 90d', () => {
      render(<PeriodSelector value="90d" onChange={mockOnChange} />)

      expect(screen.getByText('Ultimos 90 dias')).toBeInTheDocument()
    })

    it('deve exibir texto do periodo custom', () => {
      render(<PeriodSelector value="custom" onChange={mockOnChange} />)

      expect(screen.getByText('Personalizado')).toBeInTheDocument()
    })
  })

  describe('Selecao de Periodo', () => {
    it('deve abrir dropdown ao clicar no combobox', async () => {
      const user = userEvent.setup()
      render(<PeriodSelector value="30d" onChange={mockOnChange} />)

      const select = screen.getByRole('combobox')
      await user.click(select)

      // O dropdown deve ter expanded=true
      expect(select).toHaveAttribute('aria-expanded', 'true')
    })

    it('deve chamar onChange ao selecionar periodo 7d', async () => {
      const user = userEvent.setup()
      render(<PeriodSelector value="30d" onChange={mockOnChange} />)

      const select = screen.getByRole('combobox')
      await user.click(select)

      const option = screen.getByRole('option', { name: 'Ultimos 7 dias' })
      await user.click(option)

      expect(mockOnChange).toHaveBeenCalledWith('7d')
    })

    it('deve chamar onChange ao selecionar periodo 90d', async () => {
      const user = userEvent.setup()
      render(<PeriodSelector value="30d" onChange={mockOnChange} />)

      const select = screen.getByRole('combobox')
      await user.click(select)

      const option = screen.getByRole('option', { name: 'Ultimos 90 dias' })
      await user.click(option)

      expect(mockOnChange).toHaveBeenCalledWith('90d')
    })
  })

  describe('Opcoes Disponiveis', () => {
    it('deve ter todas as opcoes de periodo', async () => {
      const user = userEvent.setup()
      render(<PeriodSelector value="30d" onChange={mockOnChange} />)

      await user.click(screen.getByRole('combobox'))

      expect(screen.getByRole('option', { name: 'Ultimos 7 dias' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Ultimos 30 dias' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Ultimos 90 dias' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Personalizado' })).toBeInTheDocument()
    })
  })

  describe('Periodo Personalizado (valor custom)', () => {
    it('deve mostrar botao de calendario quando value=custom', () => {
      render(
        <PeriodSelector
          value="custom"
          onChange={mockOnChange}
          onCustomChange={mockOnCustomChange}
        />
      )

      // Deve haver botoes (combobox e possivelmente calendario)
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThanOrEqual(1)
    })

    it('deve renderizar com props de custom change', () => {
      render(
        <PeriodSelector
          value="custom"
          onChange={mockOnChange}
          onCustomChange={mockOnCustomChange}
        />
      )

      expect(screen.getByText('Personalizado')).toBeInTheDocument()
    })
  })

  describe('Acessibilidade', () => {
    it('deve ter role=combobox no trigger', () => {
      render(<PeriodSelector value="30d" onChange={mockOnChange} />)

      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    it('deve ter aria-expanded apropriado', async () => {
      const user = userEvent.setup()
      render(<PeriodSelector value="30d" onChange={mockOnChange} />)

      const combobox = screen.getByRole('combobox')

      // Fechado inicialmente
      expect(combobox).toHaveAttribute('aria-expanded', 'false')

      // Aberto apos click
      await user.click(combobox)
      expect(combobox).toHaveAttribute('aria-expanded', 'true')
    })
  })
})
