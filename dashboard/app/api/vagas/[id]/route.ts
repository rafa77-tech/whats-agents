/**
 * API: GET/PATCH/DELETE /api/vagas/[id]
 *
 * Gerencia uma vaga especifica com validacao Zod.
 */

import { NextRequest, NextResponse } from 'next/server'
import { ZodError } from 'zod'
import { createAdminClient } from '@/lib/supabase/admin'
import { parseShiftUpdateBody } from '@/lib/vagas'

export const dynamic = 'force-dynamic'

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    const { data: vaga, error } = await supabase
      .from('vagas')
      .select(
        `
        id,
        data,
        hora_inicio,
        hora_fim,
        valor,
        status,
        created_at,
        updated_at,
        hospital_id,
        especialidade_id,
        setor_id,
        cliente_id,
        contato_nome,
        contato_whatsapp,
        hospitais!inner(id, nome),
        especialidades!inner(id, nome),
        setores(id, nome),
        clientes(id, primeiro_nome, sobrenome)
      `
      )
      .eq('id', id)
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        return NextResponse.json({ error: 'Vaga nao encontrada' }, { status: 404 })
      }
      console.error('Erro ao buscar vaga:', error)
      throw error
    }

    const hospital = vaga.hospitais as unknown as { id: string; nome: string } | null
    const especialidade = vaga.especialidades as unknown as { id: string; nome: string } | null
    const setor = vaga.setores as unknown as { id: string; nome: string } | null
    const cliente = vaga.clientes as unknown as {
      id: string
      primeiro_nome: string | null
      sobrenome: string | null
    } | null

    const shift = {
      id: vaga.id,
      hospital: hospital?.nome || 'N/A',
      hospital_id: vaga.hospital_id || '',
      especialidade: especialidade?.nome || 'N/A',
      especialidade_id: vaga.especialidade_id || '',
      setor: setor?.nome || null,
      setor_id: vaga.setor_id || null,
      data: vaga.data,
      hora_inicio: vaga.hora_inicio,
      hora_fim: vaga.hora_fim,
      valor: vaga.valor || 0,
      status: vaga.status || 'aberta',
      cliente_id: vaga.cliente_id || null,
      cliente_nome: cliente
        ? [cliente.primeiro_nome, cliente.sobrenome].filter(Boolean).join(' ')
        : null,
      created_at: vaga.created_at,
      updated_at: vaga.updated_at,
      contato_nome: vaga.contato_nome || null,
      contato_whatsapp: vaga.contato_whatsapp || null,
    }

    return NextResponse.json(shift)
  } catch (error) {
    console.error('Erro ao buscar vaga:', error)
    return NextResponse.json({ error: 'Erro ao buscar vaga' }, { status: 500 })
  }
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const rawBody = await request.json()

    // Sanitize: convert empty strings to null before validation
    const body = Object.fromEntries(
      Object.entries(rawBody).map(([k, v]) => [k, v === '' ? null : v])
    )

    // Validate body with Zod
    let validatedBody
    try {
      validatedBody = parseShiftUpdateBody(body)
    } catch (error) {
      if (error instanceof ZodError) {
        return NextResponse.json(
          { error: 'Dados invalidos', details: error.errors },
          { status: 400 }
        )
      }
      throw error
    }

    const {
      cliente_id,
      status,
      hospital_id,
      especialidade_id,
      data,
      hora_inicio,
      hora_fim,
      valor,
      contato_nome,
      contato_whatsapp,
    } = validatedBody
    const supabase = createAdminClient()

    const updateData: Record<string, unknown> = {
      updated_at: new Date().toISOString(),
    }

    if (cliente_id !== undefined) {
      updateData.cliente_id = cliente_id
      // If assigning a doctor, change status to reservada
      if (cliente_id) {
        updateData.status = 'reservada'
      }
    }

    if (status !== undefined) updateData.status = status
    if (hospital_id !== undefined) updateData.hospital_id = hospital_id
    if (especialidade_id !== undefined) updateData.especialidade_id = especialidade_id
    if (data !== undefined) updateData.data = data
    if (hora_inicio !== undefined) updateData.hora_inicio = hora_inicio
    if (hora_fim !== undefined) updateData.hora_fim = hora_fim
    if (valor !== undefined) updateData.valor = valor
    if (contato_nome !== undefined) updateData.contato_nome = contato_nome
    if (contato_whatsapp !== undefined) updateData.contato_whatsapp = contato_whatsapp

    const { error } = await supabase.from('vagas').update(updateData).eq('id', id)

    if (error) {
      console.error('Erro ao atualizar vaga:', error)
      throw error
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao atualizar vaga:', error)
    return NextResponse.json({ error: 'Erro ao atualizar vaga' }, { status: 500 })
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    const { error } = await supabase.from('vagas').delete().eq('id', id)

    if (error) {
      console.error('Erro ao deletar vaga:', error)
      throw error
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao deletar vaga:', error)
    return NextResponse.json({ error: 'Erro ao deletar vaga' }, { status: 500 })
  }
}
