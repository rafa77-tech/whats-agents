"use client";

import { type TrustDistribution, type TrustLevel } from "@/types/dashboard";

interface ChipTrustDistributionProps {
  distribution: TrustDistribution[];
}

const trustConfig: Record<
  TrustLevel,
  { label: string; range: string; color: string }
> = {
  verde: { label: "Verde", range: "75+", color: "bg-green-500" },
  amarelo: { label: "Amarelo", range: "50-74", color: "bg-yellow-500" },
  laranja: { label: "Laranja", range: "35-49", color: "bg-orange-500" },
  vermelho: { label: "Vermelho", range: "<35", color: "bg-red-500" },
};

export function ChipTrustDistribution({
  distribution,
}: ChipTrustDistributionProps) {
  const maxCount = Math.max(...distribution.map((d) => d.count), 1);

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700">Trust Level</h4>
      <div className="space-y-2">
        {distribution.map((item) => {
          const config = trustConfig[item.level];
          const barWidth = (item.count / maxCount) * 100;

          return (
            <div key={item.level} className="flex items-center gap-3">
              <div className="w-24 text-sm text-gray-600">
                {config.label} ({config.range})
              </div>
              <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${config.color} rounded-full transition-all`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
              <div className="w-8 text-sm font-medium text-right">
                {item.count}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
