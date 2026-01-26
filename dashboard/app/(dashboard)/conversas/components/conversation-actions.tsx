'use client'

import { useState } from 'react'
import { UserPlus, Bot, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
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

interface Props {
  conversationId: string
  controlledBy: string
  onRefresh: () => void
}

export function ConversationActions({ conversationId, controlledBy, onRefresh }: Props) {
  const { session, user } = useAuth()
  const [loading, setLoading] = useState(false)

  const canControl = user?.role && ['operator', 'manager', 'admin'].includes(user.role)
  const isHuman = controlledBy === 'human'

  const handleHandoff = async () => {
    if (!session?.access_token) return

    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/dashboard/conversations/${conversationId}/handoff`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })
      onRefresh()
    } catch (err) {
      console.error('Failed to handoff:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleReturn = async () => {
    if (!session?.access_token) return

    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/dashboard/conversations/${conversationId}/return-to-julia`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })
      onRefresh()
    } catch (err) {
      console.error('Failed to return to julia:', err)
    } finally {
      setLoading(false)
    }
  }

  if (!canControl) {
    return (
      <div className="border-t bg-muted/50 p-4 text-center text-sm text-muted-foreground">
        Visualizacao apenas. Voce precisa de permissao de Operador para gerenciar conversas.
      </div>
    )
  }

  return (
    <div className="flex gap-2 border-t bg-background p-4">
      {isHuman ? (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button className="flex-1" variant="default" disabled={loading}>
              <Bot className="mr-2 h-4 w-4" />
              Retornar para Julia
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Retornar para Julia?</AlertDialogTitle>
              <AlertDialogDescription>
                Julia voltara a responder automaticamente esta conversa. Certifique-se de que a
                situacao foi resolvida.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={handleReturn}>Confirmar</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      ) : (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button className="flex-1" variant="secondary" disabled={loading}>
              <UserPlus className="mr-2 h-4 w-4" />
              Transferir para Humano
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Transferir para humano?</AlertDialogTitle>
              <AlertDialogDescription>
                Julia parara de responder e um operador devera assumir via Chatwoot.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={handleHandoff}>Transferir</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      <Button variant="outline" size="icon" onClick={onRefresh} disabled={loading}>
        <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
      </Button>
    </div>
  )
}
