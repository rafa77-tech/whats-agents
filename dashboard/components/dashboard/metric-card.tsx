"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Check,
  AlertTriangle,
  X,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import { type MetricData, type MetricUnit, type MetaOperator } from "@/types/dashboard";

interface MetricCardProps {
  data: MetricData;
}

function formatValue(value: number, unit: MetricUnit): string {
  switch (unit) {
    case "percent":
      return `${value.toFixed(1)}%`;
    case "currency":
      return `R$ ${value.toLocaleString("pt-BR")}`;
    case "number":
    default:
      return value.toLocaleString("pt-BR");
  }
}

function getMetaStatus(
  value: number,
  meta: number,
  operator: MetaOperator
): "success" | "warning" | "error" {
  const meetsTarget =
    operator === "gt"
      ? value >= meta
      : operator === "lt"
        ? value <= meta
        : value === meta;

  if (meetsTarget) return "success";

  const diff = Math.abs((value - meta) / meta);
  return diff < 0.2 ? "warning" : "error";
}

function MetaIndicator({ status }: { status: "success" | "warning" | "error" }) {
  if (status === "success") {
    return (
      <Badge className="bg-green-100 text-green-700 border-green-200">
        <Check className="h-3 w-3 mr-1" />
        Meta
      </Badge>
    );
  }
  if (status === "warning") {
    return (
      <Badge className="bg-yellow-100 text-yellow-700 border-yellow-200">
        <AlertTriangle className="h-3 w-3 mr-1" />
        Atencao
      </Badge>
    );
  }
  return (
    <Badge className="bg-red-100 text-red-700 border-red-200">
      <X className="h-3 w-3 mr-1" />
      Abaixo
    </Badge>
  );
}

function ComparisonBadge({
  current,
  previous,
}: {
  current: number;
  previous: number;
}) {
  if (previous === 0) return null;

  const diff = ((current - previous) / previous) * 100;
  const isPositive = diff > 0;
  const isNeutral = Math.abs(diff) < 1;

  if (isNeutral) {
    return (
      <span className="flex items-center text-gray-500 text-sm">
        <Minus className="h-3 w-3 mr-1" />
        Estavel
      </span>
    );
  }

  return (
    <span
      className={`flex items-center text-sm ${
        isPositive ? "text-green-600" : "text-red-600"
      }`}
    >
      {isPositive ? (
        <TrendingUp className="h-3 w-3 mr-1" />
      ) : (
        <TrendingDown className="h-3 w-3 mr-1" />
      )}
      {isPositive ? "+" : ""}
      {diff.toFixed(0)}%
    </span>
  );
}

export function MetricCard({ data }: MetricCardProps) {
  const { label, value, unit, meta, previousValue, metaOperator } = data;
  const status = getMetaStatus(value, meta, metaOperator);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-500">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end justify-between">
          <div>
            <div className="text-3xl font-bold">{formatValue(value, unit)}</div>
            <div className="text-sm text-gray-500 mt-1">
              Meta: {formatValue(meta, unit)}
            </div>
          </div>
          <MetaIndicator status={status} />
        </div>

        <div className="mt-4 pt-4 border-t flex items-center justify-between">
          <span className="text-sm text-gray-500">
            vs sem. ant: {formatValue(previousValue, unit)}
          </span>
          <ComparisonBadge current={value} previous={previousValue} />
        </div>
      </CardContent>
    </Card>
  );
}
