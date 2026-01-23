import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

/**
 * GET /api/filtros
 * Retorna opcoes de filtros dinamicos para campanhas
 * - especialidades: lista de especialidades com contagem de medicos
 * - estados: lista de estados (UF) com contagem de medicos
 */
export async function GET() {
  try {
    const supabase = await createClient()

    // Buscar especialidades distintas com contagem
    const { data: especialidadesData, error: espError } = await supabase
      .from('clientes')
      .select('especialidade')
      .not('especialidade', 'is', null)
      .neq('especialidade', '')
      .is('deleted_at', null)
      .eq('opt_out', false)

    if (espError) {
      console.error('Erro ao buscar especialidades:', espError)
      return NextResponse.json({ detail: 'Erro ao buscar filtros' }, { status: 500 })
    }

    // Agregar especialidades manualmente (Supabase não suporta GROUP BY diretamente)
    const especialidadesMap = new Map<string, number>()
    especialidadesData?.forEach((row) => {
      const esp = row.especialidade as string
      if (esp && esp !== 'Teste') {
        especialidadesMap.set(esp, (especialidadesMap.get(esp) || 0) + 1)
      }
    })

    const especialidades = Array.from(especialidadesMap.entries())
      .map(([value, count]) => ({ value, label: value, count }))
      .sort((a, b) => b.count - a.count)

    // Buscar estados distintos com contagem
    const { data: estadosData, error: estError } = await supabase
      .from('clientes')
      .select('estado')
      .not('estado', 'is', null)
      .neq('estado', '')
      .is('deleted_at', null)
      .eq('opt_out', false)

    if (estError) {
      console.error('Erro ao buscar estados:', estError)
      return NextResponse.json({ detail: 'Erro ao buscar filtros' }, { status: 500 })
    }

    // Agregar estados manualmente
    const estadosMap = new Map<string, number>()
    estadosData?.forEach((row) => {
      const est = row.estado as string
      if (est) {
        estadosMap.set(est, (estadosMap.get(est) || 0) + 1)
      }
    })

    // Mapa de UF para nome completo
    const nomeEstados: Record<string, string> = {
      AC: 'Acre',
      AL: 'Alagoas',
      AP: 'Amapa',
      AM: 'Amazonas',
      BA: 'Bahia',
      CE: 'Ceara',
      DF: 'Distrito Federal',
      ES: 'Espirito Santo',
      GO: 'Goias',
      MA: 'Maranhao',
      MT: 'Mato Grosso',
      MS: 'Mato Grosso do Sul',
      MG: 'Minas Gerais',
      PA: 'Para',
      PB: 'Paraiba',
      PR: 'Parana',
      PE: 'Pernambuco',
      PI: 'Piaui',
      RJ: 'Rio de Janeiro',
      RN: 'Rio Grande do Norte',
      RS: 'Rio Grande do Sul',
      RO: 'Rondonia',
      RR: 'Roraima',
      SC: 'Santa Catarina',
      SP: 'Sao Paulo',
      SE: 'Sergipe',
      TO: 'Tocantins',
    }

    const estados = Array.from(estadosMap.entries())
      .map(([value, count]) => ({
        value,
        label: nomeEstados[value] || value,
        count,
      }))
      .sort((a, b) => b.count - a.count)

    return NextResponse.json({
      especialidades,
      estados,
      totalMedicos: especialidadesData?.length || 0,
    })
  } catch (error) {
    console.error('Erro ao buscar filtros:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
