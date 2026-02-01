import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ImportLinksModal } from '@/components/group-entry/import-links-modal'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
global.URL.revokeObjectURL = vi.fn()

describe('ImportLinksModal', () => {
  const mockOnClose = vi.fn()
  const mockOnImport = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders modal with title', () => {
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)
    expect(screen.getByText('Importar Links')).toBeInTheDocument()
  })

  it('renders description', () => {
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)
    expect(screen.getByText('Importe links de grupos via arquivo CSV ou Excel')).toBeInTheDocument()
  })

  it('renders drag-and-drop area', () => {
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)
    expect(screen.getByText('Arraste um arquivo CSV ou Excel aqui')).toBeInTheDocument()
  })

  it('renders file input link', () => {
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)
    expect(screen.getByText('ou selecione um arquivo')).toBeInTheDocument()
  })

  it('renders format info', () => {
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)
    expect(screen.getByText('Formato esperado:')).toBeInTheDocument()
  })

  it('renders download template button', () => {
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)
    expect(screen.getByText('Baixar template CSV')).toBeInTheDocument()
  })

  it('renders cancel button', () => {
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
  })

  it('renders send button (disabled by default)', () => {
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)
    const sendButton = screen.getByRole('button', { name: /Enviar/i })
    expect(sendButton).toBeDisabled()
  })

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup()
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    await user.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('enables send button when file is selected', async () => {
    const user = userEvent.setup()
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    const file = new File(['link,categoria\nhttps://chat.whatsapp.com/abc,medicos'], 'links.csv', {
      type: 'text/csv',
    })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null as HTMLInputElement | null
    if (input) {
      await user.upload(input, file)
      const sendButton = screen.getByRole('button', { name: /Enviar/i })
      expect(sendButton).not.toBeDisabled()
    }
  })

  it('shows file name after selection', async () => {
    const user = userEvent.setup()
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    const file = new File(['content'], 'my-links.csv', { type: 'text/csv' })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
    if (input) {
      await user.upload(input, file)
      expect(screen.getByText('my-links.csv')).toBeInTheDocument()
    }
  })

  it('shows remove button after file selection', async () => {
    const user = userEvent.setup()
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    const file = new File(['content'], 'links.csv', { type: 'text/csv' })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
    if (input) {
      await user.upload(input, file)
      expect(screen.getByText('Remover')).toBeInTheDocument()
    }
  })

  it('removes file when remove is clicked', async () => {
    const user = userEvent.setup()
    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    const file = new File(['content'], 'links.csv', { type: 'text/csv' })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
    if (input) {
      await user.upload(input, file)
      await user.click(screen.getByText('Remover'))

      // Should be back to initial state
      expect(screen.getByText('Arraste um arquivo CSV ou Excel aqui')).toBeInTheDocument()
    }
  })

  it('downloads template CSV when button is clicked', async () => {
    const user = userEvent.setup()
    const mockClick = vi.fn()
    const originalCreateElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      const element = originalCreateElement(tag)
      if (tag === 'a') {
        element.click = mockClick
      }
      return element
    })

    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    await user.click(screen.getByText('Baixar template CSV'))

    expect(global.URL.createObjectURL).toHaveBeenCalled()
    expect(mockClick).toHaveBeenCalled()

    vi.restoreAllMocks()
  })

  it('shows upload result after successful upload', async () => {
    const user = userEvent.setup()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          total: 10,
          valid: 8,
          duplicates: 1,
          invalid: 1,
          errors: [{ line: 5, error: 'Invalid URL' }],
        }),
    })

    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    const file = new File(['content'], 'links.csv', { type: 'text/csv' })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
    if (input) {
      await user.upload(input, file)
      await user.click(screen.getByRole('button', { name: /Enviar/i }))

      await waitFor(() => {
        expect(screen.getByText('Resultado da Importacao')).toBeInTheDocument()
      })

      expect(screen.getByText('Total:')).toBeInTheDocument()
      expect(screen.getByText('10')).toBeInTheDocument()
      expect(screen.getByText('Validos:')).toBeInTheDocument()
      expect(screen.getByText('8')).toBeInTheDocument()
    }
  })

  it('shows errors in result', async () => {
    const user = userEvent.setup()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          total: 10,
          valid: 8,
          duplicates: 1,
          invalid: 1,
          errors: [{ line: 5, error: 'Invalid URL' }],
        }),
    })

    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    const file = new File(['content'], 'links.csv', { type: 'text/csv' })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
    if (input) {
      await user.upload(input, file)
      await user.click(screen.getByRole('button', { name: /Enviar/i }))

      await waitFor(() => {
        expect(screen.getByText('Erros:')).toBeInTheDocument()
        expect(screen.getByText('Linha 5: Invalid URL')).toBeInTheDocument()
      })
    }
  })

  it('shows import button after result', async () => {
    const user = userEvent.setup()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          total: 10,
          valid: 8,
          duplicates: 1,
          invalid: 1,
          errors: [],
        }),
    })

    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    const file = new File(['content'], 'links.csv', { type: 'text/csv' })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
    if (input) {
      await user.upload(input, file)
      await user.click(screen.getByRole('button', { name: /Enviar/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Importar 8 links validos/i })).toBeInTheDocument()
      })
    }
  })

  it('calls onImport when import button is clicked', async () => {
    const user = userEvent.setup()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          total: 10,
          valid: 8,
          duplicates: 1,
          invalid: 1,
          errors: [],
        }),
    })

    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    const file = new File(['content'], 'links.csv', { type: 'text/csv' })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
    if (input) {
      await user.upload(input, file)
      await user.click(screen.getByRole('button', { name: /Enviar/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Importar 8 links validos/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /Importar 8 links validos/i }))
      expect(mockOnImport).toHaveBeenCalled()
    }
  })

  it('disables import button when no valid links', async () => {
    const user = userEvent.setup()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          total: 5,
          valid: 0,
          duplicates: 3,
          invalid: 2,
          errors: [],
        }),
    })

    render(<ImportLinksModal onClose={mockOnClose} onImport={mockOnImport} />)

    const file = new File(['content'], 'links.csv', { type: 'text/csv' })

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
    if (input) {
      await user.upload(input, file)
      await user.click(screen.getByRole('button', { name: /Enviar/i }))

      await waitFor(() => {
        const importButton = screen.getByRole('button', { name: /Importar 0 links validos/i })
        expect(importButton).toBeDisabled()
      })
    }
  })
})
