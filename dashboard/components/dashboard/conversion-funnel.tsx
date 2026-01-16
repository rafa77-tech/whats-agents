/**
 * Conversion Funnel Component - Sprint 33 E10
 *
 * Visual funnel showing the conversion pipeline:
 * Enviadas -> Entregues -> Respostas -> Interesse -> Fechadas
 */

"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FunnelStageComponent } from "./funnel-stage";
import { type FunnelDataVisual } from "@/types/dashboard";
import { Filter } from "lucide-react";

interface ConversionFunnelProps {
  data: FunnelDataVisual;
  onStageClick: (stageId: string) => void;
}

export function ConversionFunnel({
  data,
  onStageClick,
}: ConversionFunnelProps) {
  const { stages, period } = data;
  const maxCount = stages[0]?.count || 1;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Funil de Conversao
          </CardTitle>
          <span className="text-sm text-gray-400">Periodo: {period}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 py-4">
        {stages.map((stage, index) => (
          <FunnelStageComponent
            key={stage.id}
            stage={stage}
            maxCount={maxCount}
            onClick={() => onStageClick(stage.id)}
            isFirst={index === 0}
          />
        ))}
      </CardContent>
    </Card>
  );
}
