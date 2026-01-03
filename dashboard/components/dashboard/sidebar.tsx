"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  Briefcase,
  Megaphone,
  BarChart3,
  Settings,
  Shield,
  Power,
  Loader2,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Conversas", href: "/conversas", icon: MessageSquare },
  { name: "Medicos", href: "/medicos", icon: Users },
  { name: "Vagas", href: "/vagas", icon: Briefcase },
  { name: "Campanhas", href: "/campanhas", icon: Megaphone },
  { name: "Metricas", href: "/metricas", icon: BarChart3 },
  { name: "Sistema", href: "/sistema", icon: Settings },
  { name: "Auditoria", href: "/auditoria", icon: Shield, requiredRole: "admin" as const },
];

const ROLE_LABELS: Record<string, string> = {
  viewer: "Visualizador",
  operator: "Operador",
  manager: "Gestor",
  admin: "Admin",
};

export function Sidebar() {
  const pathname = usePathname();
  const { dashboardUser, signOut, loading, hasPermission } = useAuth();

  const handleSignOut = async () => {
    await signOut();
  };

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-200">
        <div className="w-10 h-10 rounded-xl bg-revoluna-400 flex items-center justify-center">
          <span className="text-white font-bold text-lg">J</span>
        </div>
        <div>
          <h1 className="font-bold text-gray-900">Julia</h1>
          <p className="text-xs text-gray-500">Dashboard</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => {
          // Check role permission if required
          if (item.requiredRole && !hasPermission(item.requiredRole)) {
            return null;
          }

          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-revoluna-50 text-revoluna-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <item.icon
                className={cn(
                  "w-5 h-5",
                  isActive ? "text-revoluna-400" : "text-gray-400"
                )}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* User info & Logout */}
      <div className="p-4 border-t border-gray-200 space-y-3">
        {/* User info */}
        {dashboardUser && (
          <div className="px-3 py-2">
            <p className="text-sm font-medium text-gray-900 truncate">
              {dashboardUser.nome}
            </p>
            <p className="text-xs text-gray-500">
              {ROLE_LABELS[dashboardUser.role] || dashboardUser.role}
            </p>
          </div>
        )}

        {/* Logout button */}
        <button
          onClick={handleSignOut}
          disabled={loading}
          className="flex items-center gap-3 w-full px-3 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
          ) : (
            <Power className="w-5 h-5 text-gray-400" />
          )}
          Sair
        </button>
      </div>
    </div>
  );
}
