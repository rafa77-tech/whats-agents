/**
 * Tests for AttentionFeed component
 * Sprint 64: New triaging component for "Atenção" tab
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AttentionFeed } from '@/app/(dashboard)/conversas/components/attention-feed'
import type { ConversationListItem } from '@/types/conversas'

function makeConversation(overrides: Partial<ConversationListItem> = {}): ConversationListItem {
  return {
    id: 'conv-1',
    cliente_nome: 'Dr. Carlos Silva',
    cliente_telefone: '5511999999999',
    status: 'active',
    controlled_by: 'ai',
    unread_count: 0,
    ...overrides,
  }
}

describe('AttentionFeed', () => {
  it('shows empty state when no conversations', () => {
    render(
      <AttentionFeed
        conversations={[]}
        selectedId={null}
        onSelect={vi.fn()}
      />
    )

    expect(screen.getByText('Tudo sob controle')).toBeInTheDocument()
    expect(
      screen.getByText('Nenhuma conversa precisa de atencao no momento.')
    ).toBeInTheDocument()
  })

  it('renders conversation cards with name and attention reason', () => {
    const convs = [
      makeConversation({
        id: 'conv-1',
        controlled_by: 'human',
        attention_reason: 'Handoff pendente',
        last_message: 'Preciso falar com alguem',
      }),
    ]

    render(
      <AttentionFeed
        conversations={convs}
        selectedId={null}
        onSelect={vi.fn()}
      />
    )

    expect(screen.getByText('Dr. Carlos Silva')).toBeInTheDocument()
    expect(screen.getByText('Handoff pendente')).toBeInTheDocument()
  })

  it('shows last message in quotes', () => {
    const convs = [
      makeConversation({
        attention_reason: 'Sem resposta ha 2h',
        last_message: 'Tenho interesse na vaga',
      }),
    ]

    render(
      <AttentionFeed
        conversations={convs}
        selectedId={null}
        onSelect={vi.fn()}
      />
    )

    expect(screen.getByText(/Tenho interesse na vaga/)).toBeInTheDocument()
  })

  it('calls onSelect when conversation card is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    const convs = [
      makeConversation({
        attention_reason: 'Handoff pendente',
        controlled_by: 'human',
      }),
    ]

    render(
      <AttentionFeed
        conversations={convs}
        selectedId={null}
        onSelect={onSelect}
      />
    )

    await user.click(screen.getByText('Dr. Carlos Silva'))
    expect(onSelect).toHaveBeenCalledWith('conv-1')
  })

  it('shows "Ver conversa" button', () => {
    const convs = [
      makeConversation({
        attention_reason: 'Sem resposta ha 1h',
      }),
    ]

    render(
      <AttentionFeed
        conversations={convs}
        selectedId={null}
        onSelect={vi.fn()}
      />
    )

    expect(screen.getByText('Ver conversa')).toBeInTheDocument()
  })

  it('shows "Assumir" button for AI conversations when onAssume provided', () => {
    const convs = [
      makeConversation({
        controlled_by: 'ai',
        attention_reason: 'Sem resposta ha 2h',
      }),
    ]

    render(
      <AttentionFeed
        conversations={convs}
        selectedId={null}
        onSelect={vi.fn()}
        onAssume={vi.fn()}
      />
    )

    expect(screen.getByText('Assumir')).toBeInTheDocument()
  })

  it('does not show "Assumir" button for human-controlled conversations', () => {
    const convs = [
      makeConversation({
        controlled_by: 'human',
        attention_reason: 'Handoff pendente',
      }),
    ]

    render(
      <AttentionFeed
        conversations={convs}
        selectedId={null}
        onSelect={vi.fn()}
        onAssume={vi.fn()}
      />
    )

    expect(screen.queryByText('Assumir')).not.toBeInTheDocument()
  })

  it('highlights selected conversation', () => {
    const convs = [
      makeConversation({
        id: 'conv-1',
        attention_reason: 'Handoff pendente',
        controlled_by: 'human',
      }),
      makeConversation({
        id: 'conv-2',
        cliente_nome: 'Dr. Maria Santos',
        attention_reason: 'Sem resposta ha 1h',
      }),
    ]

    render(
      <AttentionFeed
        conversations={convs}
        selectedId="conv-1"
        onSelect={vi.fn()}
      />
    )

    // The selected card should have ring class
    const allButtons = screen.getAllByRole('button')
    // The div[role=button] cards contain the doctor names
    const card = allButtons.find((btn) => btn.textContent?.includes('Dr. Carlos Silva'))
    expect(card?.className).toContain('ring-2')
  })

  it('shows specialty when available', () => {
    const convs = [
      makeConversation({
        attention_reason: 'Handoff pendente',
        controlled_by: 'human',
        especialidade: 'Cardiologia',
      }),
    ]

    render(
      <AttentionFeed
        conversations={convs}
        selectedId={null}
        onSelect={vi.fn()}
      />
    )

    expect(screen.getByText('· Cardiologia')).toBeInTheDocument()
  })

  it('calls onAssume when Assumir button clicked', async () => {
    const user = userEvent.setup()
    const onAssume = vi.fn()
    const convs = [
      makeConversation({
        controlled_by: 'ai',
        attention_reason: 'Sem resposta ha 2h',
      }),
    ]

    render(
      <AttentionFeed
        conversations={convs}
        selectedId={null}
        onSelect={vi.fn()}
        onAssume={onAssume}
      />
    )

    await user.click(screen.getByText('Assumir'))
    expect(onAssume).toHaveBeenCalledWith('conv-1')
  })
})
