import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { adicionarAlias, removerAlias } from '@/lib/hospitais'

export const dynamic = 'force-dynamic'

/**
 * POST /api/hospitais/[id]/aliases
 * Adiciona alias a um hospital
 * Body: { alias: string }
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id: hospitalId } = await params
    const body = await request.json()

    const alias = typeof body.alias === 'string' ? body.alias.trim() : ''
    if (!alias) {
      return NextResponse.json({ detail: 'alias e obrigatorio' }, { status: 400 })
    }

    const aliasNormalizado = alias
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9\s]/g, '')
      .trim()

    const supabase = createAdminClient()
    const result = await adicionarAlias(supabase, hospitalId, alias, aliasNormalizado)

    return NextResponse.json(result, { status: 201 })
  } catch (error) {
    console.error('Erro ao adicionar alias:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}

/**
 * DELETE /api/hospitais/[id]/aliases
 * Remove alias de um hospital
 * Query: ?alias_id=xxx
 */
export async function DELETE(request: NextRequest) {
  try {
    const aliasId = request.nextUrl.searchParams.get('alias_id')
    if (!aliasId) {
      return NextResponse.json({ detail: 'alias_id e obrigatorio' }, { status: 400 })
    }

    const supabase = createAdminClient()
    await removerAlias(supabase, aliasId)

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao remover alias:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}
