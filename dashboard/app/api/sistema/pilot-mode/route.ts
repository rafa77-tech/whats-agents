import { createClient } from '@/lib/supabase/server'
import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PilotModeBody {
  pilot_mode: boolean
}

export async function POST(request: NextRequest) {
  const supabase = await createClient()

  // Verificar autenticacao
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    return NextResponse.json({ error: 'Nao autorizado' }, { status: 401 })
  }

  // Verificar role admin
  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single()

  if (profile?.role !== 'admin') {
    return NextResponse.json(
      { error: 'Permissao negada. Apenas admins podem alterar.' },
      { status: 403 }
    )
  }

  const body = (await request.json()) as PilotModeBody
  const { pilot_mode } = body

  try {
    // Chamar backend Python para alterar
    const res = await fetch(`${API_URL}/sistema/pilot-mode`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: JSON.stringify({
        pilot_mode,
        changed_by: user.email,
      }),
    })

    if (!res.ok) throw new Error('Erro ao alterar')

    const data: unknown = await res.json()

    // Log de auditoria
    await supabase.from('audit_log').insert({
      user_id: user.id,
      action: pilot_mode ? 'enable_pilot_mode' : 'disable_pilot_mode',
      resource: 'sistema',
      details: { pilot_mode },
    })

    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao alterar modo piloto:', error)
    return NextResponse.json({ error: 'Erro ao alterar modo piloto' }, { status: 500 })
  }
}
