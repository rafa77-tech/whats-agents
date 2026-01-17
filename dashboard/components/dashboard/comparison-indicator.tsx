/**
 * Comparison Indicator Component - Sprint 33 E15
 *
 * Reusable component showing trend with color-coded icon and percentage.
 * Green for positive trends, red for negative, gray for neutral.
 */

"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  calculatePercentageChange,
  getTrendStatus,
  formatChange,
} from "@/lib/dashboard/calculations";

interface ComparisonIndicatorProps {
  current: number;
  previous: number;
  lesserIsBetter?: boolean;
  showValue?: boolean;
  size?: "sm" | "md";
}

export function ComparisonIndicator({
  current,
  previous,
  lesserIsBetter = false,
  showValue = true,
  size = "md",
}: ComparisonIndicatorProps) {
  const change = calculatePercentageChange(current, previous);
  const status = getTrendStatus(change, lesserIsBetter);

  const iconSize = size === "sm" ? "h-3 w-3" : "h-4 w-4";
  const textSize = size === "sm" ? "text-xs" : "text-sm";

  // Determine which icon to show based on the change direction
  const getIcon = () => {
    if (status === "neutral" || change === null) return Minus;
    return change > 0 ? TrendingUp : TrendingDown;
  };

  const statusConfig = {
    positive: {
      color: "text-green-600",
    },
    negative: {
      color: "text-red-600",
    },
    neutral: {
      color: "text-gray-400",
    },
  };

  const config = statusConfig[status];
  const Icon = getIcon();

  if (change === null) {
    return null;
  }

  return (
    <span className={`flex items-center gap-1 ${config.color} ${textSize}`}>
      <Icon className={iconSize} />
      {showValue && formatChange(change)}
    </span>
  );
}
