/**
 * Cron Calculator Utility - Sprint 42
 *
 * Calcula proxima execucao baseada em expressoes cron.
 */

import { CronExpressionParser } from 'cron-parser'

/**
 * Calcula a proxima execucao baseada em uma expressao cron.
 *
 * @param cronExpression - Expressao cron (5 campos: min hour day month weekday)
 * @param currentDate - Data base para calculo (default: now)
 * @returns ISO string da proxima execucao, ou null se invalido
 */
export function calculateNextRun(cronExpression: string, currentDate?: Date): string | null {
  try {
    const expression = CronExpressionParser.parse(cronExpression, {
      currentDate: currentDate || new Date(),
      tz: 'America/Sao_Paulo',
    })
    return expression.next().toDate().toISOString()
  } catch {
    return null
  }
}

/**
 * Valida se uma expressao cron e valida.
 *
 * @param cronExpression - Expressao cron a validar
 * @returns true se valida, false caso contrario
 */
export function isValidCronExpression(cronExpression: string): boolean {
  try {
    CronExpressionParser.parse(cronExpression)
    return true
  } catch {
    return false
  }
}

/**
 * Retorna descricao humanizada de uma expressao cron.
 *
 * @param cronExpression - Expressao cron
 * @returns Descricao em portugues
 */
export function getCronDescription(cronExpression: string): string {
  const parts = cronExpression.split(' ')
  if (parts.length !== 5) return 'Expressão inválida'

  const minute = parts[0] ?? ''
  const hour = parts[1] ?? ''
  const dayOfMonth = parts[2] ?? ''
  const dayOfWeek = parts[4] ?? ''

  // Helper para formatar dias da semana
  const formatDayOfWeek = (d: string): string => {
    const dayNames: Record<string, string> = {
      '0': 'domingo',
      '1': 'segunda',
      '2': 'terça',
      '3': 'quarta',
      '4': 'quinta',
      '5': 'sexta',
      '6': 'sábado',
    }
    if (d === '1-5') return 'dias úteis'
    if (d === '0,6') return 'fins de semana'
    return dayNames[d] || d
  }

  // A cada minuto
  if (cronExpression === '* * * * *') return 'A cada minuto'

  // A cada X minutos
  if (minute.startsWith('*/')) {
    const interval = minute.replace('*/', '')
    let desc = `A cada ${interval} min`

    // Com restrição de horário
    if (hour !== '*' && hour.includes('-')) {
      const [start, end] = hour.split('-')
      desc += ` (${start}h-${end}h)`
    }

    // Com restrição de dias
    if (dayOfWeek !== '*') {
      desc += `, ${formatDayOfWeek(dayOfWeek)}`
    }

    return desc
  }

  // A cada hora
  if (minute === '0' && hour === '*') return 'A cada hora'

  // Horário específico
  if (minute !== '*' && hour !== '*') {
    // Múltiplos horários no mesmo dia
    if (hour.includes(',')) {
      const hours = hour.split(',').map((h) => `${h}h`)
      const timeStr = hours.join(' e ')

      if (dayOfMonth === '*' && dayOfWeek === '*') {
        return `Diário às ${timeStr}`
      }
      if (dayOfWeek === '1-5') {
        return `Dias úteis às ${timeStr}`
      }
      return `${formatDayOfWeek(dayOfWeek)} às ${timeStr}`
    }

    const time = `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`

    // Diário
    if (dayOfMonth === '*' && dayOfWeek === '*') {
      return `Diário às ${time}`
    }

    // Dias da semana específicos
    if (dayOfMonth === '*' && dayOfWeek !== '*') {
      if (dayOfWeek === '1-5') {
        return `Dias úteis às ${time}`
      }
      if (dayOfWeek === '1') {
        return `Segundas às ${time}`
      }
      if (dayOfWeek === '0') {
        return `Domingos às ${time}`
      }
      return `${formatDayOfWeek(dayOfWeek)} às ${time}`
    }
  }

  // Fallback para expressão original
  return cronExpression
}
