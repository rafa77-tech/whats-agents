'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Ban, MessageCircle, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { useAuth } from '@/hooks/use-auth'

interface Doctor {
  id: string
  nome: string
  stage_jornada?: string
  opt_out: boolean
}

interface Props {
  doctor: Doctor
  onRefresh: () => void
}

const FUNNEL_STATUSES = [
  { value: 'novo', label: 'Novo' },
  { value: 'respondeu', label: 'Respondeu' },
  { value: 'negociando', label: 'Negociando' },
  { value: 'convertido', label: 'Convertido' },
  { value: 'perdido', label: 'Perdido' },
]

export function DoctorActions({ doctor, onRefresh }: Props) {
  const router = useRouter()
  const { session, user } = useAuth()
  const [loading, setLoading] = useState(false)

  const canEdit = user?.role && ['operator', 'manager', 'admin'].includes(user.role)

  const handleFunnelChange = async (status: string) => {
    if (!session?.access_token) return

    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/dashboard/doctors/${doctor.id}/funnel`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ status }),
      })
      onRefresh()
    } catch (err) {
      console.error('Failed to update funnel:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleOptOutToggle = async () => {
    if (!session?.access_token) return

    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/dashboard/doctors/${doctor.id}/opt-out`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ opt_out: !doctor.opt_out }),
      })
      onRefresh()
    } catch (err) {
      console.error('Failed to toggle opt-out:', err)
    } finally {
      setLoading(false)
    }
  }

  if (!canEdit) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Voce precisa de permissao de Operador para realizar acoes
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Status do Funil */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Status do Funil</CardTitle>
          <CardDescription>Posicao do medico no pipeline de vendas</CardDescription>
        </CardHeader>
        <CardContent>
          <Select
            value={doctor.stage_jornada || 'novo'}
            onValueChange={handleFunnelChange}
            disabled={loading}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FUNNEL_STATUSES.map((status) => (
                <SelectItem key={status.value} value={status.value}>
                  {status.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Opt-out */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Preferencias de Contato</CardTitle>
          <CardDescription>Gerenciar preferencias de comunicacao</CardDescription>
        </CardHeader>
        <CardContent>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant={doctor.opt_out ? 'default' : 'destructive'}
                className="w-full"
                disabled={loading}
              >
                {doctor.opt_out ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Reativar Contato
                  </>
                ) : (
                  <>
                    <Ban className="mr-2 h-4 w-4" />
                    Marcar Opt-out
                  </>
                )}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>
                  {doctor.opt_out ? 'Reativar contato?' : 'Marcar como opt-out?'}
                </AlertDialogTitle>
                <AlertDialogDescription>
                  {doctor.opt_out
                    ? 'O medico voltara a receber mensagens da Julia.'
                    : 'O medico nao recebera mais mensagens automaticas da Julia.'}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancelar</AlertDialogCancel>
                <AlertDialogAction onClick={handleOptOutToggle}>Confirmar</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>

      {/* Ver Conversa */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Conversa</CardTitle>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => {
              // TODO: Navigate to active conversation or create new
              router.push('/conversas')
            }}
          >
            <MessageCircle className="mr-2 h-4 w-4" />
            Ver Conversas
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
