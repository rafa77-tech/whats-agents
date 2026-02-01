import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import {
  verificarHospitalExiste,
  verificarHospitalBloqueado,
  bloquearHospital,
  registrarAuditLog,
  type BloquearHospitalRequest,
} from '@/lib/hospitais'

export const dynamic = 'force-dynamic'

/**
 * POST /api/hospitais/bloquear
 * Bloqueia um hospital
 * Body: { hospital_id: string, motivo: string }
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

    const body = (await request.json()) as BloquearHospitalRequest
    const { hospital_id, motivo } = body

    // Validação
    if (!hospital_id || !motivo) {
      return NextResponse.json({ detail: 'hospital_id e motivo são obrigatórios' }, { status: 400 })
    }

    // Verificar se hospital existe
    const { existe, hospital } = await verificarHospitalExiste(supabase, hospital_id)
    if (!existe || !hospital) {
      return NextResponse.json({ detail: 'Hospital não encontrado' }, { status: 404 })
    }

    // Verificar se já está bloqueado
    const { bloqueado } = await verificarHospitalBloqueado(supabase, hospital_id)
    if (bloqueado) {
      return NextResponse.json({ detail: 'Hospital já está bloqueado' }, { status: 400 })
    }

    // Bloquear hospital
    const userEmail = user.email || 'desconhecido'
    const result = await bloquearHospital(supabase, hospital_id, motivo, userEmail)

    // Registrar no audit_log
    await registrarAuditLog(supabase, 'hospital_bloqueado', userEmail, {
      hospital_id,
      hospital_nome: hospital.nome,
      motivo,
      vagas_movidas: result.vagas_movidas,
    })

    return NextResponse.json({
      success: true,
      vagas_movidas: result.vagas_movidas,
    })
  } catch (error) {
    console.error('Erro ao bloquear hospital:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}
