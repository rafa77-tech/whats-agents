'use client'

import { AuditItem } from './audit-item'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight, FileQuestion } from 'lucide-react'

interface AuditLog {
  id: string
  action: string
  actor_email: string
  actor_role: string
  details: Record<string, unknown>
  created_at: string
}

interface Props {
  logs: AuditLog[]
  total: number
  page: number
  pages: number
  onPageChange: (page: number) => void
}

export function AuditList({ logs, total, page, pages, onPageChange }: Props) {
  if (logs.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
        <FileQuestion className="mb-4 h-12 w-12" />
        <p className="text-lg font-medium">Nenhum log encontrado</p>
        <p className="text-sm">Ajuste os filtros ou aguarde novas acoes</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* List */}
      <div className="flex-1">
        {logs.map((log) => (
          <AuditItem key={log.id} log={log} />
        ))}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between border-t p-4">
        <p className="text-sm text-muted-foreground">
          {total} {total === 1 ? 'registro' : 'registros'}
        </p>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <span className="text-sm">
            {page} / {pages}
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
