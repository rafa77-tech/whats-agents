"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ChipStatusCounters } from "./chip-status-counters";
import { ChipTrustDistribution } from "./chip-trust-distribution";
import { ChipPoolMetricsComponent } from "./chip-pool-metrics";
import { type ChipPoolOverviewData } from "@/types/dashboard";
import { Smartphone } from "lucide-react";

interface ChipPoolOverviewProps {
  data: ChipPoolOverviewData;
}

export function ChipPoolOverview({ data }: ChipPoolOverviewProps) {
  const { statusCounts, trustDistribution, metrics } = data;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
          <Smartphone className="h-4 w-4" />
          Pool de Chips
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Linha 1: Status + Trust */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChipStatusCounters counts={statusCounts} />
          <ChipTrustDistribution distribution={trustDistribution} />
        </div>

        {/* Linha 2: Metricas */}
        <div className="pt-4 border-t">
          <ChipPoolMetricsComponent metrics={metrics} />
        </div>
      </CardContent>
    </Card>
  );
}
