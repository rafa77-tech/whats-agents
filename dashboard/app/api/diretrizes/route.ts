import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

/**
 * GET /api/diretrizes
 * Lista diretrizes contextuais
 * Query params:
 *   - status: "ativa" | "expirada,cancelada" (default: "ativa")
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const status = request.nextUrl.searchParams.get("status") || "ativa";
    const statusArray = status.split(",");

    const { data, error } = await supabase
      .from("diretrizes_contextuais")
      .select(
        `
        *,
        vagas (data, hospital_id),
        clientes (primeiro_nome, sobrenome, telefone),
        hospitais (nome),
        especialidades (nome)
      `
      )
      .in("status", statusArray)
      .order("created_at", { ascending: false });

    if (error) {
      console.error("Erro ao buscar diretrizes:", error);
      return NextResponse.json(
        { detail: "Erro ao buscar diretrizes" },
        { status: 500 }
      );
    }

    return NextResponse.json(data || []);
  } catch (error) {
    console.error("Erro ao buscar diretrizes:", error);
    return NextResponse.json(
      { detail: "Erro interno do servidor" },
      { status: 500 }
    );
  }
}

/**
 * POST /api/diretrizes
 * Cria uma nova diretriz contextual
 */
export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient();

    // Verificar autenticacao
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ detail: "Nao autorizado" }, { status: 401 });
    }

    const body = (await request.json()) as Record<string, unknown>;

    const { data, error } = await supabase
      .from("diretrizes_contextuais")
      .insert({
        ...body,
        criado_por: user.email || user.id,
        criado_em: new Date().toISOString(),
        status: "ativa",
      })
      .select()
      .single();

    if (error) {
      console.error("Erro ao criar diretriz:", error);
      return NextResponse.json(
        { detail: "Erro ao criar diretriz" },
        { status: 500 }
      );
    }

    // Registrar no audit_log
    await supabase.from("audit_log").insert({
      action: "diretriz_criada",
      user_email: user.email,
      details: {
        diretriz_id: data.id,
        tipo: body.tipo,
        escopo: body.escopo,
      },
      created_at: new Date().toISOString(),
    });

    return NextResponse.json(data);
  } catch (error) {
    console.error("Erro ao criar diretriz:", error);
    return NextResponse.json(
      { detail: "Erro interno do servidor" },
      { status: 500 }
    );
  }
}
