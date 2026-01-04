"use client";

import { useState } from "react";
import { Menu, Search, X } from "lucide-react";
import { Sidebar } from "./sidebar";
import { JuliaStatus } from "./julia-status";
import { NotificationBell } from "./notification-bell";
import { UserMenu } from "./user-menu";

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 bg-white border-b border-gray-200">
        <div className="flex items-center gap-4 px-4 py-3 lg:px-6">
          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="lg:hidden p-2 -ml-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Abrir menu</span>
          </button>

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-revoluna-400 flex items-center justify-center">
              <span className="text-white font-bold text-sm">J</span>
            </div>
            <span className="font-semibold text-gray-900">Julia</span>
          </div>

          {/* Julia Status - hidden on mobile */}
          <div className="hidden sm:flex">
            <JuliaStatus />
          </div>

          {/* Search - Desktop only */}
          <div className="hidden md:flex flex-1 max-w-md">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="search"
                placeholder="Buscar medicos, conversas..."
                className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-revoluna-400 focus:border-transparent outline-none transition-all"
              />
            </div>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Right side actions */}
          <div className="flex items-center gap-1">
            {/* Notifications */}
            <NotificationBell />

            {/* User Menu */}
            <UserMenu />
          </div>
        </div>
      </header>

      {/* Mobile sidebar overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
          />

          {/* Sidebar drawer */}
          <div className="fixed inset-y-0 left-0 w-72 bg-white shadow-xl">
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="absolute top-4 right-4 p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors z-10"
            >
              <X className="h-5 w-5" />
              <span className="sr-only">Fechar menu</span>
            </button>
            <Sidebar onNavigate={() => setMobileMenuOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
