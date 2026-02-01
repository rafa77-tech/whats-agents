/**
 * Assign Doctor Dialog Component
 *
 * Dialog for searching and assigning a doctor to a shift.
 */

import { Search, Loader2, User } from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import type { Doctor } from '@/lib/vagas'

interface AssignDoctorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  search: string
  onSearchChange: (value: string) => void
  doctors: Doctor[]
  searching: boolean
  assigning: boolean
  onAssign: (doctorId: string) => void
}

export function AssignDoctorDialog({
  open,
  onOpenChange,
  search,
  onSearchChange,
  doctors,
  searching,
  assigning,
  onAssign,
}: AssignDoctorDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Atribuir Medico</DialogTitle>
          <DialogDescription>
            Busque e selecione um medico para atribuir a esta vaga.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Buscar por nome, telefone ou CRM..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10"
            />
          </div>

          <div className="max-h-64 space-y-2 overflow-auto">
            {searching && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            )}

            {!searching && search.length >= 2 && doctors.length === 0 && (
              <p className="py-4 text-center text-sm text-muted-foreground">
                Nenhum medico encontrado
              </p>
            )}

            {!searching &&
              doctors.map((doctor) => (
                <button
                  key={doctor.id}
                  onClick={() => onAssign(doctor.id)}
                  disabled={assigning}
                  className="flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent disabled:opacity-50"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                    <User className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{doctor.nome}</p>
                    <p className="truncate text-sm text-muted-foreground">
                      {doctor.telefone}
                      {doctor.especialidade && ` - ${doctor.especialidade}`}
                    </p>
                  </div>
                  {assigning && <Loader2 className="h-4 w-4 animate-spin" />}
                </button>
              ))}

            {!searching && search.length < 2 && (
              <p className="py-4 text-center text-sm text-muted-foreground">
                Digite ao menos 2 caracteres para buscar
              </p>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
