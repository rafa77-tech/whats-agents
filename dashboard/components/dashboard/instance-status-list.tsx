"use client";

import { type WhatsAppInstance } from "@/types/dashboard";

interface InstanceStatusListProps {
  instances: WhatsAppInstance[];
}

export function InstanceStatusList({ instances }: InstanceStatusListProps) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700">Instancias WhatsApp</h4>
      <div className="space-y-1">
        {instances.map((instance) => (
          <div
            key={instance.name}
            className="flex items-center justify-between py-1.5 px-2 bg-gray-50 rounded"
          >
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  instance.status === "online" ? "bg-green-500" : "bg-red-500"
                }`}
              />
              <span className="text-sm font-medium">{instance.name}</span>
            </div>
            <span className="text-sm text-gray-500">
              {instance.messagesToday} msgs
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
