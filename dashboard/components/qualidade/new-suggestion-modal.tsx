'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2 } from 'lucide-react'

interface NewSuggestionModalProps {
  onClose: () => void
  onCreated: () => void
}

const TIPOS = [
  { value: 'tom', label: 'Tom de voz' },
  { value: 'resposta', label: 'Tipo de resposta' },
  { value: 'abertura', label: 'Mensagem de abertura' },
  { value: 'objecao', label: 'Tratamento de objecao' },
]

export function NewSuggestionModal({ onClose, onCreated }: NewSuggestionModalProps) {
  const [tipo, setTipo] = useState('')
  const [descricao, setDescricao] = useState('')
  const [exemplos, setExemplos] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async () => {
    if (!tipo || !descricao) return

    setSaving(true)
    try {
      await fetch('/api/admin/sugestoes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tipo,
          descricao,
          exemplos: exemplos || undefined,
        }),
      })
      onCreated()
    } catch {
      // Ignore errors
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Nova Sugestao</DialogTitle>
          <DialogDescription>Crie uma sugestao de melhoria para os prompts</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label htmlFor="tipo">Tipo</Label>
            <Select value={tipo} onValueChange={setTipo}>
              <SelectTrigger>
                <SelectValue placeholder="Selecione o tipo" />
              </SelectTrigger>
              <SelectContent>
                {TIPOS.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="descricao">Descricao</Label>
            <Textarea
              id="descricao"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Descreva a sugestao de melhoria..."
              rows={3}
            />
          </div>

          <div>
            <Label htmlFor="exemplos">Exemplos (opcional)</Label>
            <Textarea
              id="exemplos"
              value={exemplos}
              onChange={(e) => setExemplos(e.target.value)}
              placeholder="Exemplos de como implementar..."
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={saving || !tipo || !descricao}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Criando...
              </>
            ) : (
              'Criar Sugestao'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
