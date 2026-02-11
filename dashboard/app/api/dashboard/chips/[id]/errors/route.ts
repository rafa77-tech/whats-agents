/**
 * API: GET /api/dashboard/chips/[id]/errors
 *
 * Retorna erros recentes de um chip (ultimas 24h).
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

interface ErrorRow {
  id: string
  tipo: string
  error_code: number | null
  error_message: string | null
  sucesso: boolean
  created_at: string
  destinatario: string | null
}

interface ChipRow {
  ultimo_erro_msg: string | null
  ultimo_erro_codigo: number | null
  ultimo_erro_em: string | null
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: chipId } = await params
    const supabase = await createClient()
    const searchParams = request.nextUrl.searchParams
    const limit = parseInt(searchParams.get('limit') || '20')

    // Buscar informacoes do chip (ultimo erro)
    const { data: chipData } = await supabase
      .from('chips')
      .select('ultimo_erro_msg, ultimo_erro_codigo, ultimo_erro_em')
      .eq('id', chipId)
      .single()

    const chip = chipData as ChipRow | null

    // Buscar interacoes com erro nas ultimas 24h
    const oneDayAgo = new Date()
    oneDayAgo.setDate(oneDayAgo.getDate() - 1)

    const { data: errors, error } = await supabase
      .from('chip_interactions')
      .select('id, tipo, error_code, error_message, sucesso, created_at, destinatario')
      .eq('chip_id', chipId)
      .eq('sucesso', false)
      .gte('created_at', oneDayAgo.toISOString())
      .order('created_at', { ascending: false })
      .limit(limit)

    if (error) throw error

    // Usar ultimo_erro_msg do chip se disponivel e interacoes nao tem
    const ultimoErroChip = chip?.ultimo_erro_msg?.trim() || null

    // Mapear para formato mais legivel
    const mappedErrors = (errors as ErrorRow[] | null)?.map((e, index) => {
      // Tentar extrair mensagem de erro mais legivel
      let errorDetail = e.error_message?.trim() || ''

      // Se a mensagem esta vazia, usar ultimo erro do chip para o primeiro item
      if (!errorDetail && index === 0 && ultimoErroChip) {
        errorDetail = ultimoErroChip
      }

      // Se ainda vazio, mostrar mensagem generica com mais contexto
      if (!errorDetail) {
        errorDetail = 'Falha no envio (sem detalhes disponiveis)'
      }

      // Se for JSON HTTP, tentar parsear para extrair mensagem
      if (errorDetail.startsWith('HTTP')) {
        try {
          const jsonMatch = errorDetail.match(/\{.*\}/)
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0])
            if (parsed.response?.message) {
              const msg = parsed.response.message
              if (Array.isArray(msg) && msg[0]?.exists === false) {
                errorDetail = `Numero nao existe no WhatsApp: ${msg[0].number}`
              } else if (typeof msg === 'string') {
                errorDetail = msg
              }
            } else if (parsed.error) {
              errorDetail = parsed.error
            }
          }
        } catch {
          // Manter mensagem original
        }
      }

      return {
        id: e.id,
        tipo: e.tipo,
        errorCode: e.error_code,
        errorMessage: errorDetail,
        createdAt: e.created_at,
        destinatario: e.destinatario,
      }
    }) || []

    // Agrupar por tipo de erro para resumo
    const errorSummary: Record<string, number> = {}
    mappedErrors.forEach((e) => {
      const key = e.errorMessage.substring(0, 60)
      errorSummary[key] = (errorSummary[key] || 0) + 1
    })

    return NextResponse.json({
      errors: mappedErrors,
      total: mappedErrors.length,
      summary: Object.entries(errorSummary).map(([message, count]) => ({
        message,
        count,
      })),
      // Info adicional do chip
      chipLastError: ultimoErroChip ? {
        message: ultimoErroChip,
        code: chip?.ultimo_erro_codigo,
        timestamp: chip?.ultimo_erro_em,
      } : null,
    })
  } catch (error) {
    console.error('Error fetching chip errors:', error)
    return NextResponse.json({ error: 'Failed to fetch chip errors' }, { status: 500 })
  }
}
