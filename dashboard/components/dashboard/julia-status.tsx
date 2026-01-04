'use client'

import { useEffect, useState } from 'react'

interface JuliaStatusData {
  status: 'ativo' | 'pausado' | 'erro'
  motivo?: string
}

export function JuliaStatus() {
  const [status, setStatus] = useState<JuliaStatusData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // TODO: Replace with actual API call when backend endpoint is ready
    // For now, simulate active status
    const fetchStatus = async () => {
      try {
        // const response = await fetch('/api/v1/dashboard/status')
        // const data = await response.json()
        // setStatus(data)

        // Simulated response
        setStatus({ status: 'ativo' })
      } catch {
        setStatus({ status: 'erro' })
      } finally {
        setLoading(false)
      }
    }

    fetchStatus()

    // Refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-gray-100 text-gray-500 text-xs">
        <span className="h-2 w-2 rounded-full bg-gray-400 animate-pulse" />
        Carregando...
      </div>
    )
  }

  const isActive = status?.status === 'ativo'
  const isPaused = status?.status === 'pausado'

  return (
    <div
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
        isActive
          ? 'bg-green-100 text-green-700'
          : isPaused
          ? 'bg-yellow-100 text-yellow-700'
          : 'bg-red-100 text-red-700'
      }`}
      title={status?.motivo}
    >
      <span
        className={`h-2 w-2 rounded-full ${
          isActive
            ? 'bg-green-500 animate-pulse'
            : isPaused
            ? 'bg-yellow-500'
            : 'bg-red-500'
        }`}
      />
      Julia {isActive ? 'Ativa' : isPaused ? 'Pausada' : 'Erro'}
    </div>
  )
}
