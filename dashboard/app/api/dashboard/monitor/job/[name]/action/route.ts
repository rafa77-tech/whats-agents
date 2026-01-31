/**
 * Job Action API - Sprint 42
 *
 * Endpoint para executar acoes em jobs (run, pause, resume, delete).
 */

import { NextRequest, NextResponse } from 'next/server'

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000'

type JobAction = 'run' | 'pause' | 'resume' | 'delete'

interface ActionRequestBody {
  action: JobAction
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  try {
    const { name: jobName } = await params
    const body = (await request.json()) as ActionRequestBody
    const { action } = body

    if (!action || !['run', 'pause', 'resume', 'delete'].includes(action)) {
      return NextResponse.json(
        { success: false, message: 'Acao invalida. Use: run, pause, resume, delete' },
        { status: 400 }
      )
    }

    // Chama a API do backend para executar a acao
    const response = await fetch(`${API_BASE_URL}/api/scheduler/jobs/${jobName}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return NextResponse.json(
        {
          success: false,
          message: errorData.detail || `Falha ao executar ${action} no job`,
          jobName,
          action,
        },
        { status: response.status }
      )
    }

    const data = await response.json()

    return NextResponse.json({
      success: true,
      message: getSuccessMessage(action, jobName),
      jobName,
      action,
      data,
    })
  } catch (error) {
    console.error('Error executing job action:', error)
    return NextResponse.json(
      { success: false, message: 'Erro interno ao executar acao' },
      { status: 500 }
    )
  }
}

function getSuccessMessage(action: JobAction, jobName: string): string {
  switch (action) {
    case 'run':
      return `Job "${jobName}" iniciado com sucesso`
    case 'pause':
      return `Job "${jobName}" pausado com sucesso`
    case 'resume':
      return `Job "${jobName}" retomado com sucesso`
    case 'delete':
      return `Job "${jobName}" removido com sucesso`
    default:
      return `Acao executada com sucesso`
  }
}
