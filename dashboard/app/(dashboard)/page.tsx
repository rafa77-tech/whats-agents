import { StatusCard } from "@/components/dashboard/status-card";
import {
  MessageSquare,
  Users,
  Briefcase,
  TrendingUp,
  CheckCircle,
  Clock,
  AlertCircle
} from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Visao geral do sistema Julia</p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
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
        <StatusCard
          title="Vagas Abertas"
          value="12"
          icon={Briefcase}
        />
        <StatusCard
          title="Taxa Resposta"
          value="34%"
          icon={TrendingUp}
          trend={{ value: 5, positive: true }}
        />
      </div>

      {/* Status Julia */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Status Julia</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
            <CheckCircle className="w-6 h-6 text-green-600" />
            <div>
              <p className="font-medium text-green-900">Online</p>
              <p className="text-sm text-green-600">Respondendo normalmente</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg">
            <Clock className="w-6 h-6 text-blue-600" />
            <div>
              <p className="font-medium text-blue-900">Horario Ativo</p>
              <p className="text-sm text-blue-600">08:00 - 20:00</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
            <AlertCircle className="w-6 h-6 text-gray-600" />
            <div>
              <p className="font-medium text-gray-900">Rate Limit</p>
              <p className="text-sm text-gray-600">15/20 msgs esta hora</p>
            </div>
          </div>
        </div>
      </div>

      {/* Atividade Recente */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Atividade Recente</h2>
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center gap-4 py-3 border-b border-gray-100 last:border-0">
              <div className="w-10 h-10 rounded-full bg-julia-100 flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-julia-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  Dr. Carlos Silva respondeu
                </p>
                <p className="text-sm text-gray-500">
                  Interesse em plantao cardiologia
                </p>
              </div>
              <span className="text-sm text-gray-400">2min</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
