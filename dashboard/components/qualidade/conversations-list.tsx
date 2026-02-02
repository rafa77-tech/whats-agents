'use client'

import { useState } from 'react'
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
import {
  useConversations,
  formatDateBR,
  formatShortId,
  CONVERSATION_FILTER_OPTIONS,
} from '@/lib/qualidade'
import type { ConversationFilter } from '@/lib/qualidade'
import { EvaluateConversationModal } from './evaluate-conversation-modal'

export function ConversationsList() {
  const [filterAvaliada, setFilterAvaliada] = useState<ConversationFilter>('false')
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)

  const { conversations, loading, refresh } = useConversations(filterAvaliada)

  const handleCloseModal = () => {
    setSelectedConversation(null)
    refresh()
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
            <Select
              value={filterAvaliada}
              onValueChange={(value) => setFilterAvaliada(value as ConversationFilter)}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Avaliada" />
              </SelectTrigger>
              <SelectContent>
                {CONVERSATION_FILTER_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
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
                    <TableCell className="font-mono text-xs">{formatShortId(conv.id)}</TableCell>
                    <TableCell>{conv.medicoNome}</TableCell>
                    <TableCell>{conv.mensagens}</TableCell>
                    <TableCell>
                      {conv.avaliada ? (
                        <Badge className="bg-status-success text-status-success-foreground">
                          <CheckCircle2 className="mr-1 h-3 w-3" />
                          Avaliada
                        </Badge>
                      ) : (
                        <Badge className="bg-status-warning text-status-warning-foreground">Pendente</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {formatDateBR(conv.criadaEm)}
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
