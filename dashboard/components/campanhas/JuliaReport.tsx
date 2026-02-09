'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { MessageSquare, RefreshCw, Clock, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface JuliaReportProps {
  report: string | null
  generatedAt: string | null
  cached: boolean
  tokensUsed: number
  loading?: boolean
  onRefresh?: () => void
  refreshing?: boolean
}

export function JuliaReport({
  report,
  generatedAt,
  cached,
  tokensUsed,
  loading,
  onRefresh,
  refreshing,
}: JuliaReportProps) {
  const [expanded, setExpanded] = useState(true)

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-status-warning-solid" />
            Relatorio da Julia
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!report) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-status-warning-solid" />
            Relatorio da Julia
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center">
            <MessageSquare className="mx-auto mb-4 h-12 w-12 text-gray-300" />
            <p className="text-gray-500">
              Nenhum relatorio disponivel ainda.
            </p>
            <p className="mt-1 text-sm text-gray-400">
              O relatorio sera gerado automaticamente quando houver respostas suficientes.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-status-warning-solid" />
            Relatorio da Julia
          </CardTitle>
          <CardDescription className="flex items-center gap-2">
            {generatedAt && (
              <>
                <Clock className="h-3 w-3" />
                {formatDate(generatedAt)}
              </>
            )}
            {cached && (
              <Badge variant="outline" className="text-xs">
                Cache
              </Badge>
            )}
          </CardDescription>
        </div>
        {onRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Regenerar
          </Button>
        )}
      </CardHeader>
      <CardContent>
        <div
          className={`prose prose-sm max-w-none dark:prose-invert ${
            expanded ? '' : 'line-clamp-6'
          }`}
        >
          <ReactMarkdown
            components={{
              h2: ({ children }) => (
                <h2 className="mb-3 mt-6 flex items-center gap-2 text-lg font-semibold first:mt-0">
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="mb-2 mt-4 text-base font-semibold">{children}</h3>
              ),
              ul: ({ children }) => (
                <ul className="mb-4 list-inside list-disc space-y-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="mb-4 list-inside list-decimal space-y-1">{children}</ol>
              ),
              li: ({ children }) => (
                <li className="text-sm text-gray-700 dark:text-gray-300">{children}</li>
              ),
              p: ({ children }) => (
                <p className="mb-3 text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                  {children}
                </p>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-gray-900 dark:text-gray-100">
                  {children}
                </strong>
              ),
            }}
          >
            {report}
          </ReactMarkdown>
        </div>

        {report.length > 500 && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-2 w-full"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? 'Ver menos' : 'Ver mais'}
          </Button>
        )}

        {tokensUsed > 0 && (
          <p className="mt-4 text-right text-xs text-muted-foreground">
            {tokensUsed} tokens utilizados
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function formatDate(isoString: string): string {
  try {
    const date = new Date(isoString)
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoString
  }
}
