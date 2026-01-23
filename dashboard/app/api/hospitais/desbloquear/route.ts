import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

interface DesbloquearRequest {
  hospital_id: string
}

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

    const body = (await request.json()) as DesbloquearRequest
    const { hospital_id } = body

    if (!hospital_id) {
      return NextResponse.json({ detail: 'hospital_id é obrigatório' }, { status: 400 })
    }

    // Buscar registro de bloqueio ativo
    const { data: bloqueio, error: bloqueioError } = await supabase
      .from('hospitais_bloqueados')
      .select('id, vagas_movidas, hospitais(nome)')
      .eq('hospital_id', hospital_id)
      .eq('status', 'bloqueado')
      .single()

    if (bloqueioError || !bloqueio) {
      return NextResponse.json({ detail: 'Hospital não está bloqueado' }, { status: 404 })
    }

    // Atualizar status para desbloqueado
    const { error: updateError } = await supabase
      .from('hospitais_bloqueados')
      .update({
        status: 'desbloqueado',
        desbloqueado_em: new Date().toISOString(),
        desbloqueado_por: user.email || 'desconhecido',
      })
      .eq('id', bloqueio.id)

    if (updateError) {
      console.error('Erro ao desbloquear hospital:', updateError)
      return NextResponse.json({ detail: 'Erro ao desbloquear hospital' }, { status: 500 })
    }

    // Contar vagas que serão restauradas
    const { count: vagasRestauradas } = await supabase
      .from('vagas')
      .select('id', { count: 'exact', head: true })
      .eq('hospital_id', hospital_id)
      .eq('status', 'bloqueada')

    // Restaurar vagas bloqueadas para "aberta"
    await supabase
      .from('vagas')
      .update({ status: 'aberta' })
      .eq('hospital_id', hospital_id)
      .eq('status', 'bloqueada')

    // Registrar no audit_log
    const hospitalNome =
      bloqueio.hospitais && typeof bloqueio.hospitais === 'object' && 'nome' in bloqueio.hospitais
        ? bloqueio.hospitais.nome
        : 'desconhecido'

    await supabase.from('audit_log').insert({
      action: 'hospital_desbloqueado',
      user_email: user.email,
      details: {
        hospital_id,
        hospital_nome: hospitalNome,
        vagas_restauradas: vagasRestauradas || 0,
      },
      created_at: new Date().toISOString(),
    })

    return NextResponse.json({
      success: true,
      vagas_restauradas: vagasRestauradas || 0,
    })
  } catch (error) {
    console.error('Erro ao desbloquear hospital:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
