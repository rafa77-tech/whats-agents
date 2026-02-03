'use client'

import { useState, useCallback, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Upload, Download, Loader2, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { toast } from '@/hooks/use-toast'
import { useImportLinks, isValidFileExtension } from '@/lib/group-entry'

interface ImportLinksModalProps {
  onClose: () => void
  onImport: () => void
}

export function ImportLinksModal({ onClose, onImport }: ImportLinksModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const { uploading, result, error, uploadFile, reset } = useImportLinks()

  // Show error toast
  useEffect(() => {
    if (error) {
      toast({
        title: 'Erro na importacao',
        description: error,
        variant: 'destructive',
      })
    }
  }, [error])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (isValidFileExtension(droppedFile.name)) {
        setFile(droppedFile)
      } else {
        toast({
          title: 'Arquivo invalido',
          description: 'Selecione um arquivo CSV ou Excel (.xlsx)',
          variant: 'destructive',
        })
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (isValidFileExtension(selectedFile.name)) {
        setFile(selectedFile)
      } else {
        toast({
          title: 'Arquivo invalido',
          description: 'Selecione um arquivo CSV ou Excel (.xlsx)',
          variant: 'destructive',
        })
      }
    }
  }

  const handleUpload = async () => {
    if (!file) return

    const success = await uploadFile(file)
    if (success) {
      toast({
        title: 'Arquivo processado',
        description: 'Verifique os resultados abaixo',
      })
    }
  }

  const handleConfirmImport = () => {
    onImport()
  }

  const handleRemoveFile = () => {
    setFile(null)
    reset()
  }

  const downloadTemplate = () => {
    const csv = 'link,categoria\nhttps://chat.whatsapp.com/exemplo,medicos\n'
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'template_links.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Importar Links</DialogTitle>
          <DialogDescription>Importe links de grupos via arquivo CSV ou Excel</DialogDescription>
        </DialogHeader>

        {!result ? (
          <div className="space-y-4">
            {/* Drop zone */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={cn(
                'flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors',
                dragActive
                  ? 'border-status-info-solid bg-status-info'
                  : 'border-muted-foreground/50',
                file && 'border-status-success-solid bg-status-success'
              )}
            >
              {file ? (
                <>
                  <CheckCircle2 className="h-8 w-8 text-status-success-foreground" />
                  <p className="mt-2 text-sm font-medium text-status-success-foreground">
                    {file.name}
                  </p>
                  <Button variant="link" size="sm" onClick={handleRemoveFile}>
                    Remover
                  </Button>
                </>
              ) : (
                <>
                  <Upload className="h-8 w-8 text-muted-foreground/70" />
                  <p className="mt-2 text-sm text-foreground/80">
                    Arraste um arquivo CSV ou Excel aqui
                  </p>
                  <label className="mt-2 cursor-pointer">
                    <span className="text-sm text-status-info-foreground hover:underline">
                      ou selecione um arquivo
                    </span>
                    <input
                      type="file"
                      accept=".csv,.xlsx"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                  </label>
                </>
              )}
            </div>

            {/* Format info */}
            <div className="rounded-lg bg-muted p-3 text-sm">
              <p className="font-medium text-foreground">Formato esperado:</p>
              <code className="text-xs text-foreground/80">
                link, categoria (opcional)
                <br />
                https://chat.whatsapp.com/xxx, medicos
              </code>
            </div>

            {/* Download template */}
            <Button variant="outline" size="sm" className="w-full" onClick={downloadTemplate}>
              <Download className="mr-2 h-4 w-4" />
              Baixar template CSV
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Import result */}
            <div className="rounded-lg bg-muted p-4">
              <h4 className="mb-3 font-medium">Resultado da Importacao</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Total:</span>{' '}
                  <span className="font-medium">{result.total}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Validos:</span>{' '}
                  <span className="font-medium text-status-success-foreground">{result.valid}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Duplicados:</span>{' '}
                  <span className="font-medium text-status-warning-foreground">
                    {result.duplicates}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Invalidos:</span>{' '}
                  <span className="font-medium text-status-error-foreground">{result.invalid}</span>
                </div>
              </div>
            </div>

            {/* Errors */}
            {result.errors.length > 0 && (
              <div className="rounded-lg border border-status-error-border bg-status-error p-3">
                <h4 className="mb-2 text-sm font-medium text-status-error-foreground">Erros:</h4>
                <div className="max-h-24 overflow-y-auto text-xs text-status-error-foreground">
                  {result.errors.map((err, i) => (
                    <p key={i}>
                      Linha {err.line}: {err.error}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          {!result ? (
            <Button onClick={handleUpload} disabled={!file || uploading}>
              {uploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Enviar
                </>
              )}
            </Button>
          ) : (
            <Button onClick={handleConfirmImport} disabled={result.valid === 0}>
              Importar {result.valid} links validos
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
