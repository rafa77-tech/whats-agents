"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Settings, Flag, Shield } from "lucide-react";
import { JuliaToggle } from "./components/julia-toggle";
import { RateLimitCard } from "./components/rate-limit-card";
import { CircuitBreakerCard } from "./components/circuit-breaker-card";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";

interface DashboardStatus {
  julia: {
    is_active: boolean;
    mode: string;
    paused_until?: string;
    pause_reason?: string;
  };
  rate_limit: {
    messages_hour: number;
    messages_day: number;
    limit_hour: number;
    limit_day: number;
    percent_hour: number;
    percent_day: number;
  };
  circuits: {
    evolution: string;
    claude: string;
    supabase: string;
  };
}

function SistemaPageSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid gap-6 md:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

export default function SistemaPage() {
  const { session } = useAuth();
  const [data, setData] = useState<DashboardStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    if (!session?.access_token) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/dashboard/status`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const result = await response.json();
        setData(result);
      }
    } catch (err) {
      console.error("Failed to fetch status:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [session?.access_token]);

  const handleToggle = async (active: boolean, reason?: string) => {
    if (!session?.access_token) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    await fetch(`${apiUrl}/dashboard/controls/julia/toggle`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ active, reason }),
    });

    await fetchStatus();
  };

  const handlePause = async (duration: number, reason: string) => {
    if (!session?.access_token) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    await fetch(`${apiUrl}/dashboard/controls/julia/pause`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ duration_minutes: duration, reason }),
    });

    await fetchStatus();
  };

  const handleUpdateRateLimit = async (limitHour: number, limitDay: number) => {
    if (!session?.access_token) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    await fetch(`${apiUrl}/dashboard/controls/rate-limit`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages_per_hour: limitHour,
        messages_per_day: limitDay,
      }),
    });

    await fetchStatus();
  };

  const handleResetCircuit = async (service: string) => {
    if (!session?.access_token) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    await fetch(`${apiUrl}/dashboard/controls/circuit/${service}/reset`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
    });

    await fetchStatus();
  };

  if (loading) {
    return <SistemaPageSkeleton />;
  }

  if (!data) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Erro ao carregar dados do sistema.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Sistema</h1>
          <p className="text-muted-foreground">
            Controles operacionais da Julia
          </p>
        </div>
      </div>

      {/* Grid principal */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Julia Toggle */}
        <JuliaToggle
          status={data.julia}
          onToggle={handleToggle}
          onPause={handlePause}
        />

        {/* Rate Limit */}
        <RateLimitCard
          status={data.rate_limit}
          onUpdate={handleUpdateRateLimit}
        />

        {/* Circuit Breakers */}
        <CircuitBreakerCard
          status={data.circuits}
          onReset={handleResetCircuit}
        />

        {/* Quick Links */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Configuracoes
            </CardTitle>
            <CardDescription>Acesso rapido</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link href="/sistema/flags">
              <Button variant="outline" className="w-full justify-start">
                <Flag className="h-4 w-4 mr-2" />
                Feature Flags
              </Button>
            </Link>
            <Link href="/auditoria">
              <Button variant="outline" className="w-full justify-start">
                <Shield className="h-4 w-4 mr-2" />
                Logs de Auditoria
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
