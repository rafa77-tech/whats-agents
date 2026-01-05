'use client'

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CampaignCard, type Campaign } from './campaign-card'

interface Props {
  campaigns: Campaign[]
  total: number
  page: number
  pages: number
  onPageChange: (page: number) => void
}

export function CampaignList({ campaigns, total, page, pages, onPageChange }: Props) {
  if (campaigns.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        Nenhuma campanha encontrada
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      <div className="space-y-2 p-4">
        {campaigns.map((campaign) => (
          <CampaignCard key={campaign.id} campaign={campaign} />
        ))}
      </div>

      {pages > 1 && (
        <div className="flex items-center justify-between border-t p-4">
          <p className="text-sm text-muted-foreground">
            Pagina {page} de {pages} ({total} campanhas)
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= pages}
              onClick={() => onPageChange(page + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
