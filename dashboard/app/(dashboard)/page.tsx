/**
 * Dashboard Principal - Sprint 33
 *
 * Layout base com grid responsivo para o dashboard de performance Julia.
 * Este arquivo define a estrutura visual com placeholders que serão
 * substituídos nos épicos subsequentes (E02-E17).
 */

"use client";

import { useState } from "react";
import { DashboardHeader } from "@/components/dashboard/dashboard-header";
import { type DashboardPeriod } from "@/types/dashboard";

export default function DashboardPage() {
  // Estado do período selecionado (default: 7 dias conforme requisito)
  const [selectedPeriod, setSelectedPeriod] = useState<DashboardPeriod>("7d");

  // Mock data para o header (será substituído por dados reais no E08)
  const mockHeaderData = {
    juliaStatus: "online" as const,
    lastHeartbeat: new Date(Date.now() - 2 * 60 * 1000), // 2 minutos atrás
    uptime30d: 99.8,
  };

  const handlePeriodChange = (period: DashboardPeriod) => {
    setSelectedPeriod(period);
    console.log("Período alterado para:", period);
  };

  const handleExport = (format: "csv" | "pdf") => {
    console.log("Exportando em formato:", format);
    // Será implementado nos épicos E16/E17
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1600px] mx-auto p-6 space-y-6">
        {/* Header - E02 */}
        <section aria-label="Header do Dashboard">
          <DashboardHeader
            juliaStatus={mockHeaderData.juliaStatus}
            lastHeartbeat={mockHeaderData.lastHeartbeat}
            uptime30d={mockHeaderData.uptime30d}
            selectedPeriod={selectedPeriod}
            onPeriodChange={handlePeriodChange}
            onExport={handleExport}
          />
        </section>

        {/* Cards de Métricas - 3 colunas */}
        <section
          aria-label="Métricas Principais"
          className="grid grid-cols-1 lg:grid-cols-3 gap-6"
        >
          {/* E03 - Cards de Métricas vs Meta */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-4 w-32 bg-gray-100 rounded animate-pulse" />
                <div className="h-6 w-16 bg-gray-100 rounded animate-pulse" />
              </div>
              <div className="h-12 w-24 bg-gray-100 rounded animate-pulse" />
              <div className="flex items-center gap-2">
                <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
                <div className="h-4 w-16 bg-green-100 rounded animate-pulse" />
              </div>
            </div>
          </div>

          {/* E04 - Cards de Qualidade Persona */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-4 w-40 bg-gray-100 rounded animate-pulse" />
                <div className="h-6 w-16 bg-gray-100 rounded animate-pulse" />
              </div>
              <div className="h-12 w-24 bg-gray-100 rounded animate-pulse" />
              <div className="flex items-center gap-2">
                <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
                <div className="h-4 w-16 bg-green-100 rounded animate-pulse" />
              </div>
            </div>
          </div>

          {/* E05 - Status Operacional e Instâncias */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-4 w-36 bg-gray-100 rounded animate-pulse" />
                <div className="h-6 w-12 bg-green-100 rounded animate-pulse" />
              </div>
              <div className="space-y-2">
                <div className="h-3 w-full bg-gray-100 rounded animate-pulse" />
                <div className="h-3 w-full bg-gray-100 rounded animate-pulse" />
                <div className="h-3 w-3/4 bg-gray-100 rounded animate-pulse" />
              </div>
            </div>
          </div>
        </section>

        {/* Pool de Chips - E06, E07 implementarão */}
        <section aria-label="Pool de Chips">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-5 w-32 bg-gray-100 rounded animate-pulse" />
                <div className="flex items-center gap-2">
                  <div className="h-6 w-20 bg-green-100 rounded animate-pulse" />
                  <div className="h-6 w-20 bg-yellow-100 rounded animate-pulse" />
                  <div className="h-6 w-20 bg-red-100 rounded animate-pulse" />
                </div>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="h-24 bg-gray-50 rounded-lg border border-gray-100 animate-pulse"
                  />
                ))}
              </div>
              <div className="h-48 bg-gray-50 rounded-lg border border-gray-100 animate-pulse" />
            </div>
          </div>
        </section>

        {/* Funil de Conversão - E10, E11 implementarão */}
        <section aria-label="Funil de Conversão">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-5 w-40 bg-gray-100 rounded animate-pulse" />
                <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
              </div>
              <div className="flex items-center gap-2 h-32">
                {[100, 85, 60, 35, 15].map((width, i) => (
                  <div
                    key={i}
                    className="flex-1 h-full flex flex-col items-center justify-end"
                  >
                    <div
                      className="w-full bg-blue-100 rounded-t-lg animate-pulse"
                      style={{ height: `${width}%` }}
                    />
                    <div className="h-4 w-16 bg-gray-100 rounded mt-2 animate-pulse" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Tendências e Alertas - 2 colunas */}
        <section
          aria-label="Tendências e Alertas"
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          {/* E12 - Gráficos Sparkline */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="space-y-4">
              <div className="h-5 w-32 bg-gray-100 rounded animate-pulse" />
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
                    <div className="flex-1 h-10 bg-gray-50 rounded animate-pulse" />
                    <div className="h-4 w-12 bg-gray-100 rounded animate-pulse" />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* E13 - Sistema de Alertas */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-5 w-24 bg-gray-100 rounded animate-pulse" />
                <div className="h-6 w-16 bg-red-100 rounded animate-pulse" />
              </div>
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="p-3 bg-gray-50 rounded-lg border border-gray-100 animate-pulse"
                  >
                    <div className="flex items-start gap-3">
                      <div className="h-5 w-5 bg-gray-200 rounded-full" />
                      <div className="flex-1 space-y-2">
                        <div className="h-4 w-3/4 bg-gray-200 rounded" />
                        <div className="h-3 w-1/2 bg-gray-100 rounded" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Activity Feed - E14 implementará */}
        <section aria-label="Feed de Atividades">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-5 w-36 bg-gray-100 rounded animate-pulse" />
                <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
              </div>
              <div className="divide-y divide-gray-100">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="py-3 flex items-center gap-4">
                    <div className="h-4 w-12 bg-gray-100 rounded animate-pulse" />
                    <div className="h-8 w-8 bg-gray-100 rounded-full animate-pulse" />
                    <div className="flex-1 space-y-1">
                      <div className="h-4 w-3/4 bg-gray-100 rounded animate-pulse" />
                      <div className="h-3 w-1/2 bg-gray-50 rounded animate-pulse" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
