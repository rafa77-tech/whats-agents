'use client'

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DoctorCard, type Doctor } from './doctor-card'

interface Props {
  doctors: Doctor[]
  total: number
  page: number
  pages: number
  onPageChange: (page: number) => void
}

export function DoctorList({ doctors, total, page, pages, onPageChange }: Props) {
  if (doctors.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        Nenhum medico encontrado
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      <div className="space-y-2 p-4">
        {doctors.map((doctor) => (
          <DoctorCard key={doctor.id} doctor={doctor} />
        ))}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between border-t p-4">
          <p className="text-sm text-muted-foreground">
            Pagina {page} de {pages} ({total} medicos)
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
