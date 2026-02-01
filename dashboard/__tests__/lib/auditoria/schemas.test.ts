/**
 * Testes para lib/auditoria/schemas.ts
 */

import { describe, it, expect } from 'vitest'
import {
  auditLogsQuerySchema,
  auditExportQuerySchema,
  parseAuditLogsQuery,
  parseAuditExportQuery,
} from '@/lib/auditoria/schemas'

// =============================================================================
// auditLogsQuerySchema
// =============================================================================

describe('auditLogsQuerySchema', () => {
  it('deve aceitar query vazia com defaults', () => {
    const result = auditLogsQuerySchema.parse({})
    expect(result.page).toBe(1)
    expect(result.per_page).toBe(50)
    expect(result.action).toBeUndefined()
  })

  it('deve aceitar page e per_page customizados', () => {
    const result = auditLogsQuerySchema.parse({ page: '3', per_page: '25' })
    expect(result.page).toBe(3)
    expect(result.per_page).toBe(25)
  })

  it('deve aceitar filtro de action', () => {
    const result = auditLogsQuerySchema.parse({ action: 'julia_toggle' })
    expect(result.action).toBe('julia_toggle')
  })

  it('deve aceitar filtro de actor_email', () => {
    const result = auditLogsQuerySchema.parse({ actor_email: 'user@example.com' })
    expect(result.actor_email).toBe('user@example.com')
  })

  it('deve aceitar filtro de from_date', () => {
    const result = auditLogsQuerySchema.parse({ from_date: '2024-01-15' })
    expect(result.from_date).toBe('2024-01-15')
  })

  it('deve aceitar filtro de to_date', () => {
    const result = auditLogsQuerySchema.parse({ to_date: '2024-01-20' })
    expect(result.to_date).toBe('2024-01-20')
  })

  it('deve rejeitar per_page maior que 100', () => {
    expect(() => auditLogsQuerySchema.parse({ per_page: '150' })).toThrow()
  })

  it('deve rejeitar page negativa', () => {
    expect(() => auditLogsQuerySchema.parse({ page: '-1' })).toThrow()
  })

  it('deve rejeitar from_date com formato invalido', () => {
    expect(() => auditLogsQuerySchema.parse({ from_date: '15-01-2024' })).toThrow()
  })

  it('deve rejeitar to_date com formato invalido', () => {
    expect(() => auditLogsQuerySchema.parse({ to_date: '2024/01/20' })).toThrow()
  })
})

// =============================================================================
// auditExportQuerySchema
// =============================================================================

describe('auditExportQuerySchema', () => {
  it('deve aceitar query vazia', () => {
    const result = auditExportQuerySchema.parse({})
    expect(result.action).toBeUndefined()
    expect(result.actor_email).toBeUndefined()
  })

  it('deve aceitar todos os filtros', () => {
    const result = auditExportQuerySchema.parse({
      action: 'manual_handoff',
      actor_email: 'admin@example.com',
      from_date: '2024-01-01',
      to_date: '2024-01-31',
    })

    expect(result.action).toBe('manual_handoff')
    expect(result.actor_email).toBe('admin@example.com')
    expect(result.from_date).toBe('2024-01-01')
    expect(result.to_date).toBe('2024-01-31')
  })

  it('deve rejeitar data com formato invalido', () => {
    expect(() => auditExportQuerySchema.parse({ from_date: 'invalid' })).toThrow()
  })

  it('deve rejeitar actor_email muito longo', () => {
    const longEmail = 'a'.repeat(256)
    expect(() => auditExportQuerySchema.parse({ actor_email: longEmail })).toThrow()
  })
})

// =============================================================================
// parseAuditLogsQuery
// =============================================================================

describe('parseAuditLogsQuery', () => {
  it('deve parsear query vazia', () => {
    const searchParams = new URLSearchParams()
    const result = parseAuditLogsQuery(searchParams)
    expect(result.page).toBe(1)
    expect(result.per_page).toBe(50)
  })

  it('deve parsear todos os parametros', () => {
    const searchParams = new URLSearchParams(
      'page=2&per_page=30&action=julia_pause&actor_email=test@test.com&from_date=2024-01-01&to_date=2024-01-31'
    )
    const result = parseAuditLogsQuery(searchParams)

    expect(result.page).toBe(2)
    expect(result.per_page).toBe(30)
    expect(result.action).toBe('julia_pause')
    expect(result.actor_email).toBe('test@test.com')
    expect(result.from_date).toBe('2024-01-01')
    expect(result.to_date).toBe('2024-01-31')
  })

  it('deve usar defaults para parametros faltando', () => {
    const searchParams = new URLSearchParams('action=circuit_reset')
    const result = parseAuditLogsQuery(searchParams)

    expect(result.page).toBe(1)
    expect(result.per_page).toBe(50)
    expect(result.action).toBe('circuit_reset')
  })
})

// =============================================================================
// parseAuditExportQuery
// =============================================================================

describe('parseAuditExportQuery', () => {
  it('deve parsear query vazia', () => {
    const searchParams = new URLSearchParams()
    const result = parseAuditExportQuery(searchParams)
    expect(result.action).toBeUndefined()
  })

  it('deve parsear todos os filtros', () => {
    const searchParams = new URLSearchParams(
      'action=create_campaign&actor_email=admin@example.com&from_date=2024-02-01&to_date=2024-02-28'
    )
    const result = parseAuditExportQuery(searchParams)

    expect(result.action).toBe('create_campaign')
    expect(result.actor_email).toBe('admin@example.com')
    expect(result.from_date).toBe('2024-02-01')
    expect(result.to_date).toBe('2024-02-28')
  })

  it('deve ignorar parametros nao definidos', () => {
    const searchParams = new URLSearchParams('action=start_campaign')
    const result = parseAuditExportQuery(searchParams)

    expect(result.action).toBe('start_campaign')
    expect(result.actor_email).toBeUndefined()
    expect(result.from_date).toBeUndefined()
  })
})
