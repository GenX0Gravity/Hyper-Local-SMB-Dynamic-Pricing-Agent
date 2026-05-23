"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { 
  LayoutDashboard, 
  Package, 
  Settings as SettingsIcon, 
  TrendingUp, 
  Zap, 
  Sliders, 
  LogOut,
  Sparkles,
  CloudSun
} from "lucide-react"

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { user, logout, loading } = useAuth()
  
  const isAuthPage = pathname === "/login" || pathname === "/register" || pathname === "/"

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-950 text-emerald-500">
        <div className="flex flex-col items-center space-y-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent"></div>
          <span className="text-sm font-semibold tracking-wider animate-pulse">LOADING PRICEPULSE AI...</span>
        </div>
      </div>
    )
  }

  // Render auth pages directly without sidebar
  if (isAuthPage) {
    return <div className="min-h-screen bg-[#030712]">{children}</div>
  }

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Recommendations", href: "/recommendations", icon: Zap, highlight: true },
    { name: "Product Catalog", href: "/products", icon: Package },
    { name: "Pricing Rules", href: "/rules", icon: Sliders },
    { name: "Demand Forecasts", href: "/analytics", icon: TrendingUp },
    { name: "Store Settings", href: "/settings", icon: SettingsIcon },
  ]

  return (
    <div className="flex min-h-screen bg-[#030712] text-slate-100">
      {/* Decorative background glows */}
      <div className="absolute top-0 left-1/4 -z-10 h-96 w-96 rounded-full bg-emerald-500/5 blur-[120px]" />
      <div className="absolute bottom-0 right-1/4 -z-10 h-96 w-96 rounded-full bg-purple-500/5 blur-[120px]" />

      {/* Sidebar navigation */}
      <aside className="fixed inset-y-0 left-0 z-20 flex w-64 flex-col border-r border-slate-900 bg-slate-950/80 backdrop-blur-md">
        {/* Brand */}
        <div className="flex h-16 items-center px-6 border-b border-slate-900">
          <Link href="/dashboard" className="flex items-center space-x-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500 text-slate-950">
              <Zap className="h-4 w-4 fill-slate-950" />
            </div>
            <span className="text-lg font-bold tracking-tight text-white">PricePulse <span className="text-emerald-400">AI</span></span>
          </Link>
        </div>

        {/* Store Context Indicator */}
        {user && (
          <div className="px-4 py-3 mx-4 my-4 rounded-lg bg-slate-900/50 border border-slate-800/80 flex items-center justify-between">
            <div>
              <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Active Store</p>
              <p className="text-xs font-semibold text-white truncate max-w-[140px]">{user.tenant_name}</p>
            </div>
            <CloudSun className="h-4 w-4 text-emerald-400" />
          </div>
        )}

        {/* Navigation items */}
        <nav className="flex-1 space-y-1 px-4 py-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-150 ${
                  isActive
                    ? item.highlight 
                      ? "bg-emerald-500 text-slate-950 shadow-[0_0_15px_rgba(16,185,129,0.3)]"
                      : "bg-slate-900 text-white border-l-2 border-emerald-500 pl-2.5"
                    : "text-slate-400 hover:bg-slate-900/50 hover:text-white"
                }`}
              >
                <Icon className={`mr-3 h-4 w-4 shrink-0 transition-transform group-hover:scale-110 ${
                  isActive 
                    ? item.highlight ? "text-slate-950" : "text-emerald-400" 
                    : "text-slate-400 group-hover:text-slate-200"
                }`} />
                <span>{item.name}</span>
                {item.highlight && !isActive && (
                  <Sparkles className="ml-auto h-3.5 w-3.5 text-emerald-400 animate-pulse" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* User profile details and Logout button */}
        <div className="border-t border-slate-900 p-4 bg-slate-950/40">
          {user && (
            <div className="mb-3 px-2">
              <p className="text-sm font-semibold text-white truncate">{user.full_name}</p>
              <p className="text-xs text-slate-500 truncate capitalize">{user.role}</p>
            </div>
          )}
          <button
            onClick={logout}
            className="flex w-full items-center px-3 py-2 text-sm font-medium text-red-400 hover:bg-red-950/20 hover:text-red-300 rounded-lg transition-colors cursor-pointer"
          >
            <LogOut className="mr-3 h-4 w-4 text-red-400" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main app panel */}
      <div className="flex flex-col flex-1 pl-64">
        {/* Top Header */}
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-slate-900 bg-[#030712]/80 backdrop-blur-md px-8">
          <h1 className="text-xl font-bold text-white tracking-tight">
            {navItems.find((item) => item.href === pathname)?.name || "Dashboard"}
          </h1>
          
          <div className="flex items-center space-x-4">
            <span className="text-xs text-slate-500 font-medium">Real-time optimization engine: <span className="text-emerald-400">active</span></span>
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></div>
          </div>
        </header>
        
        {/* Main Content Area */}
        <main className="flex-1 p-8 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
