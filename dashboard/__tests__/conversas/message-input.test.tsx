import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MessageInput } from '@/app/(dashboard)/conversas/components/message-input'

// Mock emoji-mart
vi.mock('@emoji-mart/react', () => ({
  default: ({ onEmojiSelect }: { onEmojiSelect: (emoji: { native: string }) => void }) => (
    <div data-testid="emoji-picker">
      <button onClick={() => onEmojiSelect({ native: '😀' })}>Select Emoji</button>
    </div>
  ),
}))

vi.mock('@emoji-mart/data', () => ({
  default: {},
}))

describe('MessageInput', () => {
  const mockOnSend = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders textarea and buttons', () => {
    render(<MessageInput onSend={mockOnSend} />)

    expect(screen.getByPlaceholderText(/digite sua mensagem/i)).toBeInTheDocument()
    // Check that there are buttons (emoji, attachment, mic)
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThanOrEqual(3)
  })

  it('allows typing in textarea', async () => {
    const user = userEvent.setup()
    render(<MessageInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/digite sua mensagem/i)
    await user.type(textarea, 'Hello world')

    expect(textarea).toHaveValue('Hello world')
  })

  it('shows send button when text is entered', async () => {
    const user = userEvent.setup()
    render(<MessageInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/digite sua mensagem/i)
    await user.type(textarea, 'Hello')

    // Should show send button (with Send icon) instead of mic button
    // We can detect this by looking for the bg-emerald-600 class on a button
    const buttons = screen.getAllByRole('button')
    const sendButton = buttons.find((btn) => btn.classList.contains('bg-emerald-600'))
    expect(sendButton).toBeDefined()
  })

  it('calls onSend when send button is clicked', async () => {
    const user = userEvent.setup()
    render(<MessageInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/digite sua mensagem/i)
    await user.type(textarea, 'Hello world')

    // Find send button by its emerald styling
    const buttons = screen.getAllByRole('button')
    const sendButton = buttons.find((btn) => btn.classList.contains('bg-emerald-600'))
    expect(sendButton).toBeDefined()

    if (sendButton) {
      await user.click(sendButton)

      await waitFor(() => {
        expect(mockOnSend).toHaveBeenCalledWith('Hello world', undefined)
      })
    }
  })

  it('calls onSend when Enter is pressed', async () => {
    const user = userEvent.setup()
    render(<MessageInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/digite sua mensagem/i)
    await user.type(textarea, 'Hello world')
    await user.keyboard('{Enter}')

    await waitFor(() => {
      expect(mockOnSend).toHaveBeenCalledWith('Hello world', undefined)
    })
  })

  it('does not send on Shift+Enter (allows line break)', async () => {
    const user = userEvent.setup()
    render(<MessageInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/digite sua mensagem/i)
    await user.type(textarea, 'Hello')
    await user.keyboard('{Shift>}{Enter}{/Shift}')
    await user.type(textarea, 'World')

    expect(mockOnSend).not.toHaveBeenCalled()
    expect(textarea).toHaveValue('Hello\nWorld')
  })

  it('clears input after sending', async () => {
    const user = userEvent.setup()
    mockOnSend.mockResolvedValue(undefined)

    render(<MessageInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/digite sua mensagem/i)
    await user.type(textarea, 'Hello world')
    await user.keyboard('{Enter}')

    await waitFor(() => {
      expect(textarea).toHaveValue('')
    })
  })

  it('disables input when disabled prop is true', () => {
    render(<MessageInput onSend={mockOnSend} disabled />)

    const textarea = screen.getByPlaceholderText(/digite sua mensagem/i)
    expect(textarea).toBeDisabled()
  })

  it('uses custom placeholder when provided', () => {
    render(<MessageInput onSend={mockOnSend} placeholder="Custom placeholder" />)

    expect(screen.getByPlaceholderText('Custom placeholder')).toBeInTheDocument()
  })

  it('does not send empty messages', async () => {
    const user = userEvent.setup()
    render(<MessageInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText(/digite sua mensagem/i)
    await user.type(textarea, '   ')
    await user.keyboard('{Enter}')

    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('shows attachment menu when paperclip is clicked', async () => {
    const user = userEvent.setup()
    render(<MessageInput onSend={mockOnSend} />)

    // Find paperclip button by looking for the lucide-paperclip class on an SVG inside a button
    const buttons = screen.getAllByRole('button')
    const attachButton = buttons.find((btn) => btn.querySelector('svg.lucide-paperclip'))

    if (attachButton) {
      await user.click(attachButton)

      // Menu should appear with Imagem and Documento options
      await waitFor(() => {
        expect(screen.getByText('Imagem')).toBeInTheDocument()
        expect(screen.getByText('Documento')).toBeInTheDocument()
      })
    } else {
      // If no paperclip button found, the test structure may have changed
      expect(attachButton).toBeDefined()
    }
  })
})
