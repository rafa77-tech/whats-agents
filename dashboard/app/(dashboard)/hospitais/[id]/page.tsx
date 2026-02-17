'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'
import { ArrowLeft, Building2, Check, GitMerge, Loader2, Plus, Trash2, X } from 'lucide-react'
import type { HospitalDetalhado, HospitalAlias } from '@/lib/hospitais/types'

export default function HospitalDetalhePage() {
  const params = useParams()
  const router = useRouter()
  const hospitalId = params.id as string

  const [loading, setLoading] = useState(true)
  const [hospital, setHospital] = useState<HospitalDetalhado | null>(null)
  const [saving, setSaving] = useState(false)

  // Editable fields
  const [editNome, setEditNome] = useState('')
  const [editCidade, setEditCidade] = useState('')
  const [editEstado, setEditEstado] = useState('')

  // Alias management
  const [newAlias, setNewAlias] = useState('')
  const [addingAlias, setAddingAlias] = useState(false)

  // Merge dialog
  const [mergeOpen, setMergeOpen] = useState(false)
  const [mergeSearch, setMergeSearch] = useState('')
  const [mergeResults, setMergeResults] = useState<
    Array<{ id: string; nome: string; cidade: string }>
  >([])
  const [merging, setMerging] = useState(false)
  const [selectedMerge, setSelectedMerge] = useState<{ id: string; nome: string } | null>(null)

  // Delete dialog
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const fetchHospital = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/hospitais/${hospitalId}`)
      if (!res.ok) {
        toast.error('Hospital nao encontrado')
        router.push('/hospitais')
        return
      }
      const data = await res.json()
      setHospital(data)
      setEditNome(data.nome)
      setEditCidade(data.cidade || '')
      setEditEstado(data.estado || '')
    } catch {
      toast.error('Erro ao carregar hospital')
    } finally {
      setLoading(false)
    }
  }, [hospitalId, router])

  useEffect(() => {
    fetchHospital()
  }, [fetchHospital])

  const handleSave = async () => {
    if (!hospital) return
    setSaving(true)
    try {
      const res = await fetch(`/api/hospitais/${hospitalId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome: editNome.trim(),
          cidade: editCidade.trim(),
          estado: editEstado.trim(),
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        toast.error(err.detail || 'Erro ao salvar')
        return
      }
      toast.success('Hospital atualizado')
      fetchHospital()
    } catch {
      toast.error('Erro ao salvar hospital')
    } finally {
      setSaving(false)
    }
  }

  const handleMarkReviewed = async () => {
    setSaving(true)
    try {
      const res = await fetch(`/api/hospitais/${hospitalId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ precisa_revisao: false }),
      })
      if (res.ok) {
        toast.success('Hospital marcado como revisado')
        fetchHospital()
      }
    } catch {
      toast.error('Erro ao marcar como revisado')
    } finally {
      setSaving(false)
    }
  }

  const handleAddAlias = async () => {
    if (!newAlias.trim()) return
    setAddingAlias(true)
    try {
      const res = await fetch(`/api/hospitais/${hospitalId}/aliases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alias: newAlias.trim() }),
      })
      if (res.ok) {
        toast.success('Alias adicionado')
        setNewAlias('')
        fetchHospital()
      } else {
        const err = await res.json()
        toast.error(err.detail || 'Erro ao adicionar alias')
      }
    } catch {
      toast.error('Erro ao adicionar alias')
    } finally {
      setAddingAlias(false)
    }
  }

  const handleRemoveAlias = async (aliasId: string) => {
    try {
      const res = await fetch(`/api/hospitais/${hospitalId}/aliases?alias_id=${aliasId}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        toast.success('Alias removido')
        fetchHospital()
      }
    } catch {
      toast.error('Erro ao remover alias')
    }
  }

  // Merge search
  useEffect(() => {
    if (!mergeOpen || !mergeSearch.trim()) {
      setMergeResults([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({
          search: mergeSearch.trim(),
          limit: '10',
          apenas_revisados: 'false',
        })
        const res = await fetch(`/api/hospitais?${params}`)
        const json = await res.json()
        const results = (Array.isArray(json) ? json : []).filter(
          (h: { id: string }) => h.id !== hospitalId
        )
        setMergeResults(results)
      } catch {
        setMergeResults([])
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [mergeSearch, mergeOpen, hospitalId])

  const handleMerge = async () => {
    if (!selectedMerge) return
    setMerging(true)
    try {
      const res = await fetch(`/api/hospitais/${hospitalId}/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duplicado_id: selectedMerge.id }),
      })
      if (res.ok) {
        const result = await res.json()
        toast.success(`Merge concluido: ${result.vagas_migradas || 0} vagas migradas`)
        setMergeOpen(false)
        setSelectedMerge(null)
        setMergeSearch('')
        fetchHospital()
      } else {
        const err = await res.json()
        toast.error(err.detail || 'Erro ao mesclar')
      }
    } catch {
      toast.error('Erro ao mesclar hospitais')
    } finally {
      setMerging(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      const res = await fetch(`/api/hospitais/${hospitalId}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        toast.success('Hospital deletado')
        router.push('/hospitais')
      } else {
        const err = await res.json()
        toast.error(err.detail || 'Erro ao deletar')
      }
    } catch {
      toast.error('Erro ao deletar hospital')
    } finally {
      setDeleting(false)
      setDeleteOpen(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (!hospital) {
    return null
  }

  const hasChanges =
    editNome !== hospital.nome ||
    editCidade !== (hospital.cidade || '') ||
    editEstado !== (hospital.estado || '')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push('/hospitais')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Building2 className="h-6 w-6" />
            {hospital.nome}
          </h1>
          <div className="mt-1 flex items-center gap-2">
            {hospital.precisa_revisao ? (
              <Badge
                variant="outline"
                className="border-status-warning-border text-status-warning-foreground"
              >
                Pendente de revisao
              </Badge>
            ) : (
              <Badge
                variant="outline"
                className="border-status-success-border text-status-success-foreground"
              >
                Revisado
              </Badge>
            )}
            {hospital.criado_automaticamente && <Badge variant="secondary">Auto-criado</Badge>}
            <span className="text-sm text-muted-foreground">
              {hospital.vagas_count} vagas | {hospital.aliases.length} aliases
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          {hospital.precisa_revisao && (
            <Button variant="outline" onClick={handleMarkReviewed} disabled={saving}>
              <Check className="mr-2 h-4 w-4" />
              Marcar Revisado
            </Button>
          )}
          <Button variant="outline" onClick={() => setMergeOpen(true)}>
            <GitMerge className="mr-2 h-4 w-4" />
            Merge
          </Button>
          <Button
            variant="outline"
            className="text-destructive"
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Deletar
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Info card */}
        <Card>
          <CardHeader>
            <CardTitle>Informacoes</CardTitle>
            <CardDescription>Dados do hospital</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Nome</Label>
              <Input value={editNome} onChange={(e) => setEditNome(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Cidade</Label>
                <Input value={editCidade} onChange={(e) => setEditCidade(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Estado</Label>
                <Input
                  value={editEstado}
                  onChange={(e) => setEditEstado(e.target.value)}
                  maxLength={2}
                />
              </div>
            </div>
            {hasChanges && (
              <Button onClick={handleSave} disabled={saving}>
                {saving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Salvando...
                  </>
                ) : (
                  'Salvar Alteracoes'
                )}
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Aliases card */}
        <Card>
          <CardHeader>
            <CardTitle>Aliases</CardTitle>
            <CardDescription>Nomes alternativos que mapeiam para este hospital</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="Novo alias..."
                value={newAlias}
                onChange={(e) => setNewAlias(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddAlias()}
              />
              <Button
                size="icon"
                onClick={handleAddAlias}
                disabled={addingAlias || !newAlias.trim()}
              >
                {addingAlias ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="max-h-[300px] space-y-2 overflow-y-auto">
              {hospital.aliases.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  Nenhum alias cadastrado
                </p>
              ) : (
                hospital.aliases.map((alias: HospitalAlias) => (
                  <div
                    key={alias.id}
                    className="flex items-center justify-between rounded-md border px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-medium">{alias.alias}</p>
                      <p className="text-xs text-muted-foreground">
                        {alias.origem} | confianca: {(alias.confianca * 100).toFixed(0)}%
                        {alias.confirmado && ' | confirmado'}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => handleRemoveAlias(alias.id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Merge Dialog */}
      <Dialog open={mergeOpen} onOpenChange={setMergeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mesclar Hospital</DialogTitle>
            <DialogDescription>
              Busque o hospital duplicado que sera absorvido por &quot;{hospital.nome}&quot;. Todas
              as vagas, aliases e referencias serao migradas.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <Input
              placeholder="Buscar hospital duplicado..."
              value={mergeSearch}
              onChange={(e) => {
                setMergeSearch(e.target.value)
                setSelectedMerge(null)
              }}
            />
            {selectedMerge && (
              <div className="rounded-md border border-status-info-border bg-status-info p-3">
                <p className="text-sm font-medium">{selectedMerge.nome}</p>
                <p className="text-xs text-muted-foreground">
                  Sera absorvido por &quot;{hospital.nome}&quot;
                </p>
              </div>
            )}
            {!selectedMerge && mergeResults.length > 0 && (
              <div className="max-h-[200px] space-y-1 overflow-y-auto">
                {mergeResults.map((h) => (
                  <button
                    key={h.id}
                    className="w-full rounded-md border px-3 py-2 text-left text-sm hover:bg-accent"
                    onClick={() => setSelectedMerge({ id: h.id, nome: h.nome })}
                  >
                    {h.nome}
                    {h.cidade && <span className="ml-2 text-muted-foreground">({h.cidade})</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMergeOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleMerge}
              disabled={!selectedMerge || merging}
              variant="destructive"
            >
              {merging ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Mesclando...
                </>
              ) : (
                'Confirmar Merge'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deletar Hospital</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja deletar &quot;{hospital.nome}&quot;?
              {hospital.vagas_count > 0 && (
                <span className="mt-2 block font-medium text-destructive">
                  Este hospital tem {hospital.vagas_count} vagas vinculadas e nao pode ser deletado.
                  Use a funcao de merge para mover as vagas primeiro.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? 'Deletando...' : 'Deletar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
