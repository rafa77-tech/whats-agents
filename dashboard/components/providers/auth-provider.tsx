"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { User, Session } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";

export type UserRole = "viewer" | "operator" | "manager" | "admin";

export interface DashboardUser {
  id: string;
  email: string;
  nome: string;
  avatar_url: string | null;
  role: UserRole;
  ativo: boolean;
  notificacoes_habilitadas: boolean;
}

interface AuthContextType {
  user: User | null;
  dashboardUser: DashboardUser | null;
  session: Session | null;
  loading: boolean;
  signOut: () => Promise<void>;
  hasPermission: (requiredRole: UserRole) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const ROLE_HIERARCHY: Record<UserRole, number> = {
  viewer: 0,
  operator: 1,
  manager: 2,
  admin: 3,
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const supabase = createClient();

  const [user, setUser] = useState<User | null>(null);
  const [dashboardUser, setDashboardUser] = useState<DashboardUser | null>(
    null
  );
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchDashboardUser(session.user.id);
      } else {
        setLoading(false);
      }
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      setSession(session);
      setUser(session?.user ?? null);

      if (session?.user) {
        await fetchDashboardUser(session.user.id);
      } else {
        setDashboardUser(null);
        setLoading(false);
      }

      if (event === "SIGNED_OUT") {
        router.push("/login");
      }
    });

    return () => subscription.unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchDashboardUser(supabaseUserId: string) {
    try {
      const { data, error } = await supabase
        .from("dashboard_users")
        .select("*")
        .eq("supabase_user_id", supabaseUserId)
        .single();

      if (error) throw error;
      setDashboardUser(data);

      // Atualizar último acesso
      await supabase
        .from("dashboard_users")
        .update({ ultimo_acesso: new Date().toISOString() })
        .eq("id", data.id);
    } catch (error) {
      console.error("Error fetching dashboard user:", error);
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    await supabase.auth.signOut();
  }

  function hasPermission(requiredRole: UserRole): boolean {
    if (!dashboardUser) return false;
    return ROLE_HIERARCHY[dashboardUser.role] >= ROLE_HIERARCHY[requiredRole];
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        dashboardUser,
        session,
        loading,
        signOut,
        hasPermission,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
