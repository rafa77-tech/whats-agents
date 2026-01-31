import { Metadata } from 'next'
import { GroupEntryPageContent } from '@/components/group-entry/group-entry-page-content'

export const metadata: Metadata = {
  title: 'Entrada em Grupos | Julia Dashboard',
  description: 'Gestao de entrada em grupos WhatsApp',
}

export default function GruposPage() {
  return <GroupEntryPageContent />
}
