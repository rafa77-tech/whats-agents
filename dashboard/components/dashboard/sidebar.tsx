"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Megaphone,
  FileText,
  Building2,
  Settings,
  HelpCircle,
  Power,
  type LucideIcon,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
}

const navigation: NavItem[] = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Campanhas", href: "/campanhas", icon: Megaphone },
  { name: "Instrucoes", href: "/instrucoes", icon: FileText },
  { name: "Hospitais Bloqueados", href: "/hospitais/bloqueados", icon: Building2 },
  { name: "Sistema", href: "/sistema", icon: Settings },
  { name: "Ajuda", href: "/ajuda", icon: HelpCircle },
];

export function Sidebar() {
  const pathname = usePathname();

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
          const isActive = pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href as Route}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-revoluna-50 text-revoluna-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <item.icon className={cn(
                "w-5 h-5",
                isActive ? "text-revoluna-400" : "text-gray-400"
              )} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <button className="flex items-center gap-3 w-full px-3 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
          <Power className="w-5 h-5 text-gray-400" />
          Sair
        </button>
      </div>
    </div>
  );
}
