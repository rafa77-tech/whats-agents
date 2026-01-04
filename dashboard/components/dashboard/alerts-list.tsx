"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle, AlertCircle, Info, ArrowRight } from "lucide-react";

// Mock alerts - will be replaced with real API data
const mockAlerts = [
  {
    id: "1",
    tipo: "warning" as const,
    titulo: "Rate Limit Alto",
    mensagem: "80% do limite diario atingido",
    action_url: "/sistema",
    created_at: new Date(Date.now() - 10 * 60000).toISOString(),
  },
  // Uncomment to show more alerts:
  // {
  //   id: "2",
  //   tipo: "critical" as const,
  //   titulo: "Circuit Breaker Aberto",
  //   mensagem: "Evolution API nao responde",
  //   action_url: "/sistema",
  //   created_at: new Date(Date.now() - 30 * 60000).toISOString(),
  // },
];

interface AlertItem {
  id: string;
  tipo: "critical" | "warning" | "info";
  titulo: string;
  mensagem: string;
  action_url?: string;
  created_at: string;
}

const ALERT_ICONS = {
  critical: AlertTriangle,
  warning: AlertCircle,
  info: Info,
};

const ALERT_VARIANTS = {
  critical: "destructive" as const,
  warning: "default" as const,
  info: "default" as const,
};

export function AlertsList() {
  // TODO: Replace with real API call
  const alerts: AlertItem[] = mockAlerts;

  if (alerts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Alertas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-muted-foreground">
            <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Nenhum alerta ativo</p>
            <p className="text-sm">Tudo funcionando normalmente</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <span>Alertas</span>
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground text-xs">
            {alerts.length}
          </span>
        </CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/sistema/alertas">
            Ver todos
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {alerts.map((alert) => {
          const Icon = ALERT_ICONS[alert.tipo];

          return (
            <Alert key={alert.id} variant={ALERT_VARIANTS[alert.tipo]}>
              <Icon className="h-4 w-4" />
              <AlertTitle className="text-sm">{alert.titulo}</AlertTitle>
              <AlertDescription className="text-xs">
                {alert.mensagem}
                {alert.action_url && (
                  <Link
                    href={alert.action_url}
                    className="ml-2 underline hover:no-underline"
                  >
                    Ver detalhes
                  </Link>
                )}
              </AlertDescription>
            </Alert>
          );
        })}
      </CardContent>
    </Card>
  );
}
