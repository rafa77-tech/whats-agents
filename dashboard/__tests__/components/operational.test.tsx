/**
 * Tests for operational status components
 * - components/dashboard/operational-status.tsx
 * - components/dashboard/instance-status-list.tsx
 * - components/dashboard/dashboard-header.tsx
 * - components/dashboard/conversion-funnel.tsx
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OperationalStatus } from '@/components/dashboard/operational-status'
import { InstanceStatusList } from '@/components/dashboard/instance-status-list'
import { type OperationalStatusData, type WhatsAppInstance } from '@/types/dashboard'

describe('InstanceStatusList', () => {
  const mockInstances: WhatsAppInstance[] = [
    { name: 'Julia01', status: 'online', messagesToday: 50 },
    { name: 'Julia02', status: 'offline', messagesToday: 30 },
    { name: 'Julia03', status: 'online', messagesToday: 100 },
  ]

  it('should render title', () => {
    render(<InstanceStatusList instances={mockInstances} />)
    expect(screen.getByText('Instancias WhatsApp')).toBeInTheDocument()
  })

  it('should render all instances', () => {
    render(<InstanceStatusList instances={mockInstances} />)
    expect(screen.getByText('Julia01')).toBeInTheDocument()
    expect(screen.getByText('Julia02')).toBeInTheDocument()
    expect(screen.getByText('Julia03')).toBeInTheDocument()
  })

  it('should display message count for each instance', () => {
    render(<InstanceStatusList instances={mockInstances} />)
    expect(screen.getByText('50 msgs')).toBeInTheDocument()
    expect(screen.getByText('30 msgs')).toBeInTheDocument()
    expect(screen.getByText('100 msgs')).toBeInTheDocument()
  })

  it('should show success indicator for online instances', () => {
    render(<InstanceStatusList instances={mockInstances} />)
    const successIndicators = document.querySelectorAll('.bg-status-success-solid')
    expect(successIndicators.length).toBe(2) // Julia01 and Julia03 are online
  })

  it('should show error indicator for offline instances', () => {
    render(<InstanceStatusList instances={mockInstances} />)
    const errorIndicators = document.querySelectorAll('.bg-status-error-solid')
    expect(errorIndicators.length).toBe(1) // Julia02 is offline
  })

  it('should render empty list when no instances', () => {
    render(<InstanceStatusList instances={[]} />)
    expect(screen.getByText('Instancias WhatsApp')).toBeInTheDocument()
    expect(screen.queryByText('Julia01')).not.toBeInTheDocument()
  })
})

describe('OperationalStatus', () => {
  const mockData: OperationalStatusData = {
    rateLimitHour: { current: 15, max: 20, label: 'Mensagens/hora' },
    rateLimitDay: { current: 80, max: 100, label: 'Mensagens/dia' },
    queueSize: 5,
    llmUsage: { haiku: 80, sonnet: 20 },
    instances: [
      { name: 'Julia01', status: 'online', messagesToday: 50 },
      { name: 'Julia02', status: 'offline', messagesToday: 30 },
    ],
  }

  it('should render card title', () => {
    render(<OperationalStatus data={mockData} />)
    expect(screen.getByText('Status Operacional')).toBeInTheDocument()
  })

  it('should display queue size', () => {
    render(<OperationalStatus data={mockData} />)
    expect(screen.getByText(/Fila:/)).toBeInTheDocument()
    expect(screen.getByText('5 msgs')).toBeInTheDocument()
  })

  it('should display LLM usage', () => {
    render(<OperationalStatus data={mockData} />)
    // Check for LLM usage text (haiku/sonnet percentages)
    const llmText = screen.getByText(/Haiku/)
    expect(llmText).toBeInTheDocument()
    expect(screen.getByText(/Sonnet/)).toBeInTheDocument()
  })

  it('should render rate limit bars', () => {
    render(<OperationalStatus data={mockData} />)
    expect(screen.getByText('Mensagens/hora')).toBeInTheDocument()
    expect(screen.getByText('Mensagens/dia')).toBeInTheDocument()
  })

  it('should render instance list', () => {
    render(<OperationalStatus data={mockData} />)
    expect(screen.getByText('Instancias WhatsApp')).toBeInTheDocument()
    expect(screen.getByText('Julia01')).toBeInTheDocument()
    expect(screen.getByText('Julia02')).toBeInTheDocument()
  })
})
