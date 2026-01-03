import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatusCardProps {
  title: string;
  value: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    positive: boolean;
  };
}

export function StatusCard({ title, value, icon: Icon, trend }: StatusCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 lg:p-6">
      <div className="flex items-start justify-between">
        <div className="p-2 bg-revoluna-50 rounded-lg">
          <Icon className="w-5 h-5 text-revoluna-400" />
        </div>
        {trend && (
          <div className={cn(
            "flex items-center gap-1 text-sm font-medium",
            trend.positive ? "text-green-600" : "text-red-600"
          )}>
            {trend.positive ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            {trend.value}%
          </div>
        )}
      </div>
      <div className="mt-4">
        <p className="text-2xl lg:text-3xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500 mt-1">{title}</p>
      </div>
    </div>
  );
}
