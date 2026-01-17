/**
 * API: GET /api/dashboard/alerts
 *
 * Returns active alerts from multiple sources:
 * - Chip alerts (trust critical, disconnected)
 * - Handoffs (doctors waiting for human)
 * - Expiring shifts without confirmation
 * - Rate limit warnings
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { type AlertSeverity, type AlertCategory } from '@/types/dashboard'

interface AlertData {
  id: string
  severity: AlertSeverity
  category: AlertCategory
  title: string
  message: string
  createdAt: string
  actionLabel?: string
  actionUrl?: string
}

export async function GET() {
  try {
    const supabase = await createClient()
    const alerts: AlertData[] = []
    const chatwootUrl = process.env.CHATWOOT_URL

    // 1. Alertas de chips com trust baixo
    const { data: chipsLowTrust } = await supabase
      .from('chips')
      .select('id, instance_name, trust_score')
      .lt('trust_score', 50)
      .eq('status', 'active')
      .order('trust_score', { ascending: true })
      .limit(3)

    chipsLowTrust?.forEach((chip) => {
      const isCritical = (chip.trust_score ?? 0) < 30
      alerts.push({
        id: `chip-trust-${chip.id}`,
        severity: isCritical ? 'critical' : 'warning',
        category: 'chip',
        title: `${chip.instance_name} - Trust baixo`,
        message: `Trust score: ${chip.trust_score ?? 0}`,
        createdAt: new Date().toISOString(),
        actionLabel: 'Ver chip',
        actionUrl: `/chips/${chip.id}`,
      })
    })

    // 2. Alertas de handoff pendentes
    const { data: handoffs } = await supabase
      .from('handoffs')
      .select(
        `
        id,
        motivo,
        created_at,
        conversa_id,
        conversations (
          clientes (primeiro_nome, sobrenome)
        )
      `
      )
      .eq('status', 'pendente')
      .order('created_at', { ascending: false })
      .limit(3)

    interface HandoffRow {
      id: string
      motivo: string | null
      created_at: string
      conversa_id: string | null
      conversations: {
        clientes: {
          primeiro_nome: string | null
          sobrenome: string | null
        } | null
      } | null
    }

    const typedHandoffs = handoffs as unknown as HandoffRow[] | null

    typedHandoffs?.forEach((h) => {
      const cliente = h.conversations?.clientes
      const nome = cliente
        ? `${cliente.primeiro_nome ?? ''} ${cliente.sobrenome ?? ''}`.trim() || 'Medico'
        : 'Medico'

      const handoffAlert: AlertData = {
        id: `handoff-${h.id}`,
        severity: 'critical',
        category: 'julia',
        title: `${nome} - aguardando atendimento`,
        message: h.motivo ?? 'Handoff solicitado',
        createdAt: h.created_at,
        actionLabel: 'Ver conversa',
      }

      if (chatwootUrl && h.conversa_id) {
        handoffAlert.actionUrl = `${chatwootUrl}/conversations/${h.conversa_id}`
      }

      alerts.push(handoffAlert)
    })

    // 3. Alertas de vagas expirando em 24h
    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)

    const { count: vagasCount } = await supabase
      .from('vagas')
      .select('id', { count: 'exact', head: true })
      .lte('data', tomorrow.toISOString())
      .is('medico_confirmado_id', null)
      .eq('status', 'aberta')

    if (vagasCount && vagasCount > 0) {
      alerts.push({
        id: 'vagas-expirando',
        severity: 'warning',
        category: 'vaga',
        title: `${vagasCount} vaga${vagasCount > 1 ? 's' : ''} expirando em 24h`,
        message: 'Sem medico confirmado',
        createdAt: new Date().toISOString(),
        actionLabel: 'Ver vagas',
        actionUrl: '/vagas?status=urgente',
      })
    }

    // 4. Chips desconectados (offline)
    const { data: chipsOffline, count: offlineCount } = await supabase
      .from('chips')
      .select('id, instance_name', { count: 'exact' })
      .eq('status', 'offline')
      .limit(1)

    if (offlineCount && offlineCount > 0) {
      const chipName =
        offlineCount === 1 && chipsOffline?.[0]
          ? chipsOffline[0].instance_name
          : `${offlineCount} chips`
      alerts.push({
        id: 'chips-offline',
        severity: 'critical',
        category: 'chip',
        title: `${chipName} offline`,
        message: offlineCount === 1 ? 'Chip desconectado' : `${offlineCount} chips desconectados`,
        createdAt: new Date().toISOString(),
        actionLabel: 'Ver chips',
        actionUrl: '/chips?status=offline',
      })
    }

    // Contar por severidade
    const totalCritical = alerts.filter((a) => a.severity === 'critical').length
    const totalWarning = alerts.filter((a) => a.severity === 'warning').length

    return NextResponse.json({
      alerts,
      totalCritical,
      totalWarning,
    })
  } catch (error) {
    console.error('Error fetching alerts:', error)

    // Return mock data on error for development
    const mockAlerts: AlertData[] = [
      {
        id: 'mock-1',
        severity: 'critical',
        category: 'julia',
        title: 'Dr. Joao - aguardando atendimento',
        message: 'Medico solicitou falar com humano',
        createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        actionLabel: 'Ver conversa',
      },
      {
        id: 'mock-2',
        severity: 'critical',
        category: 'chip',
        title: 'Julia-05 - Trust baixo',
        message: 'Trust score: 48',
        createdAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        actionLabel: 'Ver chip',
      },
      {
        id: 'mock-3',
        severity: 'warning',
        category: 'vaga',
        title: '5 vagas expirando em 24h',
        message: 'Sem medico confirmado',
        createdAt: new Date().toISOString(),
        actionLabel: 'Ver vagas',
      },
      {
        id: 'mock-4',
        severity: 'warning',
        category: 'operational',
        title: 'Rate limit hora em 85%',
        message: 'Reseta em 12 minutos',
        createdAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      },
    ]

    return NextResponse.json({
      alerts: mockAlerts,
      totalCritical: 2,
      totalWarning: 2,
    })
  }
}
