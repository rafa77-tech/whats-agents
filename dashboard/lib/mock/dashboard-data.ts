/**
 * Mock data for dashboard components
 * Sprint 33 - Dashboard Performance Julia
 *
 * This file contains mock data used during development.
 * Will be replaced by real API calls in E08.
 */

import { type MetricData } from "@/types/dashboard";

// ============================================================================
// E03 - Metrics vs Meta
// ============================================================================

export const mockMetricsVsMeta: MetricData[] = [
  {
    label: "Taxa de Resposta",
    value: 32,
    unit: "percent",
    meta: 30,
    previousValue: 28,
    metaOperator: "gt",
  },
  {
    label: "Taxa de Conversao",
    value: 18,
    unit: "percent",
    meta: 25,
    previousValue: 20,
    metaOperator: "gt",
  },
  {
    label: "Fechamentos/Semana",
    value: 18,
    unit: "number",
    meta: 15,
    previousValue: 15,
    metaOperator: "gt",
  },
];
