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
import { MetricsSection } from "@/components/dashboard/metrics-section";
import { QualityMetricsSection } from "@/components/dashboard/quality-metrics-section";
import { OperationalStatus } from "@/components/dashboard/operational-status";
import { ChipPoolOverview } from "@/components/dashboard/chip-pool-overview";
import { ChipListTable } from "@/components/dashboard/chip-list-table";
import { ConversionFunnel } from "@/components/dashboard/conversion-funnel";
import { FunnelDrilldownModal } from "@/components/dashboard/funnel-drilldown-modal";
import { TrendsSection } from "@/components/dashboard/trends-section";
import { AlertsList } from "@/components/dashboard/alerts-list";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { type DashboardPeriod } from "@/types/dashboard";
import {
  mockMetricsVsMeta,
  mockQualityMetrics,
  mockOperationalStatus,
  mockChipPoolOverview,
  mockChipsList,
  mockFunnelData,
  mockTrendsData,
  mockAlertsData,
  mockActivityData,
} from "@/lib/mock/dashboard-data";

export default function DashboardPage() {
  // Estado do periodo selecionado (default: 7 dias conforme requisito)
  const [selectedPeriod, setSelectedPeriod] = useState<DashboardPeriod>("7d");

  // Estado do modal de drill-down do funil
  const [funnelModalOpen, setFunnelModalOpen] = useState(false);
  const [selectedFunnelStage, setSelectedFunnelStage] = useState<string | null>(
    null
  );

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

  const handleExport = async (format: "csv" | "pdf") => {
    try {
      const response = await fetch(
        `/api/dashboard/export?format=${format}&period=${selectedPeriod}`
      );

      if (!response.ok) {
        console.error("Export failed:", response.statusText);
        return;
      }

      // Get the blob and create download link
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers.get("Content-Disposition");
      let filename = `dashboard-julia-${selectedPeriod}.${format}`;
      if (contentDisposition) {
        const match = /filename="?([^"]+)"?/.exec(contentDisposition);
        if (match?.[1]) {
          filename = match[1];
        }
      }

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Export error:", error);
    }
  };

  const handleFunnelStageClick = (stageId: string) => {
    setSelectedFunnelStage(stageId);
    setFunnelModalOpen(true);
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

        {/* E03 - Cards de Métricas vs Meta */}
        <section aria-label="Métricas Principais">
          <MetricsSection metrics={mockMetricsVsMeta} />
        </section>

        {/* E04 - Cards de Qualidade Persona */}
        <section aria-label="Qualidade Persona">
          <QualityMetricsSection metrics={mockQualityMetrics} />
        </section>

        {/* E05 - Status Operacional e Instâncias */}
        <section aria-label="Status Operacional">
          <OperationalStatus data={mockOperationalStatus} />
        </section>

        {/* E06 - Pool de Chips - Visao Geral */}
        <section aria-label="Pool de Chips" className="space-y-6">
          <ChipPoolOverview data={mockChipPoolOverview} />
          {/* E07 - Lista Detalhada de Chips */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <ChipListTable chips={mockChipsList} />
          </div>
        </section>

        {/* E10 - Funil de Conversao */}
        <section aria-label="Funil de Conversao">
          <ConversionFunnel
            data={mockFunnelData}
            onStageClick={handleFunnelStageClick}
          />
        </section>

        {/* Tendências e Alertas - 2 colunas */}
        <section
          aria-label="Tendências e Alertas"
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          {/* E12 - Gráficos Sparkline */}
          <TrendsSection data={mockTrendsData} />

          {/* E13 - Sistema de Alertas */}
          <AlertsList initialData={mockAlertsData} />
        </section>

        {/* E14 - Activity Feed */}
        <section aria-label="Feed de Atividades">
          <ActivityFeed initialData={mockActivityData} />
        </section>
      </div>

      {/* E11 - Modal Drill-Down do Funil */}
      <FunnelDrilldownModal
        open={funnelModalOpen}
        onOpenChange={setFunnelModalOpen}
        stage={selectedFunnelStage}
        period={selectedPeriod}
      />
    </div>
  );
}
