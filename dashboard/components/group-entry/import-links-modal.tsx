'use client'

import { useState, useCallback } from 'react'
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

interface ImportLinksModalProps {
  onClose: () => void
  onImport: () => void
}

interface ImportResult {
  total: number
  valid: number
  duplicates: number
  invalid: number
  errors: Array<{ line: number; error: string }>
}

export function ImportLinksModal({ onClose, onImport }: ImportLinksModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [dragActive, setDragActive] = useState(false)

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
      if (droppedFile.name.endsWith('.csv') || droppedFile.name.endsWith('.xlsx')) {
        setFile(droppedFile)
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/group-entry/import/csv', {
        method: 'POST',
        body: formData,
      })

      if (res.ok) {
        const data = await res.json()
        setResult({
          total: data.total || 0,
          valid: data.valid || 0,
          duplicates: data.duplicates || 0,
          invalid: data.invalid || 0,
          errors: data.errors || [],
        })
      }
    } catch {
      // Ignore errors
    } finally {
      setUploading(false)
    }
  }

  const handleConfirmImport = () => {
    onImport()
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
                dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300',
                file && 'border-green-500 bg-green-50'
              )}
            >
              {file ? (
                <>
                  <CheckCircle2 className="h-8 w-8 text-green-500" />
                  <p className="mt-2 text-sm font-medium text-green-700">{file.name}</p>
                  <Button variant="link" size="sm" onClick={() => setFile(null)}>
                    Remover
                  </Button>
                </>
              ) : (
                <>
                  <Upload className="h-8 w-8 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-600">
                    Arraste um arquivo CSV ou Excel aqui
                  </p>
                  <label className="mt-2 cursor-pointer">
                    <span className="text-sm text-blue-600 hover:underline">
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
            <div className="rounded-lg bg-gray-50 p-3 text-sm">
              <p className="font-medium text-gray-700">Formato esperado:</p>
              <code className="text-xs text-gray-600">
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
            <div className="rounded-lg bg-gray-50 p-4">
              <h4 className="mb-3 font-medium">Resultado da Importacao</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-500">Total:</span>{' '}
                  <span className="font-medium">{result.total}</span>
                </div>
                <div>
                  <span className="text-gray-500">Validos:</span>{' '}
                  <span className="font-medium text-green-600">{result.valid}</span>
                </div>
                <div>
                  <span className="text-gray-500">Duplicados:</span>{' '}
                  <span className="font-medium text-yellow-600">{result.duplicates}</span>
                </div>
                <div>
                  <span className="text-gray-500">Invalidos:</span>{' '}
                  <span className="font-medium text-red-600">{result.invalid}</span>
                </div>
              </div>
            </div>

            {/* Errors */}
            {result.errors.length > 0 && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                <h4 className="mb-2 text-sm font-medium text-red-700">Erros:</h4>
                <div className="max-h-24 overflow-y-auto text-xs text-red-600">
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
