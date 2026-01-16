"use client";

import { type ChipStatusCount, type ChipStatus } from "@/types/dashboard";

interface ChipStatusCountersProps {
  counts: ChipStatusCount[];
}

const statusConfig: Record<
  ChipStatus,
  { label: string; bgColor: string; textColor: string }
> = {
  active: { label: "Active", bgColor: "bg-green-100", textColor: "text-green-700" },
  ready: { label: "Ready", bgColor: "bg-blue-100", textColor: "text-blue-700" },
  warming: { label: "Warming", bgColor: "bg-yellow-100", textColor: "text-yellow-700" },
  degraded: { label: "Degraded", bgColor: "bg-orange-100", textColor: "text-orange-700" },
  banned: { label: "Banned", bgColor: "bg-red-100", textColor: "text-red-700" },
  provisioned: { label: "Provisioned", bgColor: "bg-gray-100", textColor: "text-gray-700" },
  pending: { label: "Pending", bgColor: "bg-gray-100", textColor: "text-gray-700" },
  paused: { label: "Paused", bgColor: "bg-gray-100", textColor: "text-gray-700" },
  cancelled: { label: "Cancelled", bgColor: "bg-gray-100", textColor: "text-gray-700" },
};

export function ChipStatusCounters({ counts }: ChipStatusCountersProps) {
  // Filtrar apenas status relevantes
  const relevantStatuses: ChipStatus[] = ["active", "ready", "warming", "degraded"];
  const filteredCounts = counts.filter((c) =>
    relevantStatuses.includes(c.status)
  );

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700">Status do Pool</h4>
      <div className="grid grid-cols-4 gap-2">
        {filteredCounts.map((item) => {
          const config = statusConfig[item.status];
          return (
            <div
              key={item.status}
              className={`${config.bgColor} rounded-lg p-3 text-center`}
            >
              <div className={`text-2xl font-bold ${config.textColor}`}>
                {item.count}
              </div>
              <div className={`text-xs ${config.textColor}`}>{config.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
