/**
 * API: GET /api/dashboard/quality
 *
 * Retorna metricas de qualidade (bot detection, latencia, handoff rate).
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import {
  getPeriodDates,
  calculateRate,
  validatePeriod,
} from "@/lib/dashboard/calculations";

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const period = validatePeriod(request.nextUrl.searchParams.get("period"));
    const { currentStart, currentEnd, previousStart, previousEnd } =
      getPeriodDates(period);

    // === Bot Detection ===

    // Total de conversas no periodo atual
    const { count: conversasCurrent } = await supabase
      .from("conversations")
      .select("*", { count: "exact", head: true })
      .gte("created_at", currentStart)
      .lte("created_at", currentEnd);

    // Deteccoes de bot no periodo atual
    const { count: botDetectionsCurrent } = await supabase
      .from("metricas_deteccao_bot")
      .select("*", { count: "exact", head: true })
      .gte("created_at", currentStart)
      .lte("created_at", currentEnd);

    // Total de conversas no periodo anterior
    const { count: conversasPrevious } = await supabase
      .from("conversations")
      .select("*", { count: "exact", head: true })
      .gte("created_at", previousStart)
      .lte("created_at", previousEnd);

    // Deteccoes de bot no periodo anterior
    const { count: botDetectionsPrevious } = await supabase
      .from("metricas_deteccao_bot")
      .select("*", { count: "exact", head: true })
      .gte("created_at", previousStart)
      .lte("created_at", previousEnd);

    const botRateCurrent = calculateRate(
      botDetectionsCurrent || 0,
      conversasCurrent || 0
    );
    const botRatePrevious = calculateRate(
      botDetectionsPrevious || 0,
      conversasPrevious || 0
    );

    // === Latencia Media ===

    // Buscar latencia media das interacoes (tempo entre msg recebida e resposta)
    // Usando chip_metrics_hourly que tem tempo_resposta_medio_segundos
    const { data: latencyCurrent } = await supabase
      .from("chip_metrics_hourly")
      .select("tempo_resposta_medio_segundos")
      .gte("hora", currentStart)
      .lte("hora", currentEnd)
      .not("tempo_resposta_medio_segundos", "is", null);

    const { data: latencyPrevious } = await supabase
      .from("chip_metrics_hourly")
      .select("tempo_resposta_medio_segundos")
      .gte("hora", previousStart)
      .lte("hora", previousEnd)
      .not("tempo_resposta_medio_segundos", "is", null);

    const avgLatencyCurrent =
      latencyCurrent && latencyCurrent.length > 0
        ? Number(
            (
              latencyCurrent.reduce(
                (sum, row) =>
                  sum + ((row.tempo_resposta_medio_segundos as number) || 0),
                0
              ) / latencyCurrent.length
            ).toFixed(1)
          )
        : 0;

    const avgLatencyPrevious =
      latencyPrevious && latencyPrevious.length > 0
        ? Number(
            (
              latencyPrevious.reduce(
                (sum, row) =>
                  sum + ((row.tempo_resposta_medio_segundos as number) || 0),
                0
              ) / latencyPrevious.length
            ).toFixed(1)
          )
        : 0;

    // === Handoff Rate ===

    // Handoffs no periodo atual
    const { count: handoffsCurrent } = await supabase
      .from("handoffs")
      .select("*", { count: "exact", head: true })
      .gte("created_at", currentStart)
      .lte("created_at", currentEnd);

    // Handoffs no periodo anterior
    const { count: handoffsPrevious } = await supabase
      .from("handoffs")
      .select("*", { count: "exact", head: true })
      .gte("created_at", previousStart)
      .lte("created_at", previousEnd);

    const handoffRateCurrent = calculateRate(
      handoffsCurrent || 0,
      conversasCurrent || 0
    );
    const handoffRatePrevious = calculateRate(
      handoffsPrevious || 0,
      conversasPrevious || 0
    );

    return NextResponse.json({
      metrics: {
        botDetection: {
          value: botRateCurrent,
          previous: botRatePrevious,
        },
        avgLatency: {
          value: avgLatencyCurrent,
          previous: avgLatencyPrevious,
        },
        handoffRate: {
          value: handoffRateCurrent,
          previous: handoffRatePrevious,
        },
      },
    });
  } catch (error) {
    console.error("Error fetching dashboard quality metrics:", error);
    return NextResponse.json(
      { error: "Failed to fetch quality metrics" },
      { status: 500 }
    );
  }
}
