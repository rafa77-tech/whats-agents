import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

interface ResponderBody {
  resposta: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * POST /api/ajuda/[id]/responder
 * Responde a um pedido de ajuda
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const supabase = await createClient();
    const { id } = await params;

    // Verificar autenticacao
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ detail: "Nao autorizado" }, { status: 401 });
    }

    const body = (await request.json()) as ResponderBody;
    const { resposta } = body;

    if (!resposta?.trim()) {
      return NextResponse.json(
        { detail: "Resposta e obrigatoria" },
        { status: 400 }
      );
    }

    // Buscar pedido
    const { data: pedido, error: pedidoError } = await supabase
      .from("pedidos_ajuda")
      .select("*")
      .eq("id", id)
      .single();

    if (pedidoError || !pedido) {
      return NextResponse.json(
        { detail: "Pedido nao encontrado" },
        { status: 404 }
      );
    }

    // Atualizar pedido
    const { data, error } = await supabase
      .from("pedidos_ajuda")
      .update({
        status: "respondido",
        resposta: resposta.trim(),
        respondido_por: user.email || user.id,
        respondido_em: new Date().toISOString(),
      })
      .eq("id", id)
      .select()
      .single();

    if (error) {
      console.error("Erro ao atualizar pedido:", error);
      return NextResponse.json(
        { detail: "Erro ao atualizar pedido" },
        { status: 500 }
      );
    }

    // Retomar conversa (chamar backend Python)
    try {
      await fetch(`${API_URL}/conversas/${pedido.conversa_id}/retomar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${process.env.API_SECRET ?? ""}`,
        },
        body: JSON.stringify({
          resposta_gestor: resposta.trim(),
          pedido_ajuda_id: id,
        }),
      });
    } catch (error) {
      console.error("Erro ao retomar conversa:", error);
      // Nao falha a request - pedido ja foi marcado como respondido
    }

    // Registrar no audit_log
    await supabase.from("audit_log").insert({
      action: "pedido_ajuda_respondido",
      user_email: user.email,
      details: {
        pedido_id: id,
        conversa_id: pedido.conversa_id,
      },
      created_at: new Date().toISOString(),
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Erro ao responder pedido:", error);
    return NextResponse.json(
      { detail: "Erro interno do servidor" },
      { status: 500 }
    );
  }
}
