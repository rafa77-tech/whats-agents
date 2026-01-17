"use client";

import { type ChipPoolAggregatedMetrics } from "@/types/dashboard";
import { TrendingUp, TrendingDown } from "lucide-react";

interface ChipPoolMetricsProps {
  metrics: ChipPoolAggregatedMetrics;
}

function MetricItem({
  label,
  value,
  previousValue,
  format,
  invertTrend = false,
}: {
  label: string;
  value: number;
  previousValue: number;
  format: "number" | "percent";
  invertTrend?: boolean;
}) {
  const diff =
    previousValue !== 0 ? ((value - previousValue) / previousValue) * 100 : 0;
  const isPositive = diff > 0;
  // Para taxa block e erros, queda e bom
  const isGood = invertTrend ? !isPositive : isPositive;

  const formattedValue =
    format === "percent"
      ? `${value.toFixed(1)}%`
      : value.toLocaleString("pt-BR");

  return (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <div className="text-lg font-bold text-gray-900">{formattedValue}</div>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      {Math.abs(diff) >= 1 && (
        <div
          className={`flex items-center justify-center text-xs ${
            isGood ? "text-green-600" : "text-red-600"
          }`}
        >
          {isPositive ? (
            <TrendingUp className="h-3 w-3 mr-0.5" />
          ) : (
            <TrendingDown className="h-3 w-3 mr-0.5" />
          )}
          {isPositive ? "+" : ""}
          {diff.toFixed(0)}%
        </div>
      )}
    </div>
  );
}

export function ChipPoolMetricsComponent({ metrics }: ChipPoolMetricsProps) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700">
        Metricas Agregadas (periodo)
      </h4>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricItem
          label="Msgs Enviadas"
          value={metrics.totalMessagesSent}
          previousValue={metrics.previousMessagesSent}
          format="number"
        />
        <MetricItem
          label="Taxa Resposta"
          value={metrics.avgResponseRate}
          previousValue={metrics.previousResponseRate}
          format="percent"
        />
        <MetricItem
          label="Taxa Block"
          value={metrics.avgBlockRate}
          previousValue={metrics.previousBlockRate}
          format="percent"
          invertTrend
        />
        <MetricItem
          label="Erros"
          value={metrics.totalErrors}
          previousValue={metrics.previousErrors}
          format="number"
          invertTrend
        />
      </div>
    </div>
  );
}
