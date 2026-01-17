/**
 * API: GET /api/dashboard/funnel
 *
 * Retorna dados do funil de conversao.
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getPeriodDates, validatePeriod } from "@/lib/dashboard/calculations";

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const period = validatePeriod(request.nextUrl.searchParams.get("period"));
    const { currentStart, currentEnd, previousStart, previousEnd, days } =
      getPeriodDates(period);

    // === Enviadas (mensagens na fila que foram processadas) ===

    const { count: enviadasCurrent } = await supabase
      .from("fila_mensagens")
      .select("*", { count: "exact", head: true })
      .in("outcome", ["delivered", "sent", "read"])
      .gte("created_at", currentStart)
      .lte("created_at", currentEnd);

    const { count: enviadasPrevious } = await supabase
      .from("fila_mensagens")
      .select("*", { count: "exact", head: true })
      .in("outcome", ["delivered", "sent", "read"])
      .gte("created_at", previousStart)
      .lte("created_at", previousEnd);

    // === Entregues (outcome = delivered) ===

    const { count: entreguesCurrent } = await supabase
      .from("fila_mensagens")
      .select("*", { count: "exact", head: true })
      .eq("outcome", "delivered")
      .gte("created_at", currentStart)
      .lte("created_at", currentEnd);

    const { count: entreguesPrevious } = await supabase
      .from("fila_mensagens")
      .select("*", { count: "exact", head: true })
      .eq("outcome", "delivered")
      .gte("created_at", previousStart)
      .lte("created_at", previousEnd);

    // === Respostas (interacoes com direcao 'in') ===

    const { count: respostasCurrent } = await supabase
      .from("interacoes")
      .select("*", { count: "exact", head: true })
      .eq("direcao", "in")
      .gte("created_at", currentStart)
      .lte("created_at", currentEnd);

    const { count: respostasPrevious } = await supabase
      .from("interacoes")
      .select("*", { count: "exact", head: true })
      .eq("direcao", "in")
      .gte("created_at", previousStart)
      .lte("created_at", previousEnd);

    // === Interesse (conversations com stage que indica interesse) ===

    const { count: interesseCurrent } = await supabase
      .from("conversations")
      .select("*", { count: "exact", head: true })
      .in("stage", ["interesse", "negociacao", "qualificado", "proposta"])
      .gte("updated_at", currentStart)
      .lte("updated_at", currentEnd);

    const { count: interessePrevious } = await supabase
      .from("conversations")
      .select("*", { count: "exact", head: true })
      .in("stage", ["interesse", "negociacao", "qualificado", "proposta"])
      .gte("updated_at", previousStart)
      .lte("updated_at", previousEnd);

    // === Fechadas (conversations com status fechado/completed) ===

    const { count: fechadasCurrent } = await supabase
      .from("conversations")
      .select("*", { count: "exact", head: true })
      .in("status", ["fechado", "completed", "convertido"])
      .gte("completed_at", currentStart)
      .lte("completed_at", currentEnd);

    const { count: fechadasPrevious } = await supabase
      .from("conversations")
      .select("*", { count: "exact", head: true })
      .in("status", ["fechado", "completed", "convertido"])
      .gte("completed_at", previousStart)
      .lte("completed_at", previousEnd);

    // Calculate percentages based on enviadas
    const enviadasCount = enviadasCurrent || 1;
    const entreguesCount = entreguesCurrent || 0;
    const respostasCount = respostasCurrent || 0;
    const interesseCount = interesseCurrent || 0;
    const fechadasCount = fechadasCurrent || 0;

    return NextResponse.json({
      stages: [
        {
          id: "enviadas",
          label: "Enviadas",
          count: enviadasCount,
          previousCount: enviadasPrevious || 0,
          percentage: 100,
        },
        {
          id: "entregues",
          label: "Entregues",
          count: entreguesCount,
          previousCount: entreguesPrevious || 0,
          percentage: Number(((entreguesCount / enviadasCount) * 100).toFixed(1)),
        },
        {
          id: "respostas",
          label: "Respostas",
          count: respostasCount,
          previousCount: respostasPrevious || 0,
          percentage: Number(((respostasCount / enviadasCount) * 100).toFixed(1)),
        },
        {
          id: "interesse",
          label: "Interesse",
          count: interesseCount,
          previousCount: interessePrevious || 0,
          percentage: Number(((interesseCount / enviadasCount) * 100).toFixed(1)),
        },
        {
          id: "fechadas",
          label: "Fechadas",
          count: fechadasCount,
          previousCount: fechadasPrevious || 0,
          percentage: Number(((fechadasCount / enviadasCount) * 100).toFixed(1)),
        },
      ],
      period: `${days} dias`,
    });
  } catch (error) {
    console.error("Error fetching funnel data:", error);
    return NextResponse.json(
      { error: "Failed to fetch funnel data" },
      { status: 500 }
    );
  }
}
