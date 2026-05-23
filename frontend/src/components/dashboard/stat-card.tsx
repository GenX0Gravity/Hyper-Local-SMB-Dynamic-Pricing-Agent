import * as React from "react"
import { LucideIcon } from "lucide-react"

interface StatCardProps {
  title: string
  value: string
  subtitle?: string
  icon: LucideIcon
  trend?: { value: string; positive?: boolean }
  accent?: "emerald" | "purple" | "blue" | "amber" | "default"
}

const accentMap = {
  emerald: "border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.08)]",
  purple: "border-purple-500/20 shadow-[0_0_20px_rgba(139,92,246,0.08)]",
  blue: "border-blue-500/20 shadow-[0_0_20px_rgba(59,130,246,0.08)]",
  amber: "border-amber-500/20 shadow-[0_0_20px_rgba(245,158,11,0.08)]",
  default: "border-white/5",
}

const iconMap = {
  emerald: "text-emerald-400 bg-emerald-500/10",
  purple: "text-purple-400 bg-purple-500/10",
  blue: "text-blue-400 bg-blue-500/10",
  amber: "text-amber-400 bg-amber-500/10",
  default: "text-slate-400 bg-slate-800/80",
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  accent = "default",
}: StatCardProps) {
  return (
    <div
      className={`glass-card rounded-2xl p-5 transition-all duration-300 hover:border-white/10 ${accentMap[accent]}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {title}
          </p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            {value}
          </p>
          {subtitle && (
            <p className="mt-1 text-xs font-medium text-slate-500">{subtitle}</p>
          )}
          {trend && (
            <p
              className={`mt-2 text-xs font-semibold ${
                trend.positive ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {trend.value}
            </p>
          )}
        </div>
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconMap[accent]}`}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  )
}
