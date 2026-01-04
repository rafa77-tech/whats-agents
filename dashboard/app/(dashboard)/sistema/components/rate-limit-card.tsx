"use client";

import { useState } from "react";
import { Gauge, Settings } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/hooks/use-auth";

interface RateLimitStatus {
  messages_hour: number;
  messages_day: number;
  limit_hour: number;
  limit_day: number;
  percent_hour: number;
  percent_day: number;
}

interface Props {
  status: RateLimitStatus;
  onUpdate?: (limitHour: number, limitDay: number) => Promise<void>;
}

export function RateLimitCard({ status, onUpdate }: Props) {
  const [showSettings, setShowSettings] = useState(false);
  const [newLimitHour, setNewLimitHour] = useState(status.limit_hour);
  const [newLimitDay, setNewLimitDay] = useState(status.limit_day);
  const [loading, setLoading] = useState(false);

  const { user } = useAuth();
  const canEdit = user?.role === "admin";

  const handleUpdate = async () => {
    if (!onUpdate) return;
    setLoading(true);
    try {
      await onUpdate(newLimitHour, newLimitDay);
      setShowSettings(false);
    } finally {
      setLoading(false);
    }
  };

  const getProgressColor = (percent: number) => {
    if (percent >= 90) return "bg-red-500";
    if (percent >= 70) return "bg-yellow-500";
    return "bg-green-500";
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-full bg-blue-100">
                <Gauge className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <CardTitle className="text-lg">Rate Limit</CardTitle>
                <CardDescription>Controle de envios</CardDescription>
              </div>
            </div>
            {canEdit && onUpdate && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowSettings(true)}
              >
                <Settings className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Por hora */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Esta hora</span>
              <span className="font-medium">
                {status.messages_hour} / {status.limit_hour}
              </span>
            </div>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${getProgressColor(status.percent_hour)}`}
                style={{ width: `${Math.min(status.percent_hour, 100)}%` }}
              />
            </div>
          </div>

          {/* Por dia */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Hoje</span>
              <span className="font-medium">
                {status.messages_day} / {status.limit_day}
              </span>
            </div>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${getProgressColor(status.percent_day)}`}
                style={{ width: `${Math.min(status.percent_day, 100)}%` }}
              />
            </div>
          </div>

          {/* Alertas */}
          {status.percent_hour >= 90 && (
            <div className="p-2 bg-red-50 rounded text-sm text-red-600">
              Limite horario quase atingido!
            </div>
          )}
          {status.percent_day >= 90 && (
            <div className="p-2 bg-red-50 rounded text-sm text-red-600">
              Limite diario quase atingido!
            </div>
          )}
        </CardContent>
      </Card>

      {/* Settings Dialog */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Configurar Rate Limit</DialogTitle>
            <DialogDescription>
              Ajuste os limites de mensagens. Valores muito altos podem causar
              ban.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="limit-hour">Limite por hora</Label>
              <Input
                id="limit-hour"
                type="number"
                min={1}
                max={50}
                value={newLimitHour}
                onChange={(e) => setNewLimitHour(parseInt(e.target.value) || 20)}
              />
              <p className="text-xs text-muted-foreground">
                Recomendado: 20. Maximo seguro: 50
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="limit-day">Limite por dia</Label>
              <Input
                id="limit-day"
                type="number"
                min={10}
                max={200}
                value={newLimitDay}
                onChange={(e) => setNewLimitDay(parseInt(e.target.value) || 100)}
              />
              <p className="text-xs text-muted-foreground">
                Recomendado: 100. Maximo seguro: 200
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSettings(false)}>
              Cancelar
            </Button>
            <Button onClick={handleUpdate} disabled={loading}>
              {loading ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
