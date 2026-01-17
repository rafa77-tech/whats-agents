/**
 * Sparkline Chart Component - Sprint 33 E12
 *
 * Compact line chart showing metric trends over time.
 */

"use client";

import { LineChart, Line, ResponsiveContainer } from "recharts";
import { type SparklineMetric } from "@/types/dashboard";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SparklineChartProps {
  metric: SparklineMetric;
}

export function SparklineChart({ metric }: SparklineChartProps) {
  const { label, data, currentValue, unit, trend, trendIsGood } = metric;

  // Determinar cor da linha baseado na tendencia
  const lineColor =
    trend === "stable"
      ? "#9CA3AF" // gray
      : trendIsGood
        ? "#10B981" // green
        : "#EF4444"; // red

  // Icone de tendencia
  const TrendIcon =
    trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;

  // Formatar valor
  const formattedValue =
    unit === "%"
      ? `${currentValue.toFixed(1)}%`
      : unit === "s"
        ? `${currentValue.toFixed(0)}s`
        : unit === "$"
          ? `$${currentValue.toFixed(2)}`
          : currentValue.toFixed(0);

  return (
    <div className="flex items-center gap-4 py-2">
      <div className="w-32 text-sm text-gray-600">{label}</div>

      <div className="flex-1 h-8 min-w-[100px]">
        <ResponsiveContainer width="100%" height={32} minWidth={100}>
          <LineChart data={data}>
            <Line
              type="monotone"
              dataKey="value"
              stroke={lineColor}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-2 w-20 justify-end">
        <span className="font-medium">{formattedValue}</span>
        <TrendIcon
          className={`h-4 w-4 ${
            trend === "stable"
              ? "text-gray-400"
              : trendIsGood
                ? "text-green-500"
                : "text-red-500"
          }`}
        />
      </div>
    </div>
  );
}
