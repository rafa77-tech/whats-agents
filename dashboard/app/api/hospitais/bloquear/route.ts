import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

interface BloquearRequest {
  hospital_id: string;
  motivo: string;
}

/**
 * POST /api/hospitais/bloquear
 * Bloqueia um hospital
 * Body: { hospital_id: string, motivo: string }
 */
export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient();

    // Verificar autenticação
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ detail: "Não autorizado" }, { status: 401 });
    }

    const body = (await request.json()) as BloquearRequest;
    const { hospital_id, motivo } = body;

    if (!hospital_id || !motivo) {
      return NextResponse.json(
        { detail: "hospital_id e motivo são obrigatórios" },
        { status: 400 }
      );
    }

    // Verificar se hospital existe
    const { data: hospital, error: hospitalError } = await supabase
      .from("hospitais")
      .select("id, nome")
      .eq("id", hospital_id)
      .single();

    if (hospitalError || !hospital) {
      return NextResponse.json(
        { detail: "Hospital não encontrado" },
        { status: 404 }
      );
    }

    // Verificar se já está bloqueado
    const { data: jaExiste } = await supabase
      .from("hospitais_bloqueados")
      .select("id")
      .eq("hospital_id", hospital_id)
      .eq("status", "bloqueado")
      .single();

    if (jaExiste) {
      return NextResponse.json(
        { detail: "Hospital já está bloqueado" },
        { status: 400 }
      );
    }

    // Contar vagas abertas que serão afetadas
    const { count: vagasCount } = await supabase
      .from("vagas")
      .select("id", { count: "exact", head: true })
      .eq("hospital_id", hospital_id)
      .eq("status", "aberta");

    const vagasMovidas = vagasCount || 0;

    // Criar registro de bloqueio
    const { error: insertError } = await supabase
      .from("hospitais_bloqueados")
      .insert({
        hospital_id,
        motivo,
        bloqueado_por: user.email || "desconhecido",
        bloqueado_em: new Date().toISOString(),
        status: "bloqueado",
        vagas_movidas: vagasMovidas,
      });

    if (insertError) {
      console.error("Erro ao bloquear hospital:", insertError);
      return NextResponse.json(
        { detail: "Erro ao bloquear hospital" },
        { status: 500 }
      );
    }

    // Mover vagas para status "bloqueada" (se houver coluna de status)
    // Na implementação real, pode ser necessário mover para tabela separada
    if (vagasMovidas > 0) {
      await supabase
        .from("vagas")
        .update({ status: "bloqueada" })
        .eq("hospital_id", hospital_id)
        .eq("status", "aberta");
    }

    // Registrar no audit_log
    await supabase.from("audit_log").insert({
      action: "hospital_bloqueado",
      user_email: user.email,
      details: {
        hospital_id,
        hospital_nome: hospital.nome,
        motivo,
        vagas_movidas: vagasMovidas,
      },
      created_at: new Date().toISOString(),
    });

    return NextResponse.json({
      success: true,
      vagas_movidas: vagasMovidas,
    });
  } catch (error) {
    console.error("Erro ao bloquear hospital:", error);
    return NextResponse.json(
      { detail: "Erro interno do servidor" },
      { status: 500 }
    );
  }
}
