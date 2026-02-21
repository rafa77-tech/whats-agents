/**
 * Tests for FlowsTab component
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import FlowsTab from '@/components/meta/tabs/flows-tab'

describe('FlowsTab', () => {
  it('should render the flow builder placeholder', () => {
    render(<FlowsTab />)
    expect(screen.getByText('WhatsApp Flows')).toBeInTheDocument()
    expect(screen.getByText('Flow Builder')).toBeInTheDocument()
    expect(screen.getByText('Em breve')).toBeInTheDocument()
  })

  it('should list available flow types', () => {
    render(<FlowsTab />)
    expect(screen.getByText('Onboarding de medicos')).toBeInTheDocument()
    expect(screen.getByText('Confirmacao de plantao')).toBeInTheDocument()
    expect(screen.getByText('Avaliacao pos-plantao')).toBeInTheDocument()
  })
})
