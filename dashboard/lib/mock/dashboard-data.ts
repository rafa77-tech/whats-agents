/**
 * Mock data for dashboard components
 * Sprint 33 - Dashboard Performance Julia
 *
 * This file contains mock data used during development.
 * Will be replaced by real API calls in E08.
 */

import { type MetricData, type QualityMetricData } from "@/types/dashboard";

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

// ============================================================================
// E04 - Quality Metrics
// ============================================================================

export const mockQualityMetrics: QualityMetricData[] = [
  {
    label: "Deteccao como Bot",
    value: 0.4,
    unit: "percent",
    threshold: { good: 1, warning: 3 },
    operator: "lt",
    previousValue: 0.6,
    tooltip:
      "Porcentagem de conversas onde o medico detectou que estava falando com um bot",
  },
  {
    label: "Latencia Media",
    value: 24,
    unit: "seconds",
    threshold: { good: 30, warning: 60 },
    operator: "lt",
    previousValue: 28,
    tooltip: "Tempo medio que Julia leva para responder uma mensagem",
  },
  {
    label: "Taxa de Handoff",
    value: 3.2,
    unit: "percent",
    threshold: { good: 5, warning: 10 },
    operator: "lt",
    previousValue: 4.1,
    tooltip: "Porcentagem de conversas transferidas para atendimento humano",
  },
];
