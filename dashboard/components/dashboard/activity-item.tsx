/**
 * Activity Item Component - Sprint 33 E14
 *
 * Individual activity event in the feed timeline.
 */

"use client";

import { type ActivityEvent, type ActivityType } from "@/types/dashboard";
import {
  CheckCircle,
  RefreshCw,
  Send,
  MessageSquare,
  Award,
  AlertTriangle,
  type LucideIcon,
} from "lucide-react";
import { format } from "date-fns";

interface ActivityItemProps {
  event: ActivityEvent;
}

const typeConfig: Record<
  ActivityType,
  {
    icon: LucideIcon;
    bgColor: string;
    iconColor: string;
  }
> = {
  fechamento: {
    icon: CheckCircle,
    bgColor: "bg-green-100",
    iconColor: "text-green-600",
  },
  handoff: {
    icon: RefreshCw,
    bgColor: "bg-blue-100",
    iconColor: "text-blue-600",
  },
  campanha: {
    icon: Send,
    bgColor: "bg-purple-100",
    iconColor: "text-purple-600",
  },
  resposta: {
    icon: MessageSquare,
    bgColor: "bg-green-100",
    iconColor: "text-green-600",
  },
  chip: {
    icon: Award,
    bgColor: "bg-yellow-100",
    iconColor: "text-yellow-600",
  },
  alerta: {
    icon: AlertTriangle,
    bgColor: "bg-orange-100",
    iconColor: "text-orange-600",
  },
};

export function ActivityItem({ event }: ActivityItemProps) {
  const { type, message, chipName, timestamp } = event;
  const config = typeConfig[type];
  const Icon = config.icon;

  const time = format(new Date(timestamp), "HH:mm");

  return (
    <div className="flex items-start gap-3 py-2">
      {/* Timestamp */}
      <span className="text-xs text-gray-400 w-12 pt-0.5">{time}</span>

      {/* Icon */}
      <div className={`p-1.5 rounded-full ${config.bgColor}`}>
        <Icon className={`h-3.5 w-3.5 ${config.iconColor}`} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-700">
          {chipName && (
            <span className="font-medium text-gray-900">{chipName} </span>
          )}
          {message}
        </p>
      </div>
    </div>
  );
}
