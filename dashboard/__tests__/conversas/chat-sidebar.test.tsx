import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ChatSidebar } from '@/app/(dashboard)/conversas/components/chat-sidebar'
import type { ConversationListItem } from '@/types/conversas'

const mockConversations: ConversationListItem[] = [
  {
    id: '1',
    cliente_nome: 'Dr. João Silva',
    cliente_telefone: '5511999999999',
    status: 'active',
    controlled_by: 'ai',
    last_message: 'Olá, tudo bem?',
    last_message_at: new Date().toISOString(),
    unread_count: 2,
    chip: {
      id: 'chip-1',
      telefone: '5511888888888',
      instance_name: 'julia-01',
      status: 'active',
      trust_level: 'verde',
    },
  },
  {
    id: '2',
    cliente_nome: 'Dra. Maria Santos',
    cliente_telefone: '5511888888888',
    status: 'active',
    controlled_by: 'human',
    last_message: 'Preciso de ajuda',
    last_message_at: new Date(Date.now() - 3600000).toISOString(),
    unread_count: 0,
    chip: null,
  },
]

describe('ChatSidebar', () => {
  it('renders conversation list', () => {
    render(<ChatSidebar conversations={mockConversations} selectedId={null} onSelect={vi.fn()} />)

    expect(screen.getByText('Dr. João Silva')).toBeInTheDocument()
    expect(screen.getByText('Dra. Maria Santos')).toBeInTheDocument()
  })

  it('shows last message preview', () => {
    render(<ChatSidebar conversations={mockConversations} selectedId={null} onSelect={vi.fn()} />)

    expect(screen.getByText('Olá, tudo bem?')).toBeInTheDocument()
    expect(screen.getByText('Preciso de ajuda')).toBeInTheDocument()
  })

  it('shows unread count badge', () => {
    render(<ChatSidebar conversations={mockConversations} selectedId={null} onSelect={vi.fn()} />)

    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('highlights selected conversation', () => {
    render(<ChatSidebar conversations={mockConversations} selectedId="1" onSelect={vi.fn()} />)

    const buttons = screen.getAllByRole('button')
    const selectedButton = buttons.find((btn) => btn.textContent?.includes('Dr. João Silva'))
    expect(selectedButton).toHaveClass('bg-muted')
  })

  it('calls onSelect when conversation is clicked', () => {
    const onSelect = vi.fn()
    render(<ChatSidebar conversations={mockConversations} selectedId={null} onSelect={onSelect} />)

    const buttons = screen.getAllByRole('button')
    const conversationButton = buttons.find((btn) => btn.textContent?.includes('Dr. João Silva'))
    expect(conversationButton).toBeDefined()

    if (conversationButton) {
      fireEvent.click(conversationButton)
      expect(onSelect).toHaveBeenCalledWith('1')
    }
  })

  it('shows handoff indicator for human-controlled conversations', () => {
    render(<ChatSidebar conversations={mockConversations} selectedId={null} onSelect={vi.fn()} />)

    // The human-controlled conversation uses bg-state-handoff on the avatar
    const buttons = screen.getAllByRole('button')
    const humanControlledButton = buttons.find((btn) =>
      btn.textContent?.includes('Dra. Maria Santos')
    )
    expect(humanControlledButton).toBeDefined()

    // Check for handoff state styling on avatar fallback
    const handoffAvatar = humanControlledButton?.querySelector('.bg-state-handoff')
    expect(handoffAvatar).toBeInTheDocument()
  })

  it('shows load more button when hasMore is true', () => {
    const onLoadMore = vi.fn()
    render(
      <ChatSidebar
        conversations={mockConversations}
        selectedId={null}
        onSelect={vi.fn()}
        hasMore={true}
        onLoadMore={onLoadMore}
      />
    )

    const loadMoreButton = screen.getByText(/carregar mais/i)
    expect(loadMoreButton).toBeInTheDocument()

    fireEvent.click(loadMoreButton)
    expect(onLoadMore).toHaveBeenCalled()
  })

  it('does not show load more button when hasMore is false', () => {
    render(
      <ChatSidebar
        conversations={mockConversations}
        selectedId={null}
        onSelect={vi.fn()}
        hasMore={false}
      />
    )

    expect(screen.queryByText(/carregar mais/i)).not.toBeInTheDocument()
  })

  it('shows specialty when available', () => {
    const base = mockConversations[0]!
    const convWithSpecialty: ConversationListItem[] = [
      {
        ...base,
        especialidade: 'Cardiologia',
      },
    ]

    render(
      <ChatSidebar
        conversations={convWithSpecialty}
        selectedId={null}
        onSelect={vi.fn()}
      />
    )

    expect(screen.getByText('· Cardiologia')).toBeInTheDocument()
  })
})
