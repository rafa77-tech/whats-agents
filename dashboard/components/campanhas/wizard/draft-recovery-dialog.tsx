/**
 * Draft Recovery Dialog - Sprint 34 E05
 *
 * Dialog shown when a draft is found in localStorage.
 */

'use client'

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
import { FileText } from 'lucide-react'

interface DraftRecoveryDialogProps {
  open: boolean
  draftStep: number
  onRecover: () => void
  onDiscard: () => void
}

const STEP_NAMES: Record<number, string> = {
  1: 'Configuracao',
  2: 'Audiencia',
  3: 'Mensagem',
  4: 'Revisao',
}

export function DraftRecoveryDialog({
  open,
  draftStep,
  onRecover,
  onDiscard,
}: DraftRecoveryDialogProps) {
  return (
    <AlertDialog open={open}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-amber-500" />
            Rascunho Encontrado
          </AlertDialogTitle>
          <AlertDialogDescription>
            Encontramos um rascunho de campanha que voce estava criando. Voce estava no passo{' '}
            <strong>{draftStep}</strong> ({STEP_NAMES[draftStep] || 'Desconhecido'}).
            <br />
            <br />
            Deseja continuar de onde parou ou comecar do zero?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onDiscard}>Comecar do Zero</AlertDialogCancel>
          <AlertDialogAction onClick={onRecover}>Continuar Rascunho</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
