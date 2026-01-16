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

    return NextResponse.json({
      stages: {
        enviadas: {
          count: enviadasCurrent || 0,
          previous: enviadasPrevious || 0,
        },
        entregues: {
          count: entreguesCurrent || 0,
          previous: entreguesPrevious || 0,
        },
        respostas: {
          count: respostasCurrent || 0,
          previous: respostasPrevious || 0,
        },
        interesse: {
          count: interesseCurrent || 0,
          previous: interessePrevious || 0,
        },
        fechadas: {
          count: fechadasCurrent || 0,
          previous: fechadasPrevious || 0,
        },
      },
      period: {
        start: currentStart,
        end: currentEnd,
        days,
      },
    });
  } catch (error) {
    console.error("Error fetching funnel data:", error);
    return NextResponse.json(
      { error: "Failed to fetch funnel data" },
      { status: 500 }
    );
  }
}
