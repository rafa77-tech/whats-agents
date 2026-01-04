import { StatusCard } from '@/components/dashboard/status-card'
import {
  MessageSquare,
  Users,
  Briefcase,
  TrendingUp,
  CheckCircle,
  Clock,
  AlertCircle,
} from 'lucide-react'

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Visao geral do sistema Julia</p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatusCard
          title="Conversas Hoje"
          value="24"
          icon={MessageSquare}
          trend={{ value: 12, positive: true }}
        />
        <StatusCard
          title="Medicos Ativos"
          value="156"
          icon={Users}
          trend={{ value: 8, positive: true }}
        />
        <StatusCard title="Vagas Abertas" value="12" icon={Briefcase} />
        <StatusCard
          title="Taxa Resposta"
          value="34%"
          icon={TrendingUp}
          trend={{ value: 5, positive: true }}
        />
      </div>

      {/* Status Julia */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Status Julia</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="flex items-center gap-3 rounded-lg bg-green-50 p-4">
            <CheckCircle className="h-6 w-6 text-green-600" />
            <div>
              <p className="font-medium text-green-900">Online</p>
              <p className="text-sm text-green-600">Respondendo normalmente</p>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-lg bg-blue-50 p-4">
            <Clock className="h-6 w-6 text-blue-600" />
            <div>
              <p className="font-medium text-blue-900">Horario Ativo</p>
              <p className="text-sm text-blue-600">08:00 - 20:00</p>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-lg bg-gray-50 p-4">
            <AlertCircle className="h-6 w-6 text-gray-600" />
            <div>
              <p className="font-medium text-gray-900">Rate Limit</p>
              <p className="text-sm text-gray-600">15/20 msgs esta hora</p>
            </div>
          </div>
        </div>
      </div>

      {/* Atividade Recente */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Atividade Recente</h2>
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="flex items-center gap-4 border-b border-gray-100 py-3 last:border-0"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-revoluna-50">
                <MessageSquare className="h-5 w-5 text-revoluna-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-gray-900">Dr. Carlos Silva respondeu</p>
                <p className="text-sm text-gray-500">Interesse em plantao cardiologia</p>
              </div>
              <span className="text-sm text-gray-400">2min</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
