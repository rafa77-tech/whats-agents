/**
 * Tests for MessageFlowWidget (Sprint 56)
 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MessageFlowWidget } from '@/components/dashboard/message-flow/message-flow-widget'
import type { MessageFlowData, ChipNode, RecentMessage } from '@/types/dashboard'

// Mock CSS import
vi.mock('@/components/dashboard/message-flow/message-flow.css', () => ({}))

function createMockChip(overrides: Partial<ChipNode> = {}): ChipNode {
  return {
    id: 'chip-1',
    name: 'Julia-01',
    status: 'active',
    trustScore: 85,
    recentOutbound: 3,
    recentInbound: 2,
    isActive: true,
    ...overrides,
  }
}

function createMockMessage(overrides: Partial<RecentMessage> = {}): RecentMessage {
  return {
    id: 'msg-1',
    chipId: 'chip-1',
    direction: 'outbound',
    timestamp: new Date().toISOString(),
    ...overrides,
  }
}

function createMockData(overrides: Partial<MessageFlowData> = {}): MessageFlowData {
  return {
    chips: [createMockChip()],
    recentMessages: [createMockMessage()],
    messagesPerMinute: 5,
    updatedAt: new Date().toISOString(),
    ...overrides,
  }
}

describe('MessageFlowWidget', () => {
  it('renderiza skeleton durante loading', () => {
    render(<MessageFlowWidget data={null} isLoading={true} />)
    // Loading skeleton has pulse animation divs
    const card = document.querySelector('.animate-pulse')
    expect(card).toBeInTheDocument()
  })

  it('renderiza "Nenhum chip ativo" com chips vazio', () => {
    const data = createMockData({ chips: [], recentMessages: [] })
    render(<MessageFlowWidget data={data} isLoading={false} />)
    expect(screen.getByText('Nenhum chip ativo')).toBeInTheDocument()
  })

  it('renderiza "Nenhum chip ativo" com data null', () => {
    render(<MessageFlowWidget data={null} isLoading={false} />)
    expect(screen.getByText('Nenhum chip ativo')).toBeInTheDocument()
  })

  it('renderiza titulo "Message Flow"', () => {
    const data = createMockData()
    render(<MessageFlowWidget data={data} isLoading={false} />)
    expect(screen.getByText('Message Flow')).toBeInTheDocument()
  })

  it('mostra badge msg/min quando messagesPerMinute > 0', () => {
    const data = createMockData({ messagesPerMinute: 12 })
    render(<MessageFlowWidget data={data} isLoading={false} />)
    expect(screen.getByText('12/min')).toBeInTheDocument()
  })

  it('não mostra badge msg/min quando messagesPerMinute = 0', () => {
    const data = createMockData({ messagesPerMinute: 0 })
    render(<MessageFlowWidget data={data} isLoading={false} />)
    expect(screen.queryByText('0/min')).not.toBeInTheDocument()
  })

  it('renderiza SVG com aria-label descritivo em desktop', () => {
    const data = createMockData({
      chips: [
        createMockChip({ id: 'c1', name: 'Chip-01' }),
        createMockChip({ id: 'c2', name: 'Chip-02' }),
      ],
      messagesPerMinute: 7,
    })
    render(<MessageFlowWidget data={data} isLoading={false} />)
    const svg = document.querySelector('svg[role="img"]')
    expect(svg).toBeInTheDocument()
    expect(svg?.getAttribute('aria-label')).toContain('2 chips')
    expect(svg?.getAttribute('aria-label')).toContain('7 mensagens por minuto')
  })

  it('renderiza nó Jull.ia no SVG', () => {
    const data = createMockData()
    render(<MessageFlowWidget data={data} isLoading={false} />)
    const juliaTexts = screen.getAllByText('Jull.ia')
    expect(juliaTexts.length).toBeGreaterThanOrEqual(1)
  })

  it('renderiza chips com nome truncado', () => {
    const data = createMockData({
      chips: [createMockChip({ id: 'c1', name: 'MuitoLongoChipNameAqui' })],
    })
    render(<MessageFlowWidget data={data} isLoading={false} />)
    expect(screen.getByText('MuitoLongoCh')).toBeInTheDocument()
  })

  it('não quebra com 15 chips (máximo)', () => {
    const chips = Array.from({ length: 15 }, (_, i) =>
      createMockChip({ id: `c${i}`, name: `Chip-${i}` })
    )
    const data = createMockData({ chips })
    render(<MessageFlowWidget data={data} isLoading={false} />)
    expect(screen.getByText('Message Flow')).toBeInTheDocument()
  })

  it('renderiza MobilePulse no mobile viewport', () => {
    const data = createMockData({
      chips: [
        createMockChip({ isActive: true }),
        createMockChip({ id: 'c2', name: 'Chip-02', isActive: false }),
      ],
    })
    render(<MessageFlowWidget data={data} isLoading={false} />)
    // MobilePulse shows "Julia Ativa" or "Julia Idle"
    // It's rendered but hidden on desktop via CSS, visible on mobile
    const mobileContent = screen.getByText(/Julia (Ativa|Idle)/)
    expect(mobileContent).toBeInTheDocument()
  })

  it('renderiza legenda com status', () => {
    const data = createMockData()
    render(<MessageFlowWidget data={data} isLoading={false} />)
    expect(screen.getByText('ativo')).toBeInTheDocument()
    expect(screen.getByText('aquecendo')).toBeInTheDocument()
    expect(screen.getByText('degradado')).toBeInTheDocument()
    expect(screen.getByText('pausado')).toBeInTheDocument()
  })

  it('renderiza legenda com direções', () => {
    const data = createMockData()
    render(<MessageFlowWidget data={data} isLoading={false} />)
    expect(screen.getByText('enviada')).toBeInTheDocument()
    expect(screen.getByText('recebida')).toBeInTheDocument()
  })
})
