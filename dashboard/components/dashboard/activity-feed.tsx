"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { formatRelativeTime } from "@/lib/utils";
import {
  MessageSquare,
  CheckCircle,
  AlertTriangle,
  UserPlus,
  Send,
  Megaphone,
} from "lucide-react";

// Mock activity data - will be replaced with real API data later
const mockActivities = [
  {
    id: "1",
    tipo: "resposta",
    descricao: "Dr. Carlos Silva respondeu mensagem",
    created_at: new Date(Date.now() - 2 * 60000).toISOString(),
  },
  {
    id: "2",
    tipo: "plantao_confirmado",
    descricao: "Dra. Ana confirmou plantao dia 15/01",
    created_at: new Date(Date.now() - 15 * 60000).toISOString(),
  },
  {
    id: "3",
    tipo: "handoff",
    descricao: "Dr. Pedro solicitou atendimento humano",
    created_at: new Date(Date.now() - 30 * 60000).toISOString(),
  },
  {
    id: "4",
    tipo: "mensagem",
    descricao: "Julia enviou oferta para Dr. Marcos",
    created_at: new Date(Date.now() - 45 * 60000).toISOString(),
  },
  {
    id: "5",
    tipo: "novo_medico",
    descricao: "Novo medico cadastrado: Dr. Felipe Santos",
    created_at: new Date(Date.now() - 60 * 60000).toISOString(),
  },
  {
    id: "6",
    tipo: "campanha",
    descricao: "Campanha 'Cardiologia SP' iniciada",
    created_at: new Date(Date.now() - 2 * 60 * 60000).toISOString(),
  },
];

interface ActivityItem {
  id: string;
  tipo: string;
  descricao: string;
  created_at: string;
}

const ACTIVITY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  mensagem: Send,
  plantao_confirmado: CheckCircle,
  handoff: AlertTriangle,
  novo_medico: UserPlus,
  campanha: Megaphone,
  resposta: MessageSquare,
};

const ACTIVITY_COLORS: Record<string, string> = {
  mensagem: "text-blue-500 bg-blue-50",
  plantao_confirmado: "text-green-500 bg-green-50",
  handoff: "text-red-500 bg-red-50",
  novo_medico: "text-purple-500 bg-purple-50",
  campanha: "text-amber-500 bg-amber-50",
  resposta: "text-emerald-500 bg-emerald-50",
};

export function ActivityFeed() {
  // TODO: Replace with real API call
  const activities: ActivityItem[] = mockActivities;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Atividade Recente</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[200px] pr-4">
          <div className="space-y-4">
            {activities.map((activity) => {
              const Icon = ACTIVITY_ICONS[activity.tipo] || MessageSquare;
              const colorClass = ACTIVITY_COLORS[activity.tipo] || "text-gray-500 bg-gray-50";

              return (
                <div key={activity.id} className="flex items-start gap-3">
                  <div className={`p-1.5 rounded-full ${colorClass}`}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{activity.descricao}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatRelativeTime(activity.created_at)}
                    </p>
                  </div>
                </div>
              );
            })}

            {activities.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                Nenhuma atividade recente
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
