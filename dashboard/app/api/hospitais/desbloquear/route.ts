import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import {
  verificarHospitalBloqueado,
  desbloquearHospital,
  registrarAuditLog,
  type DesbloquearHospitalRequest,
} from '@/lib/hospitais'

export const dynamic = 'force-dynamic'

/**
 * POST /api/hospitais/desbloquear
 * Desbloqueia um hospital
 * Body: { hospital_id: string }
 */
export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient()

    // Verificar autenticação
    const {
      data: { user },
    } = await supabase.auth.getUser()
    if (!user) {
      return NextResponse.json({ detail: 'Não autorizado' }, { status: 401 })
    }

    const body = (await request.json()) as DesbloquearHospitalRequest
    const { hospital_id } = body

    // Validação
    if (!hospital_id) {
      return NextResponse.json({ detail: 'hospital_id é obrigatório' }, { status: 400 })
    }

    // Buscar registro de bloqueio ativo
    const { bloqueado, bloqueio } = await verificarHospitalBloqueado(supabase, hospital_id)
    if (!bloqueado || !bloqueio) {
      return NextResponse.json({ detail: 'Hospital não está bloqueado' }, { status: 404 })
    }

    // Desbloquear hospital
    const userEmail = user.email || 'desconhecido'
    const result = await desbloquearHospital(supabase, hospital_id, bloqueio.id, userEmail)

    // Extrair nome do hospital do bloqueio
    const hospitalNome =
      bloqueio.hospitais && typeof bloqueio.hospitais === 'object' && 'nome' in bloqueio.hospitais
        ? bloqueio.hospitais.nome
        : 'desconhecido'

    // Registrar no audit_log
    await registrarAuditLog(supabase, 'hospital_desbloqueado', userEmail, {
      hospital_id,
      hospital_nome: hospitalNome,
      vagas_restauradas: result.vagas_restauradas,
    })

    return NextResponse.json({
      success: true,
      vagas_restauradas: result.vagas_restauradas,
    })
  } catch (error) {
    console.error('Erro ao desbloquear hospital:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}
