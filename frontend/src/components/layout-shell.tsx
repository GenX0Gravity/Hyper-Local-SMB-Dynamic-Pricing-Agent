"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import {
  LayoutDashboard,
  TrendingUp,
  Zap,
  CloudRain,
  CalendarDays,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
} from "lucide-react"

const NAV_ITEMS = [
  { name: "Overview", href: "/overview", icon: LayoutDashboard },
  { name: "Demand Forecast", href: "/forecast", icon: TrendingUp },
  { name: "Pricing Recommendations", href: "/recommendations", icon: Zap, highlight: true },
  { name: "Weather Impact", href: "/weather", icon: CloudRain },
  { name: "Event Impact", href: "/events", icon: CalendarDays },
  { name: "Revenue Analytics", href: "/revenue", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
]

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { user, logout, loading } = useAuth()
  const [mobileOpen, setMobileOpen] = React.useState(false)

  const isAuthPage =
    pathname === "/login" || pathname === "/register" || pathname === "/"

  React.useEffect(() => {
    setMobileOpen(false)
  }, [pathname])

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#030712] text-emerald-500">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent" />
          <span className="text-sm font-semibold tracking-wider animate-pulse">
            LOADING PRICEPULSE...
          </span>
        </div>
      </div>
    )
  }

  if (isAuthPage) {
    return <div className="min-h-screen bg-[#030712]">{children}</div>
  }

  const currentPage =
    NAV_ITEMS.find((item) => pathname === item.href || pathname.startsWith(item.href + "/"))
      ?.name || "Dashboard"

  const sidebar = (
  <>
    <div className="flex h-16 items-center border-b border-white/5 px-5">
      <Link href="/overview" className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-lg shadow-emerald-500/25">
          <Zap className="h-4 w-4 fill-slate-950 text-slate-950" />
        </div>
        <span className="text-lg font-bold text-white">
          PricePulse <span className="text-emerald-400">AI</span>
        </span>
      </Link>
      <button
        type="button"
        className="ml-auto lg:hidden text-slate-400 hover:text-white"
        onClick={() => setMobileOpen(false)}
        aria-label="Close menu"
      >
        <X className="h-5 w-5" />
      </button>
    </div>

    {user && (
      <div className="mx-4 mt-4 rounded-xl border border-white/5 bg-white/[0.03] p-3 backdrop-blur-sm">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
          Active Store
        </p>
        <p className="truncate text-sm font-semibold text-white">{user.tenant_name}</p>
      </div>
    )}

    <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon
        const isActive = pathname === item.href
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
              isActive
                ? item.highlight
                  ? "bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/25"
                  : "bg-white/10 text-white"
                : "text-slate-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            <Icon
              className={`h-4 w-4 shrink-0 ${
                isActive && item.highlight ? "text-slate-950" : isActive ? "text-emerald-400" : ""
              }`}
            />
            <span className="truncate">{item.name}</span>
          </Link>
        )
      })}
    </nav>

    <div className="border-t border-white/5 p-4">
      {user && (
        <div className="mb-3 px-1">
          <p className="truncate text-sm font-semibold text-white">{user.full_name}</p>
          <p className="text-xs capitalize text-slate-500">{user.role}</p>
        </div>
      )}
      <button
        type="button"
        onClick={logout}
        className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/10"
      >
        <LogOut className="h-4 w-4" />
        Sign Out
      </button>
    </div>
  </>
  )

  return (
    <div className="relative min-h-screen bg-[#030712] text-slate-100">
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -left-32 top-0 h-[28rem] w-[28rem] rounded-full bg-emerald-500/10 blur-[120px]" />
        <div className="absolute -right-32 bottom-0 h-[28rem] w-[28rem] rounded-full bg-violet-500/10 blur-[120px]" />
        <div className="absolute left-1/2 top-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-500/5 blur-[100px]" />
      </div>

      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Close overlay"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-white/5 bg-slate-950/90 backdrop-blur-xl transition-transform duration-300 lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {sidebar}
      </aside>

      <div className="flex min-h-screen flex-col lg:pl-72">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-white/5 bg-[#030712]/80 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="text-lg font-bold text-white sm:text-xl">{currentPage}</h1>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="hidden text-slate-500 sm:inline">Engine</span>
            <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 font-semibold text-emerald-400">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              Live
            </span>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  )
}
