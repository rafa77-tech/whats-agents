'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Briefcase,
  MapPin,
  Building2,
  Stethoscope,
  Calendar,
  Clock,
  DollarSign,
  Users,
  ExternalLink,
} from 'lucide-react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { MensagemOriginalModal } from '@/components/mensagem-original-modal'

interface GrupoComVagas {
  id: string
  nome: string
  vagas_importadas: number
}

interface MensagemOriginalData {
  texto: string
  sender_nome: string
  created_at: string
}

interface VagaHoje {
  id: string
  hospital: string
  especialidade: string
  valor: number | null
  data: string | null
  periodo: string | null
  grupo: string
  created_at: string
  mensagem_original: MensagemOriginalData | null
}

interface VagasHojeData {
  grupos: GrupoComVagas[]
  vagas: VagaHoje[]
}

function formatValor(valor: number | null): string {
  if (!valor) return '-'
  return valor.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  })
}

function formatData(data: string | null): string {
  if (!data) return '-'
  try {
    return format(new Date(data + 'T12:00:00'), 'dd/MM', { locale: ptBR })
  } catch {
    return data
  }
}

function formatDataFull(data: string | null): string {
  if (!data) return '-'
  try {
    return format(new Date(data + 'T12:00:00'), "dd 'de' MMMM, yyyy", { locale: ptBR })
  } catch {
    return data
  }
}

function formatHora(createdAt: string): string {
  try {
    return format(new Date(createdAt), 'HH:mm')
  } catch {
    return '-'
  }
}

function formatHoraFull(createdAt: string): string {
  try {
    return format(new Date(createdAt), "dd/MM/yyyy 'as' HH:mm", { locale: ptBR })
  } catch {
    return '-'
  }
}

const PERIODO_LABELS: Record<string, string> = {
  diurno: 'Diurno',
  noturno: 'Noturno',
  '24h': '24h',
}

// =============================================================================
// DETAIL ROW
// =============================================================================

function DetailRow({
  icon: Icon,
  label,
  value,
  onClick,
}: {
  icon: React.ElementType
  label: string
  value: string
  onClick?: () => void
}) {
  return (
    <div className="flex items-start gap-3 py-2">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        {onClick ? (
          <button
            type="button"
            onClick={onClick}
            className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
          >
            {value}
            <ExternalLink className="h-3 w-3" />
          </button>
        ) : (
          <p className="text-sm font-medium">{value}</p>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function VagasHoje() {
  const [data, setData] = useState<VagasHojeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedGrupo, setSelectedGrupo] = useState<string>('todos')
  const [selectedVaga, setSelectedVaga] = useState<VagaHoje | null>(null)
  const [showMsgModal, setShowMsgModal] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/market-intelligence/vagas-hoje')
      if (res.ok) {
        setData(await res.json())
      }
    } catch (err) {
      console.error('Erro ao carregar vagas hoje:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const vagasFiltradas =
    selectedGrupo === 'todos'
      ? (data?.vagas ?? [])
      : (data?.vagas ?? []).filter((v) => v.grupo === selectedGrupo)

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[120px]" />
        <Skeleton className="h-[300px]" />
      </div>
    )
  }

  if (!data) return null

  const totalImportadasHoje = data.vagas.length

  return (
    <div className="space-y-4">
      {/* Dropdown de Grupos */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <MapPin className="h-4 w-4" />
              Vagas por Grupo
              <Badge variant="secondary" className="ml-1">
                {data.grupos.length} grupos
              </Badge>
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <Select value={selectedGrupo} onValueChange={setSelectedGrupo}>
            <SelectTrigger>
              <SelectValue placeholder="Selecione um grupo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todos">
                Todos os grupos ({data.grupos.reduce((acc, g) => acc + g.vagas_importadas, 0)} vagas
                em 30d)
              </SelectItem>
              {data.grupos.map((grupo) => (
                <SelectItem key={grupo.id} value={grupo.nome}>
                  {grupo.nome} ({grupo.vagas_importadas})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Tabela de Vagas Importadas Hoje */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Briefcase className="h-4 w-4" />
            Vagas Importadas Hoje
            <Badge variant="secondary" className="ml-1">
              {vagasFiltradas.length}
              {selectedGrupo !== 'todos' ? ` de ${totalImportadasHoje}` : ''}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {vagasFiltradas.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Nenhuma vaga importada hoje
              {selectedGrupo !== 'todos' ? ' para este grupo' : ''}.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Hora</TableHead>
                    <TableHead>Hospital</TableHead>
                    <TableHead>Especialidade</TableHead>
                    <TableHead>Data</TableHead>
                    <TableHead>Periodo</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                    <TableHead>Grupo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {vagasFiltradas.map((vaga) => (
                    <TableRow
                      key={vaga.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => setSelectedVaga(vaga)}
                    >
                      <TableCell className="text-muted-foreground">
                        {formatHora(vaga.created_at)}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate font-medium">
                        {vaga.hospital}
                      </TableCell>
                      <TableCell>{vaga.especialidade}</TableCell>
                      <TableCell>{formatData(vaga.data)}</TableCell>
                      <TableCell>
                        {vaga.periodo ? (PERIODO_LABELS[vaga.periodo] ?? vaga.periodo) : '-'}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatValor(vaga.valor)}
                      </TableCell>
                      <TableCell className="max-w-[180px] truncate text-muted-foreground">
                        {vaga.grupo}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal de Detalhes da Vaga */}
      <Dialog open={selectedVaga !== null} onOpenChange={(open) => !open && setSelectedVaga(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" />
              Detalhes da Vaga
            </DialogTitle>
          </DialogHeader>
          {selectedVaga && (
            <div className="divide-y">
              <DetailRow icon={Building2} label="Hospital" value={selectedVaga.hospital} />
              <DetailRow
                icon={Stethoscope}
                label="Especialidade"
                value={selectedVaga.especialidade}
              />
              <DetailRow
                icon={Calendar}
                label="Data do Plantao"
                value={formatDataFull(selectedVaga.data)}
              />
              <DetailRow
                icon={Clock}
                label="Periodo"
                value={
                  selectedVaga.periodo
                    ? (PERIODO_LABELS[selectedVaga.periodo] ?? selectedVaga.periodo)
                    : 'Nao informado'
                }
              />
              <DetailRow icon={DollarSign} label="Valor" value={formatValor(selectedVaga.valor)} />
              {selectedVaga.mensagem_original ? (
                <DetailRow
                  icon={Users}
                  label="Grupo de Origem"
                  value={selectedVaga.grupo}
                  onClick={() => setShowMsgModal(true)}
                />
              ) : (
                <DetailRow icon={Users} label="Grupo de Origem" value={selectedVaga.grupo} />
              )}
              <DetailRow
                icon={Clock}
                label="Importada em"
                value={formatHoraFull(selectedVaga.created_at)}
              />
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Modal de Mensagem Original */}
      {selectedVaga?.mensagem_original && (
        <MensagemOriginalModal
          open={showMsgModal}
          onOpenChange={setShowMsgModal}
          grupoNome={selectedVaga.grupo}
          mensagem={selectedVaga.mensagem_original}
        />
      )}
    </div>
  )
}
