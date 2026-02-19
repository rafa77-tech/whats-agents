/**
 * API Market Intelligence Vagas Hoje - Sprint 64
 *
 * Retorna vagas importadas hoje e ranking de grupos por vagas importadas.
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()

    // 1. Grupos com contagem de vagas importadas (30d)
    const { data: gruposRaw, error: gruposError } = await supabase.rpc('get_grupos_vagas_count')

    // Fallback: query direta se a RPC não existir
    let grupos: Array<{ id: string; nome: string; vagas_importadas: number }>
    if (gruposError) {
      const { data, error } = await supabase
        .from('vagas_grupo')
        .select('grupo_origem_id, grupos_whatsapp!inner(id, nome, ativo)')
        .eq('status', 'importada')
        .eq('eh_duplicada', false)
        .gte('created_at', new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString())

      if (error) {
        console.error('[Vagas Hoje] Erro ao buscar grupos:', error)
        return NextResponse.json({ error: 'Erro ao buscar grupos' }, { status: 500 })
      }

      // Agregar por grupo
      const contagem = new Map<string, { id: string; nome: string; count: number }>()
      for (const row of data || []) {
        const grupo = row.grupos_whatsapp as unknown as {
          id: string
          nome: string
          ativo: boolean
        }
        if (!grupo.ativo) continue
        const existing = contagem.get(grupo.id)
        if (existing) {
          existing.count++
        } else {
          contagem.set(grupo.id, { id: grupo.id, nome: grupo.nome, count: 1 })
        }
      }

      grupos = Array.from(contagem.values())
        .map((g) => ({ id: g.id, nome: g.nome, vagas_importadas: g.count }))
        .sort((a, b) => b.vagas_importadas - a.vagas_importadas)
    } else {
      grupos = gruposRaw || []
    }

    // 2. Vagas importadas hoje
    const hoje = new Date()
    hoje.setHours(0, 0, 0, 0)

    const { data: vagasHoje, error: vagasError } = await supabase
      .from('vagas_grupo')
      .select(
        `
        id,
        hospital_raw,
        especialidade_raw,
        valor,
        data,
        periodo,
        created_at,
        grupo_origem_id,
        mensagem_id,
        grupos_whatsapp!inner(nome),
        mensagens_grupo(texto, sender_nome, created_at)
      `
      )
      .eq('status', 'importada')
      .eq('eh_duplicada', false)
      .gte('created_at', hoje.toISOString())
      .order('created_at', { ascending: false })
      .limit(50)

    if (vagasError) {
      console.error('[Vagas Hoje] Erro ao buscar vagas:', vagasError)
      return NextResponse.json({ error: 'Erro ao buscar vagas' }, { status: 500 })
    }

    const vagas = (vagasHoje || []).map((v) => {
      const msg = v.mensagens_grupo as unknown as {
        texto: string
        sender_nome: string
        created_at: string
      } | null

      return {
        id: v.id,
        hospital: v.hospital_raw,
        especialidade: v.especialidade_raw,
        valor: v.valor,
        data: v.data,
        periodo: v.periodo,
        grupo: (v.grupos_whatsapp as unknown as { nome: string })?.nome ?? '-',
        created_at: v.created_at,
        mensagem_original: msg
          ? { texto: msg.texto, sender_nome: msg.sender_nome, created_at: msg.created_at }
          : null,
      }
    })

    return NextResponse.json({ grupos, vagas })
  } catch (error) {
    console.error('[Vagas Hoje] Erro:', error)
    return NextResponse.json({ error: 'Erro interno' }, { status: 500 })
  }
}
