import { DashboardLayoutWrapper } from '@/components/dashboard/dashboard-layout-wrapper'

/**
 * Layout principal do Dashboard.
 *
 * Sprint 44 T05.2: Convertido para Server Component.
 * A lógica dependente de pathname foi movida para DashboardLayoutWrapper (client).
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <DashboardLayoutWrapper>{children}</DashboardLayoutWrapper>
}
