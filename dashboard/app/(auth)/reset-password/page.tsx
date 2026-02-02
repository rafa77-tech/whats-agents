'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Lock, Loader2, Eye, EyeOff, CheckCircle } from 'lucide-react'

export default function ResetPasswordPage() {
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const supabase = createClient()

  useEffect(() => {
    // Check if we have a valid session from the recovery link
    const checkSession = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession()
      if (!session) {
        // No session means the recovery link wasn't processed correctly
        // The user might have arrived here directly
        setError('Link de recuperação inválido ou expirado. Solicite um novo link.')
      }
    }
    checkSession()
  }, [supabase.auth])

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (password !== confirmPassword) {
      setError('As senhas não coincidem')
      setLoading(false)
      return
    }

    if (password.length < 6) {
      setError('A senha deve ter pelo menos 6 caracteres')
      setLoading(false)
      return
    }

    try {
      const { error: updateError } = await supabase.auth.updateUser({
        password: password,
      })

      if (updateError) {
        throw updateError
      }

      setSuccess(true)

      // Redirect to dashboard after 2 seconds
      setTimeout(() => {
        router.push('/dashboard')
      }, 2000)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao atualizar senha'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-revoluna-50 to-revoluna-100">
        <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-xl">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-status-success">
            <CheckCircle className="h-8 w-8 text-status-success-foreground" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Senha atualizada!</h1>
          <p className="mt-2 text-gray-500">Redirecionando para o dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-revoluna-50 to-revoluna-100">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-revoluna-400">
            <span className="text-2xl font-bold text-white">J</span>
          </div>
          <h1 className="text-3xl font-bold text-revoluna-700">Nova Senha</h1>
          <p className="mt-2 text-gray-500">Digite sua nova senha</p>
        </div>

        <form onSubmit={handleResetPassword} className="space-y-5">
          {error && (
            <div className="rounded-lg border border-status-error-border bg-status-error p-3">
              <p className="text-sm text-status-error-foreground">{error}</p>
            </div>
          )}

          <div>
            <label htmlFor="password" className="mb-2 block text-sm font-medium text-gray-700">
              Nova Senha
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="********"
                required
                disabled={loading}
                className="w-full rounded-lg border border-gray-300 py-3 pl-10 pr-12 outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-revoluna-400 disabled:opacity-50"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                className="absolute right-3 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center text-gray-400 hover:text-gray-600"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
          </div>

          <div>
            <label
              htmlFor="confirmPassword"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Confirmar Senha
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                id="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="********"
                required
                disabled={loading}
                className="w-full rounded-lg border border-gray-300 py-3 pl-10 pr-12 outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-revoluna-400 disabled:opacity-50"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !password || !confirmPassword}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-revoluna-400 px-4 py-3 font-medium text-white transition-colors hover:bg-revoluna-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Atualizando...
              </>
            ) : (
              'Atualizar Senha'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
