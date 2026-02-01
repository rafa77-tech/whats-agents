import { Metadata } from 'next'
import { QualidadePageContent } from '@/components/qualidade/qualidade-page-content'

export const metadata: Metadata = {
  title: 'Qualidade | Julia Dashboard',
  description: 'Avaliacao de qualidade das conversas',
}

export default function QualidadePage() {
  return <QualidadePageContent />
}
