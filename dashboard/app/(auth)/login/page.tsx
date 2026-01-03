"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Mail, Loader2, CheckCircle } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const supabase = createClient();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { error: authError } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: `${window.location.origin}/callback`,
        },
      });

      if (authError) throw authError;
      setSent(true);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Erro ao enviar link";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-revoluna-50 to-revoluna-100">
        <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-xl text-center">
          <div className="mx-auto w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-6">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Verifique seu email
          </h1>
          <p className="text-gray-500 mb-6">
            Enviamos um link de acesso para <strong>{email}</strong>
          </p>
          <button
            type="button"
            onClick={() => {
              setSent(false);
              setEmail("");
            }}
            className="text-sm text-revoluna-600 hover:text-revoluna-700 underline"
          >
            Usar outro email
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-revoluna-50 to-revoluna-100">
      <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-xl">
        <div className="text-center mb-8">
          <div className="mx-auto w-14 h-14 rounded-xl bg-revoluna-400 flex items-center justify-center mb-4">
            <span className="text-white font-bold text-2xl">J</span>
          </div>
          <h1 className="text-3xl font-bold text-revoluna-700">
            Julia Dashboard
          </h1>
          <p className="text-gray-500 mt-2">Entre com seu email para acessar</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Email
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                disabled={loading}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-revoluna-400 focus:border-transparent outline-none transition-all disabled:opacity-50"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !email}
            className="w-full py-3 px-4 bg-revoluna-400 hover:bg-revoluna-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Enviando...
              </>
            ) : (
              "Entrar com Magic Link"
            )}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Voce recebera um link de acesso no seu email
        </p>
      </div>
    </div>
  );
}
