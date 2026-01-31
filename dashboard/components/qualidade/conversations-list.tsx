'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Loader2, Eye, CheckCircle2, XCircle } from 'lucide-react'
import { EvaluateConversationModal } from './evaluate-conversation-modal'

interface Conversation {
  id: string
  medicoNome: string
  mensagens: number
  status: string
  avaliada: boolean
  criadaEm: string
}

export function ConversationsList() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [filterAvaliada, setFilterAvaliada] = useState<string>('false')
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)

  const fetchConversations = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (filterAvaliada !== 'all') {
        params.append('avaliada', filterAvaliada)
      }
      params.append('limit', '20')

      const res = await fetch(`/api/admin/conversas?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setConversations(
          data.conversas?.map((c: Record<string, unknown>) => ({
            id: c.id,
            medicoNome: c.medico_nome || 'Desconhecido',
            mensagens: c.total_mensagens || 0,
            status: c.status,
            avaliada: c.avaliada,
            criadaEm: c.criada_em,
          })) || []
        )
      }
    } catch {
      // Ignore errors
    } finally {
      setLoading(false)
    }
  }, [filterAvaliada])

  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  const handleCloseModal = () => {
    setSelectedConversation(null)
    fetchConversations()
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Conversas para Avaliacao</CardTitle>
              <CardDescription>{conversations.length} conversas encontradas</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="mb-4">
            <Select value={filterAvaliada} onValueChange={setFilterAvaliada}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Avaliada" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="false">Nao Avaliadas</SelectItem>
                <SelectItem value="true">Avaliadas</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : conversations.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Medico</TableHead>
                  <TableHead>Mensagens</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Data</TableHead>
                  <TableHead className="text-right">Acao</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {conversations.map((conv) => (
                  <TableRow key={conv.id}>
                    <TableCell className="font-mono text-xs">#{conv.id.slice(0, 8)}</TableCell>
                    <TableCell>{conv.medicoNome}</TableCell>
                    <TableCell>{conv.mensagens}</TableCell>
                    <TableCell>
                      {conv.avaliada ? (
                        <Badge className="bg-green-100 text-green-800">
                          <CheckCircle2 className="mr-1 h-3 w-3" />
                          Avaliada
                        </Badge>
                      ) : (
                        <Badge className="bg-yellow-100 text-yellow-800">Pendente</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(conv.criadaEm).toLocaleDateString('pt-BR')}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedConversation(conv.id)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="py-8 text-center text-gray-500">
              <XCircle className="mx-auto h-8 w-8 text-gray-300" />
              <p className="mt-2">Nenhuma conversa encontrada</p>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedConversation && (
        <EvaluateConversationModal
          conversationId={selectedConversation}
          onClose={handleCloseModal}
        />
      )}
    </>
  )
}
