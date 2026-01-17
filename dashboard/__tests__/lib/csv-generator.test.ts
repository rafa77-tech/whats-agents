/**
 * Tests for lib/dashboard/csv-generator.ts
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { generateDashboardCSV } from '@/lib/dashboard/csv-generator'
import { type DashboardExportData } from '@/types/dashboard'

describe('generateDashboardCSV', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2025-01-15T12:00:00'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  const mockData: DashboardExportData = {
    period: {
      start: '2025-01-08T00:00:00',
      end: '2025-01-15T00:00:00',
    },
    metrics: [
      {
        name: 'Taxa de Resposta',
        current: 35,
        previous: 30,
        meta: 30,
        unit: 'percent',
      },
      {
        name: 'Tempo Medio',
        current: 45,
        previous: 50,
        meta: 60,
        unit: 's',
      },
    ],
    quality: [
      {
        name: 'Naturalidade',
        current: 85,
        previous: 80,
        unit: '%',
        meta: '> 80%',
      },
    ],
    chips: [
      {
        name: 'Revoluna-01',
        status: 'active',
        trust: 85,
        messagesToday: 10,
        responseRate: 35.5,
        errors: 0,
      },
      {
        name: 'Revoluna-02',
        status: 'warming',
        trust: 70,
        messagesToday: 5,
        responseRate: 28.3,
        errors: 1,
      },
    ],
    funnel: [
      { stage: 'Enviadas', count: 100, percentage: 100, change: 10 },
      { stage: 'Entregues', count: 95, percentage: 95, change: 5 },
      { stage: 'Respostas', count: 35, percentage: 35, change: -2 },
    ],
  }

  it('should generate CSV with BOM for Excel compatibility', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv.startsWith('\uFEFF')).toBe(true)
  })

  it('should include report header', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('Relatorio Dashboard Julia')
  })

  it('should include period dates', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('Periodo:')
  })

  it('should include metrics section', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('METRICAS PRINCIPAIS')
    expect(csv).toContain('Taxa de Resposta')
    expect(csv).toContain('35.0%')
  })

  it('should include quality section', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('QUALIDADE DA PERSONA')
    expect(csv).toContain('Naturalidade')
  })

  it('should include chips section', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('POOL DE CHIPS')
    expect(csv).toContain('Revoluna-01')
    expect(csv).toContain('Revoluna-02')
  })

  it('should include funnel section', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('FUNIL DE CONVERSAO')
    expect(csv).toContain('Enviadas')
    expect(csv).toContain('Entregues')
    expect(csv).toContain('Respostas')
  })

  it('should format positive change with + prefix', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('+10%')
  })

  it('should format negative change', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('-2%')
  })

  it('should calculate and show status for metrics', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('Atingida') // 35 >= 30
    expect(csv).toContain('Abaixo') // 45 < 60
  })

  it('should format currency values', () => {
    const dataWithCurrency: DashboardExportData = {
      ...mockData,
      metrics: [
        {
          name: 'Custo',
          current: 1500.5,
          previous: 1400,
          meta: 2000,
          unit: 'currency',
        },
      ],
    }
    const csv = generateDashboardCSV(dataWithCurrency)
    expect(csv).toContain('R$ 1500.50')
  })

  it('should escape CSV special characters', () => {
    const dataWithComma: DashboardExportData = {
      ...mockData,
      metrics: [
        {
          name: 'Taxa, teste',
          current: 50,
          previous: 40,
          meta: 45,
          unit: 'percent',
        },
      ],
    }
    const csv = generateDashboardCSV(dataWithComma)
    expect(csv).toContain('"Taxa, teste"')
  })

  it('should handle quotes in values', () => {
    const dataWithQuotes: DashboardExportData = {
      ...mockData,
      quality: [
        {
          name: 'Test "quoted"',
          current: 90,
          previous: 85,
          unit: '%',
          meta: '> 80%',
        },
      ],
    }
    const csv = generateDashboardCSV(dataWithQuotes)
    expect(csv).toContain('"Test ""quoted"""')
  })

  it('should handle zero previous value (N/A change)', () => {
    const dataWithZero: DashboardExportData = {
      ...mockData,
      metrics: [
        {
          name: 'Nova Metrica',
          current: 50,
          previous: 0,
          meta: 45,
          unit: 'percent',
        },
      ],
    }
    const csv = generateDashboardCSV(dataWithZero)
    expect(csv).toContain('N/A')
  })

  it('should include all required columns in metrics header', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('Metrica,Valor Atual,Valor Anterior,Variacao,Meta,Status')
  })

  it('should include all required columns in chips header', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('Chip,Status,Trust,Msgs Hoje,Taxa Resp,Erros 24h')
  })

  it('should include all required columns in funnel header', () => {
    const csv = generateDashboardCSV(mockData)
    expect(csv).toContain('Etapa,Quantidade,Porcentagem,Variacao')
  })
})
