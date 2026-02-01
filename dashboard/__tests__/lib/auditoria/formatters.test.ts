/**
 * Testes para lib/auditoria/formatters.ts
 */

import { describe, it, expect } from 'vitest'
import {
  formatAuditDate,
  formatAuditDateFull,
  formatDateForFilename,
  getActionIcon,
  getActionLabel,
  escapeCsvField,
  formatDetailsForCsv,
  buildAuditLogsUrl,
  buildExportUrl,
} from '@/lib/auditoria/formatters'
import { Settings, Power, Flag } from 'lucide-react'

// =============================================================================
// Formatadores de data
// =============================================================================

describe('formatAuditDate', () => {
  it('deve formatar data corretamente', () => {
    const result = formatAuditDate('2024-01-15T14:30:00Z')
    expect(result).toMatch(/\d{2}\/\d{2} \d{2}:\d{2}/)
  })

  it('deve retornar string original em caso de erro', () => {
    const result = formatAuditDate('invalid-date')
    expect(result).toBe('invalid-date')
  })
})

describe('formatAuditDateFull', () => {
  it('deve formatar data completa corretamente', () => {
    const result = formatAuditDateFull('2024-01-15T14:30:00Z')
    expect(result).toMatch(/\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2}/)
  })

  it('deve retornar string original em caso de erro', () => {
    const result = formatAuditDateFull('invalid')
    expect(result).toBe('invalid')
  })
})

describe('formatDateForFilename', () => {
  it('deve formatar data para nome de arquivo', () => {
    const date = new Date('2024-01-15T10:00:00Z')
    const result = formatDateForFilename(date)
    expect(result).toBe('2024-01-15')
  })

  it('deve usar data atual se nao fornecida', () => {
    const result = formatDateForFilename()
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})

// =============================================================================
// Formatadores de acao
// =============================================================================

describe('getActionIcon', () => {
  it('deve retornar icone correto para julia_toggle', () => {
    const icon = getActionIcon('julia_toggle')
    expect(icon).toBe(Power)
  })

  it('deve retornar icone correto para feature_flag_update', () => {
    const icon = getActionIcon('feature_flag_update')
    expect(icon).toBe(Flag)
  })

  it('deve retornar Settings para acao desconhecida', () => {
    const icon = getActionIcon('unknown_action')
    expect(icon).toBe(Settings)
  })
})

describe('getActionLabel', () => {
  it('deve retornar label correto para julia_toggle', () => {
    const label = getActionLabel('julia_toggle')
    expect(label).toBe('Toggle Julia')
  })

  it('deve retornar label correto para manual_handoff', () => {
    const label = getActionLabel('manual_handoff')
    expect(label).toBe('Handoff Manual')
  })

  it('deve retornar a propria acao se label nao existe', () => {
    const label = getActionLabel('custom_action')
    expect(label).toBe('custom_action')
  })
})

// =============================================================================
// Formatadores de CSV
// =============================================================================

describe('escapeCsvField', () => {
  it('deve retornar string simples sem alteracao', () => {
    const result = escapeCsvField('simple text')
    expect(result).toBe('simple text')
  })

  it('deve escapar string com virgula', () => {
    const result = escapeCsvField('text, with comma')
    expect(result).toBe('"text, with comma"')
  })

  it('deve escapar string com aspas', () => {
    const result = escapeCsvField('text with "quotes"')
    expect(result).toBe('"text with ""quotes"""')
  })

  it('deve escapar string com quebra de linha', () => {
    const result = escapeCsvField('text\nwith newline')
    expect(result).toBe('"text\nwith newline"')
  })
})

describe('formatDetailsForCsv', () => {
  it('deve formatar objeto simples', () => {
    const result = formatDetailsForCsv({ key: 'value' })
    expect(result).toContain('key')
    expect(result).toContain('value')
  })

  it('deve escapar caracteres especiais', () => {
    const result = formatDetailsForCsv({ text: 'value, with comma' })
    expect(result.startsWith('"')).toBe(true)
    expect(result.endsWith('"')).toBe(true)
  })
})

// =============================================================================
// Builders de URL
// =============================================================================

describe('buildAuditLogsUrl', () => {
  it('deve construir URL com paginacao', () => {
    const url = buildAuditLogsUrl('/api/auditoria', 1, 50, {})
    expect(url).toBe('/api/auditoria?page=1&per_page=50')
  })

  it('deve incluir filtros na URL', () => {
    const url = buildAuditLogsUrl('/api/auditoria', 2, 25, {
      action: 'julia_toggle',
      actor_email: 'admin@test.com',
    })

    expect(url).toContain('page=2')
    expect(url).toContain('per_page=25')
    expect(url).toContain('action=julia_toggle')
    expect(url).toContain('actor_email=admin%40test.com')
  })

  it('deve incluir filtros de data', () => {
    const url = buildAuditLogsUrl('/api/auditoria', 1, 50, {
      from_date: '2024-01-01',
      to_date: '2024-01-31',
    })

    expect(url).toContain('from_date=2024-01-01')
    expect(url).toContain('to_date=2024-01-31')
  })

  it('deve ignorar filtros undefined', () => {
    const url = buildAuditLogsUrl('/api/auditoria', 1, 50, {
      action: undefined,
      actor_email: 'test@test.com',
    })

    expect(url).not.toContain('action=')
    expect(url).toContain('actor_email=')
  })
})

describe('buildExportUrl', () => {
  it('deve construir URL sem filtros', () => {
    const url = buildExportUrl('/api/auditoria/export', {})
    expect(url).toBe('/api/auditoria/export')
  })

  it('deve incluir filtros na URL', () => {
    const url = buildExportUrl('/api/auditoria/export', {
      action: 'create_campaign',
      from_date: '2024-01-01',
    })

    expect(url).toContain('action=create_campaign')
    expect(url).toContain('from_date=2024-01-01')
  })

  it('deve ignorar filtros undefined', () => {
    const url = buildExportUrl('/api/auditoria/export', {
      action: 'pause_campaign',
      actor_email: undefined,
    })

    expect(url).toContain('action=pause_campaign')
    expect(url).not.toContain('actor_email')
  })
})
