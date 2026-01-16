"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Megaphone,
  FileText,
  Settings,
  HelpCircle,
} from "lucide-react";

const navigation = [
  { name: "Home", href: "/", icon: LayoutDashboard },
  { name: "Campanhas", href: "/campanhas", icon: Megaphone },
  { name: "Instrucoes", href: "/instrucoes", icon: FileText },
  { name: "Sistema", href: "/sistema", icon: Settings },
  { name: "Ajuda", href: "/ajuda", icon: HelpCircle },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <div className="bg-white border-t border-gray-200 px-2 py-2 safe-area-pb">
      <nav className="flex items-center justify-around">
        {navigation.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-1 px-3 py-2 rounded-lg min-w-[64px] transition-colors",
                isActive
                  ? "text-revoluna-400"
                  : "text-gray-500"
              )}
            >
              <item.icon className="w-6 h-6" />
              <span className="text-xs font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
