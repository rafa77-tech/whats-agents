/**
 * Tests for ConversationSummary component
 * Sprint 64: New summary display above chat messages
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConversationSummary } from '@/app/(dashboard)/conversas/components/conversation-summary'
import type { ConversationSummary as SummaryType } from '@/types/conversas'

const baseSummary: SummaryType = {
  text: 'Dr. Carlos, Cardiologia. Demonstrou interesse. 15 mensagens trocadas (8 medico, 7 Julia).',
  total_msg_medico: 8,
  total_msg_julia: 7,
  duracao_dias: 3,
}

describe('ConversationSummary', () => {
  it('renders summary text', () => {
    render(<ConversationSummary summary={baseSummary} />)

    expect(screen.getByText(baseSummary.text)).toBeInTheDocument()
  })

  it('shows message counts', () => {
    render(<ConversationSummary summary={baseSummary} />)

    expect(screen.getByText('8 medico / 7 Julia')).toBeInTheDocument()
  })

  it('shows duration when > 0 days', () => {
    render(<ConversationSummary summary={baseSummary} />)

    expect(screen.getByText('3 dias')).toBeInTheDocument()
  })

  it('does not show duration when 0 days', () => {
    const summary = { ...baseSummary, duracao_dias: 0 }
    render(<ConversationSummary summary={summary} />)

    expect(screen.queryByText(/dia/)).not.toBeInTheDocument()
  })

  it('shows singular "dia" for 1 day', () => {
    const summary = { ...baseSummary, duracao_dias: 1 }
    render(<ConversationSummary summary={summary} />)

    expect(screen.getByText('1 dia')).toBeInTheDocument()
  })

  it('can be dismissed', async () => {
    const user = userEvent.setup()
    const { container } = render(<ConversationSummary summary={baseSummary} />)

    // Summary should be visible
    expect(screen.getByText(baseSummary.text)).toBeInTheDocument()

    // Click dismiss button
    const dismissButton = screen.getByRole('button')
    await user.click(dismissButton)

    // Summary should be gone
    expect(container.firstChild).toBeNull()
  })

  it('shows Resumo label', () => {
    render(<ConversationSummary summary={baseSummary} />)

    expect(screen.getByText('Resumo')).toBeInTheDocument()
  })
})
