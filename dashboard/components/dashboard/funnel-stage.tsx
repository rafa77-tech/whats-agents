/**
 * Funnel Stage Component - Sprint 33 E10
 *
 * Individual stage bar for the conversion funnel visualization.
 */

"use client";

import { type FunnelStageVisual } from "@/types/dashboard";
import { TrendingUp, TrendingDown } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface FunnelStageProps {
  stage: FunnelStageVisual;
  maxCount: number; // para calcular largura relativa
  onClick: () => void;
  isFirst: boolean;
}

const stageColors: Record<string, { bg: string; border: string; text: string }> =
  {
    enviadas: {
      bg: "bg-blue-100",
      border: "border-blue-300",
      text: "text-blue-700",
    },
    entregues: {
      bg: "bg-blue-100",
      border: "border-blue-300",
      text: "text-blue-700",
    },
    respostas: {
      bg: "bg-green-100",
      border: "border-green-300",
      text: "text-green-700",
    },
    interesse: {
      bg: "bg-yellow-100",
      border: "border-yellow-300",
      text: "text-yellow-700",
    },
    fechadas: {
      bg: "bg-emerald-100",
      border: "border-emerald-300",
      text: "text-emerald-700",
    },
  };

export function FunnelStageComponent({
  stage,
  maxCount,
  onClick,
  isFirst,
}: FunnelStageProps) {
  const { id, label, count, previousCount, percentage } = stage;

  // Calcular largura proporcional (minimo 30% para legibilidade)
  const widthPercent = Math.max(30, (count / maxCount) * 100);

  // Calcular variacao
  const diff =
    previousCount > 0 ? ((count - previousCount) / previousCount) * 100 : 0;
  const isPositive = diff > 0;

  const colors = stageColors[id] ?? {
    bg: "bg-blue-100",
    border: "border-blue-300",
    text: "text-blue-700",
  };

  const paddingValue = isFirst ? 0 : (100 - widthPercent) / 2;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className="flex justify-center cursor-pointer transition-transform hover:scale-[1.02]"
            onClick={onClick}
            style={{
              paddingLeft: `${paddingValue}%`,
              paddingRight: `${paddingValue}%`,
            }}
          >
            <div
              className={`
                w-full py-3 px-4 rounded-lg border-2
                ${colors.bg} ${colors.border}
                flex items-center justify-between
              `}
            >
              <div className="flex items-center gap-2">
                <span className={`font-medium ${colors.text}`}>{label}:</span>
                <span className="font-bold text-gray-900">
                  {count.toLocaleString("pt-BR")}
                </span>
                <span className="text-gray-500 text-sm">
                  ({percentage.toFixed(1)}%)
                </span>
              </div>

              {Math.abs(diff) >= 1 && (
                <div
                  className={`flex items-center text-sm ${
                    isPositive ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {isPositive ? (
                    <TrendingUp className="h-4 w-4 mr-1" />
                  ) : (
                    <TrendingDown className="h-4 w-4 mr-1" />
                  )}
                  {isPositive ? "+" : ""}
                  {diff.toFixed(0)}%
                </div>
              )}
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>Clique para ver detalhes de {label.toLowerCase()}</p>
          <p className="text-xs text-gray-400">
            Periodo anterior: {previousCount.toLocaleString("pt-BR")}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
