"use client";

import { useState } from "react";
import { Bell, Menu, Search, X } from "lucide-react";
import { Sidebar } from "./sidebar";

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between px-4 py-3 lg:px-6">
          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="lg:hidden p-2 -ml-2 text-gray-500 hover:text-gray-700"
          >
            <Menu className="w-6 h-6" />
          </button>

          {/* Search */}
          <div className="flex-1 max-w-lg mx-4 lg:mx-0">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="search"
                placeholder="Buscar medicos, conversas..."
                className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-julia-500 focus:border-transparent outline-none"
              />
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">
            {/* Notifications */}
            <button className="relative p-2 text-gray-500 hover:text-gray-700">
              <Bell className="w-6 h-6" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            </button>

            {/* User avatar */}
            <div className="w-9 h-9 rounded-full bg-julia-100 flex items-center justify-center">
              <span className="text-sm font-medium text-julia-700">R</span>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile sidebar overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50"
            onClick={() => setMobileMenuOpen(false)}
          />

          {/* Sidebar */}
          <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-xl">
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="absolute top-4 right-4 p-2 text-gray-500"
            >
              <X className="w-5 h-5" />
            </button>
            <Sidebar />
          </div>
        </div>
      )}
    </>
  );
}
