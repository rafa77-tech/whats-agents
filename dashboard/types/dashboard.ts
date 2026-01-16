/**
 * Dashboard Types - Sprint 33
 *
 * Tipos compartilhados entre os componentes do dashboard.
 */

// ============================================================================
// Period Types
// ============================================================================

export type DashboardPeriod = "7d" | "14d" | "30d";

// ============================================================================
// Header Types
// ============================================================================

export interface DashboardHeaderProps {
  juliaStatus: "online" | "offline";
  lastHeartbeat: Date | null;
  uptime30d: number; // 0-100
  selectedPeriod: DashboardPeriod;
  onPeriodChange: (period: DashboardPeriod) => void;
  onExport: (format: "csv" | "pdf") => void;
}

// ============================================================================
// Status Types
// ============================================================================

export interface JuliaStatus {
  status: "online" | "offline";
  lastHeartbeat: string | null; // ISO timestamp
  uptime30d: number;
  activeChips: number;
  totalChips: number;
}

// ============================================================================
// Metric Types
// ============================================================================

export type MetricUnit = "percent" | "number" | "currency";
export type MetaOperator = "gt" | "lt" | "eq"; // greater than, less than, equal

export interface MetricData {
  label: string;
  value: number;
  unit: MetricUnit;
  meta: number;
  previousValue: number;
  metaOperator: MetaOperator;
}

export type QualityUnit = "percent" | "seconds";
export type ThresholdOperator = "lt" | "gt"; // less than or greater than for "good"

export interface QualityThreshold {
  good: number;
  warning: number;
}

export interface QualityMetricData {
  label: string;
  value: number;
  unit: QualityUnit;
  threshold: QualityThreshold;
  operator: ThresholdOperator;
  previousValue: number;
  tooltip?: string;
}

// ============================================================================
// Operational Status Types
// ============================================================================

export interface RateLimitData {
  current: number;
  max: number;
  label: string;
}

export interface LLMUsageData {
  haiku: number; // percentage
  sonnet: number; // percentage
}

export interface WhatsAppInstance {
  name: string;
  status: "online" | "offline";
  messagesToday: number;
}

export interface OperationalStatusData {
  rateLimitHour: RateLimitData;
  rateLimitDay: RateLimitData;
  queueSize: number;
  llmUsage: LLMUsageData;
  instances: WhatsAppInstance[];
}

// ============================================================================
// Chip Types
// ============================================================================

export type ChipStatus =
  | "provisioned"
  | "pending"
  | "warming"
  | "ready"
  | "active"
  | "degraded"
  | "paused"
  | "banned"
  | "cancelled";

export type TrustLevel = "verde" | "amarelo" | "laranja" | "vermelho";

export interface ChipSummary {
  id: string;
  name: string;
  status: ChipStatus;
  trustScore: number;
  trustLevel: TrustLevel;
  messagesToday: number;
  dailyLimit: number;
  responseRate: number;
  errors24h: number;
  lastActive: string | null;
}

export interface ChipDetail {
  id: string;
  name: string;
  telefone: string;
  status: ChipStatus;
  trustScore: number;
  trustLevel: TrustLevel;
  messagesToday: number;
  dailyLimit: number;
  responseRate: number;
  errorsLast24h: number;
  hasActiveAlert: boolean;
  alertMessage?: string;
  warmingDay?: number; // se estiver em warming
}

export interface ChipPoolMetrics {
  totalChips: number;
  activeChips: number;
  warmingChips: number;
  degradedChips: number;
  avgTrustScore: number;
  totalMessagesToday: number;
  totalDailyCapacity: number;
}

export interface ChipStatusCount {
  status: ChipStatus;
  count: number;
}

export interface TrustDistribution {
  level: TrustLevel;
  count: number;
  percentage: number;
}

export interface ChipPoolAggregatedMetrics {
  totalMessagesSent: number;
  avgResponseRate: number;
  avgBlockRate: number;
  totalErrors: number;
  // Comparativos
  previousMessagesSent: number;
  previousResponseRate: number;
  previousBlockRate: number;
  previousErrors: number;
}

export interface ChipPoolOverviewData {
  statusCounts: ChipStatusCount[];
  trustDistribution: TrustDistribution[];
  metrics: ChipPoolAggregatedMetrics;
}

// ============================================================================
// Funnel Types
// ============================================================================

export interface FunnelStage {
  stage: string;
  count: number;
  percentage: number;
  change: number; // vs previous period
}

export interface FunnelData {
  stages: FunnelStage[];
  period: {
    start: string;
    end: string;
  };
}

// Visual funnel for dashboard component
export interface FunnelStageVisual {
  id: string;
  label: string;
  count: number;
  previousCount: number;
  percentage: number; // em relacao ao total (primeira etapa)
}

export interface FunnelDataVisual {
  stages: FunnelStageVisual[];
  period: string;
}

// ============================================================================
// Alert Types
// ============================================================================

export type AlertSeverity = "critical" | "warning" | "info";
export type AlertCategory = "julia" | "chip" | "operational" | "vaga";

export interface DashboardAlert {
  id: string;
  severity: AlertSeverity;
  category: AlertCategory;
  title: string;
  message: string;
  createdAt: string; // ISO timestamp
  actionLabel?: string;
  actionUrl?: string;
  metadata?: Record<string, unknown>;
}

export interface AlertsData {
  alerts: DashboardAlert[];
  totalCritical: number;
  totalWarning: number;
}

// ============================================================================
// Activity Types
// ============================================================================

export type ActivityType =
  | "fechamento"
  | "handoff"
  | "campanha"
  | "resposta"
  | "chip"
  | "alerta";

export interface ActivityEvent {
  id: string;
  type: ActivityType;
  message: string;
  details?: string;
  chipName?: string;
  timestamp: string; // ISO timestamp
  metadata?: Record<string, unknown>;
}

export interface ActivityFeedData {
  events: ActivityEvent[];
  hasMore: boolean;
}

// ============================================================================
// Export Types
// ============================================================================

export interface DashboardExportData {
  period: { start: string; end: string };
  metrics: Array<{
    name: string;
    current: number;
    previous: number;
    meta: number;
    unit: string;
  }>;
  quality: Array<{
    name: string;
    current: number;
    previous: number;
    meta: string;
    unit: string;
  }>;
  chips: Array<{
    name: string;
    status: string;
    trust: number;
    messagesToday: number;
    responseRate: number;
    errors: number;
  }>;
  funnel: Array<{
    stage: string;
    count: number;
    percentage: number;
    change: number;
  }>;
}
