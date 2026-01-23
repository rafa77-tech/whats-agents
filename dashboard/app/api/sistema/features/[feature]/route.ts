/**
 * API: POST /api/sistema/features/[feature]
 *
 * Toggle de feature autonoma individual.
 * Sprint 35: Controle granular de features autonomas.
 */
import { createClient } from '@/lib/supabase/server'
import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const VALID_FEATURES = [
  'discovery_automatico',
  'oferta_automatica',
  'reativacao_automatica',
  'feedback_automatico',
] as const

type FeatureType = (typeof VALID_FEATURES)[number]

interface FeatureToggleBody {
  enabled: boolean
}

interface FeatureToggleResponse {
  success: boolean
  feature: string
  enabled: boolean
  pilot_mode: boolean
  autonomous_features: Record<string, boolean>
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ feature: string }> }
) {
  const { feature } = await params
  const supabase = await createClient()

  // Validar feature
  if (!VALID_FEATURES.includes(feature as FeatureType)) {
    return NextResponse.json(
      { error: `Feature invalida: ${feature}. Validas: ${VALID_FEATURES.join(', ')}` },
      { status: 400 }
    )
  }

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

  const body = (await request.json()) as FeatureToggleBody
  const { enabled } = body

  if (typeof enabled !== 'boolean') {
    return NextResponse.json({ error: 'Campo "enabled" deve ser boolean' }, { status: 400 })
  }

  try {
    // Chamar backend Python para alterar
    const res = await fetch(`${API_URL}/sistema/features/${feature}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: JSON.stringify({
        enabled,
        changed_by: user.email,
      }),
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao alterar feature')
    }

    const data = (await res.json()) as FeatureToggleResponse

    // Log de auditoria
    await supabase.from('audit_log').insert({
      user_id: user.id,
      action: enabled ? 'enable_feature' : 'disable_feature',
      resource: 'sistema',
      details: { feature, enabled },
    })

    return NextResponse.json(data)
  } catch (error) {
    console.error(`Erro ao alterar feature ${feature}:`, error)
    return NextResponse.json(
      { error: `Erro ao alterar feature ${feature}` },
      { status: 500 }
    )
  }
}
