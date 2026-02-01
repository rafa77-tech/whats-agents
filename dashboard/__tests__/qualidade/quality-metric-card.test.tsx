/**
 * Testes para o componente QualityMetricCard
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CheckCircle2, Star, ClipboardList } from 'lucide-react'
import { QualityMetricCard } from '@/components/qualidade/quality-metric-card'

describe('QualityMetricCard', () => {
  it('deve renderizar titulo e valor', () => {
    render(
      <QualityMetricCard title="Avaliadas" value={10} icon={CheckCircle2} color="green" />
    )

    expect(screen.getByText('Avaliadas')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
  })

  it('deve renderizar com suffix', () => {
    render(
      <QualityMetricCard title="Score Medio" value={4.5} suffix="/5" icon={Star} color="blue" />
    )

    expect(screen.getByText('Score Medio')).toBeInTheDocument()
    expect(screen.getByText('4.5')).toBeInTheDocument()
    expect(screen.getByText('/5')).toBeInTheDocument()
  })

  it('deve aplicar classes de cor verde', () => {
    const { container } = render(
      <QualityMetricCard title="Test" value={0} icon={CheckCircle2} color="green" />
    )

    const cardContent = container.querySelector('.bg-green-50')
    expect(cardContent).toBeInTheDocument()
  })

  it('deve aplicar classes de cor amarela', () => {
    const { container } = render(
      <QualityMetricCard title="Test" value={0} icon={ClipboardList} color="yellow" />
    )

    const cardContent = container.querySelector('.bg-yellow-50')
    expect(cardContent).toBeInTheDocument()
  })

  it('deve aplicar classes de cor azul', () => {
    const { container } = render(
      <QualityMetricCard title="Test" value={0} icon={Star} color="blue" />
    )

    const cardContent = container.querySelector('.bg-blue-50')
    expect(cardContent).toBeInTheDocument()
  })

  it('deve aplicar classes de cor vermelha', () => {
    const { container } = render(
      <QualityMetricCard title="Test" value={0} icon={CheckCircle2} color="red" />
    )

    const cardContent = container.querySelector('.bg-red-50')
    expect(cardContent).toBeInTheDocument()
  })

  it('deve renderizar o icone', () => {
    const { container } = render(
      <QualityMetricCard title="Test" value={0} icon={Star} color="blue" />
    )

    const icon = container.querySelector('svg')
    expect(icon).toBeInTheDocument()
    expect(icon).toHaveClass('h-8', 'w-8')
  })

  it('deve renderizar valor zero corretamente', () => {
    render(<QualityMetricCard title="Pendentes" value={0} icon={ClipboardList} color="yellow" />)

    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('deve renderizar valores decimais', () => {
    render(
      <QualityMetricCard title="Score" value={4.75} suffix="/5" icon={Star} color="blue" />
    )

    expect(screen.getByText('4.75')).toBeInTheDocument()
  })
})
