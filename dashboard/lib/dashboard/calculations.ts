/**
 * Dashboard Calculations - Sprint 33 E08
 *
 * Funcoes auxiliares para calculos de datas e metricas do dashboard.
 */

import { type DashboardPeriod } from "@/types/dashboard";

export interface PeriodDates {
  currentStart: string;
  currentEnd: string;
  previousStart: string;
  previousEnd: string;
  days: number;
}

/**
 * Calcula as datas do periodo atual e anterior baseado no periodo selecionado.
 *
 * @param period - Periodo selecionado ("7d" | "14d" | "30d")
 * @returns Objeto com datas ISO para periodo atual e anterior
 */
export function getPeriodDates(period: DashboardPeriod | string): PeriodDates {
  const periodMap: Record<string, number> = {
    "7d": 7,
    "14d": 14,
    "30d": 30,
  };

  const days = periodMap[period] || 7;
  const now = new Date();

  // Periodo atual: agora ate X dias atras
  const currentEnd = now.toISOString();
  const currentStart = new Date(now);
  currentStart.setDate(currentStart.getDate() - days);

  // Periodo anterior: X dias atras ate 2X dias atras
  const previousEnd = currentStart.toISOString();
  const previousStart = new Date(currentStart);
  previousStart.setDate(previousStart.getDate() - days);

  return {
    currentStart: currentStart.toISOString(),
    currentEnd,
    previousStart: previousStart.toISOString(),
    previousEnd,
    days,
  };
}

/**
 * Calcula a variacao percentual entre dois valores.
 *
 * @param current - Valor atual
 * @param previous - Valor anterior
 * @returns Variacao percentual (positivo = aumento, negativo = queda)
 */
export function calculatePercentChange(
  current: number,
  previous: number
): number {
  if (previous === 0) {
    return current > 0 ? 100 : 0;
  }
  return Number((((current - previous) / previous) * 100).toFixed(1));
}

/**
 * Calcula a taxa como porcentagem (evita divisao por zero).
 *
 * @param numerator - Numerador
 * @param denominator - Denominador
 * @returns Taxa em porcentagem (0-100)
 */
export function calculateRate(numerator: number, denominator: number): number {
  if (denominator === 0) return 0;
  return Number(((numerator / denominator) * 100).toFixed(1));
}

/**
 * Arredonda um numero para N casas decimais.
 *
 * @param value - Valor a ser arredondado
 * @param decimals - Numero de casas decimais (default: 1)
 * @returns Valor arredondado
 */
export function roundTo(value: number, decimals: number = 1): number {
  const multiplier = Math.pow(10, decimals);
  return Math.round(value * multiplier) / multiplier;
}

/**
 * Valida e retorna o periodo ou o default.
 *
 * @param period - Periodo a validar
 * @returns Periodo valido
 */
export function validatePeriod(period: string | null): DashboardPeriod {
  const validPeriods = ["7d", "14d", "30d"];
  if (period && validPeriods.includes(period)) {
    return period as DashboardPeriod;
  }
  return "7d";
}
