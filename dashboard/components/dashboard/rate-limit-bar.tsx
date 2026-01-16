"use client";

import { type RateLimitData } from "@/types/dashboard";

interface RateLimitBarProps {
  data: RateLimitData;
}

function getProgressColor(percentage: number): string {
  if (percentage < 50) return "bg-green-500";
  if (percentage < 80) return "bg-yellow-500";
  return "bg-red-500";
}

export function RateLimitBar({ data }: RateLimitBarProps) {
  const { current, max, label } = data;
  const percentage = (current / max) * 100;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">
          {current}/{max}
        </span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full">
        <div
          className={`h-full rounded-full transition-all ${getProgressColor(
            percentage
          )}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}
