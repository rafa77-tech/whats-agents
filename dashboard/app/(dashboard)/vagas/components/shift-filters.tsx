'use client'

import { useState, useEffect } from 'react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuth } from '@/hooks/use-auth'

interface Filters {
  status?: string | undefined
  hospital_id?: string | undefined
  especialidade_id?: string | undefined
  date_from?: string | undefined
  date_to?: string | undefined
}

interface Option {
  id: string
  nome: string
}

interface Props {
  filters: Filters
  onApply: (filters: Filters) => void
  onClear: () => void
}

const STATUS_OPTIONS = [
  { value: 'aberta', label: 'Aberta' },
  { value: 'reservada', label: 'Reservada' },
  { value: 'confirmada', label: 'Confirmada' },
  { value: 'cancelada', label: 'Cancelada' },
  { value: 'realizada', label: 'Realizada' },
]

export function ShiftFilters({ filters, onApply, onClear }: Props) {
  const { session } = useAuth()
  const [localFilters, setLocalFilters] = useState<Filters>(filters)
  const [hospitals, setHospitals] = useState<Option[]>([])
  const [especialidades, setEspecialidades] = useState<Option[]>([])

  useEffect(() => {
    const fetchOptions = async () => {
      if (!session?.access_token) return

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      try {
        const [hospsRes, espsRes] = await Promise.all([
          fetch(`${apiUrl}/dashboard/shifts/options/hospitals`, {
            headers: { Authorization: `Bearer ${session.access_token}` },
          }),
          fetch(`${apiUrl}/dashboard/shifts/options/especialidades`, {
            headers: { Authorization: `Bearer ${session.access_token}` },
          }),
        ])

        if (hospsRes.ok) {
          const data = await hospsRes.json()
          setHospitals(data)
        }
        if (espsRes.ok) {
          const data = await espsRes.json()
          setEspecialidades(data)
        }
      } catch (err) {
        console.error('Failed to fetch filter options:', err)
      }
    }

    fetchOptions()
  }, [session?.access_token])

  const handleApply = () => {
    onApply(localFilters)
  }

  return (
    <div className="space-y-6 py-4">
      <div className="space-y-2">
        <Label>Status</Label>
        <Select
          value={localFilters.status || 'all'}
          onValueChange={(value) =>
            setLocalFilters((prev) => ({
              ...prev,
              status: value === 'all' ? undefined : value,
            }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            {STATUS_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Hospital</Label>
        <Select
          value={localFilters.hospital_id || 'all'}
          onValueChange={(value) =>
            setLocalFilters((prev) => ({
              ...prev,
              hospital_id: value === 'all' ? undefined : value,
            }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            {hospitals.map((h) => (
              <SelectItem key={h.id} value={h.id}>
                {h.nome}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Especialidade</Label>
        <Select
          value={localFilters.especialidade_id || 'all'}
          onValueChange={(value) =>
            setLocalFilters((prev) => ({
              ...prev,
              especialidade_id: value === 'all' ? undefined : value,
            }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {especialidades.map((e) => (
              <SelectItem key={e.id} value={e.id}>
                {e.nome}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Data Inicial</Label>
          <Input
            type="date"
            value={localFilters.date_from || ''}
            onChange={(e) =>
              setLocalFilters((prev) => ({
                ...prev,
                date_from: e.target.value || undefined,
              }))
            }
          />
        </div>
        <div className="space-y-2">
          <Label>Data Final</Label>
          <Input
            type="date"
            value={localFilters.date_to || ''}
            onChange={(e) =>
              setLocalFilters((prev) => ({
                ...prev,
                date_to: e.target.value || undefined,
              }))
            }
          />
        </div>
      </div>

      <div className="flex gap-2 pt-4">
        <Button variant="outline" className="flex-1" onClick={onClear}>
          Limpar
        </Button>
        <Button className="flex-1" onClick={handleApply}>
          Aplicar
        </Button>
      </div>
    </div>
  )
}
