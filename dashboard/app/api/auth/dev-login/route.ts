import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

/**
 * POST /api/auth/dev-login
 * Bypass de autenticacao APENAS para desenvolvimento local
 * Usa signInAnonymously para criar sessao sem usuario real
 */
export async function POST() {
  // Bloquear em producao
  if (process.env.NEXT_PUBLIC_ENV === 'production' || process.env.NODE_ENV === 'production') {
    return NextResponse.json(
      { error: 'Dev login nao permitido em producao' },
      { status: 403 }
    )
  }

  // Verificar se eh localhost
  const isLocalhost = process.env.NEXT_PUBLIC_SITE_URL?.includes('localhost')
  if (!isLocalhost) {
    return NextResponse.json(
      { error: 'Dev login apenas permitido em localhost' },
      { status: 403 }
    )
  }

  try {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

    if (!supabaseUrl || !supabaseAnonKey) {
      return NextResponse.json(
        { error: 'Supabase nao configurado' },
        { status: 500 }
      )
    }

    const supabase = createClient(supabaseUrl, supabaseAnonKey)

    // Tentar login anonimo
    const { data, error } = await supabase.auth.signInAnonymously()

    if (error) {
      console.error('Erro no login anonimo:', error)

      // Se login anonimo nao esta habilitado, informar
      if (error.message.includes('Anonymous sign-ins are disabled')) {
        return NextResponse.json(
          {
            error: 'Login anonimo desabilitado. Habilite no Supabase Dashboard.',
            hint: 'Authentication > Providers > Anonymous Sign-In > Enable',
            alternative: 'Ou use o magic link normal para testar'
          },
          { status: 400 }
        )
      }

      return NextResponse.json(
        { error: `Erro no dev login: ${error.message}` },
        { status: 500 }
      )
    }

    return NextResponse.json({
      session: data.session,
      user: data.user,
    })
  } catch (err) {
    console.error('Erro no dev login:', err)
    return NextResponse.json(
      { error: 'Erro ao fazer dev login' },
      { status: 500 }
    )
  }
}
