"use client"

import * as React from "react"
import Link from "next/link"
import { apiFetch } from "@/lib/api-client"
import { useAuth } from "@/lib/auth-context"
import { PageHeader } from "@/components/dashboard/page-header"
import { StatCard } from "@/components/dashboard/stat-card"
import { GlassPanel } from "@/components/dashboard/glass-panel"
import { Button } from "@/components/ui/button"
import {
  LayoutDashboard,
  TrendingUp,
  Zap,
  Activity,
  CheckCircle2,
  RefreshCw,
  CloudRain,
  CalendarDays,
  ArrowRight,
} from "lucide-react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
} from "recharts"
import { chartTooltipStyle, chartLabelStyle, CHART_COLORS } from "@/lib/chart-theme"

interface KpiResponse {
  kpis: {
    revenue_increase: number
    conversion_rate: number
    accepted_recommendations: number
    total_revenue: number
    total_units_sold: number
  }
}

export default function OverviewPage() {
  const { user } = useAuth()
  const [stats, setStats] = React.useState<KpiResponse["kpis"] | null>(null)
  const [eventScore, setEventScore] = React.useState(0)
  const [weatherScore, setWeatherScore] = React.useState(50)
  const [pendingRecs, setPendingRecs] = React.useState(0)
  const [evaluating, setEvaluating] = React.useState(false)

  const load = React.useCallback(async () => {
    const [statsRes, eventsRes, weatherRes, recsRes] = await Promise.all([
      apiFetch("/analytics/kpi?lookback_days=30"),
      apiFetch("/events/impact-score"),
      apiFetch("/weather/monitor"),
      apiFetch("/recommendations?status_filter=pending"),
    ])
    if (statsRes.ok) {
      const data = await statsRes.json()
      setStats(data.kpis)
    }
    if (eventsRes.ok) {
      const e = await eventsRes.json()
      setEventScore(e.aggregate_impact_score ?? 0)
    }
    if (weatherRes.ok) {
      const w = await weatherRes.json()
      setWeatherScore(w.is_heavy_rain ? 85 : w.is_raining ? 70 : 50)
    }
    if (recsRes.ok) setPendingRecs((await recsRes.json()).length)
  }, [])

  React.useEffect(() => {
    load()
  }, [load])

  const runEvaluate = async () => {
    setEvaluating(true)
    await apiFetch("/recommendations/evaluate", { method: "POST" })
    await load()
    setEvaluating(false)
  }

  const revenueChart = [
    { day: "Mon", base: 620, optimized: 680 },
    { day: "Tue", base: 710, optimized: 790 },
    { day: "Wed", base: 540, optimized: 610 },
    { day: "Thu", base: 820, optimized: 940 },
    { day: "Fri", base: 950, optimized: 1080 },
    { day: "Sat", base: 1100, optimized: 1240 },
    { day: "Sun", base: 880, optimized: 960 },
  ]

  const signalChart = [
    { name: "Demand", value: 68 },
    { name: "Weather", value: weatherScore },
    { name: "Events", value: eventScore },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${user?.full_name?.split(" ")[0] || "there"}`}
        description="Real-time pricing intelligence across weather, events, and demand signals."
        icon={LayoutDashboard}
        badge="Overview"
        actions={
          <Button variant="glow" onClick={runEvaluate} disabled={evaluating}>
            <RefreshCw className={`mr-2 h-4 w-4 ${evaluating ? "animate-spin" : ""}`} />
            Sync Prices
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Revenue Lift"
          value={`+$${stats?.revenue_increase?.toFixed(0) ?? "426"}`}
          subtitle="From dynamic pricing"
          icon={TrendingUp}
          accent="emerald"
          trend={{ value: "+8.4% vs baseline", positive: true }}
        />
        <StatCard
          title="Total Revenue"
          value={`$${stats?.total_revenue?.toLocaleString() ?? "4,850"}`}
          subtitle={`${stats?.total_units_sold ?? 320} units sold`}
          icon={Activity}
          accent="blue"
        />
        <StatCard
          title="Pending Actions"
          value={String(pendingRecs)}
          subtitle="Pricing recommendations"
          icon={Zap}
          accent="amber"
        />
        <StatCard
          title="Capture Rate"
          value={`${stats?.conversion_rate?.toFixed(0) ?? 80}%`}
          subtitle={`${stats?.accepted_recommendations ?? 24} accepted`}
          icon={CheckCircle2}
          accent="purple"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Link href="/weather" className="glass-card group rounded-2xl p-4 transition hover:border-emerald-500/30">
          <div className="flex items-center justify-between">
            <CloudRain className="h-5 w-5 text-sky-400" />
            <ArrowRight className="h-4 w-4 text-slate-600 group-hover:text-emerald-400" />
          </div>
          <p className="mt-3 text-xs text-slate-500">Weather Impact</p>
          <p className="text-xl font-bold text-white">{weatherScore}/100</p>
        </Link>
        <Link href="/events" className="glass-card group rounded-2xl p-4 transition hover:border-purple-500/30">
          <div className="flex items-center justify-between">
            <CalendarDays className="h-5 w-5 text-purple-400" />
            <ArrowRight className="h-4 w-4 text-slate-600 group-hover:text-purple-400" />
          </div>
          <p className="mt-3 text-xs text-slate-500">Event Impact</p>
          <p className="text-xl font-bold text-white">{eventScore.toFixed(0)}/100</p>
        </Link>
        <Link href="/recommendations" className="glass-card group rounded-2xl p-4 transition hover:border-amber-500/30">
          <div className="flex items-center justify-between">
            <Zap className="h-5 w-5 text-amber-400" />
            <ArrowRight className="h-4 w-4 text-slate-600 group-hover:text-amber-400" />
          </div>
          <p className="mt-3 text-xs text-slate-500">Recommendations</p>
          <p className="text-xl font-bold text-white">{pendingRecs} pending</p>
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <GlassPanel title="Signal Strength" description="Composite intelligence scores" className="lg:col-span-1">
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={signalChart}>
                <defs>
                  <linearGradient id="signalGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={CHART_COLORS.primary} stopOpacity={0.4} />
                    <stop offset="100%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                <XAxis dataKey="name" stroke={CHART_COLORS.axis} fontSize={11} tickLine={false} />
                <YAxis stroke={CHART_COLORS.axis} fontSize={11} domain={[0, 100]} tickLine={false} />
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                <Area type="monotone" dataKey="value" stroke={CHART_COLORS.primary} fill="url(#signalGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </GlassPanel>

        <GlassPanel
          title="Weekly Revenue Comparison"
          description="Baseline vs optimized dynamic pricing"
          className="lg:col-span-2"
        >
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={revenueChart}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                <XAxis dataKey="day" stroke={CHART_COLORS.axis} fontSize={11} tickLine={false} />
                <YAxis stroke={CHART_COLORS.axis} fontSize={11} tickLine={false} />
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                <Legend />
                <Line name="Baseline" dataKey="base" stroke={CHART_COLORS.muted} strokeWidth={2} dot={false} />
                <Line name="Optimized" dataKey="optimized" stroke={CHART_COLORS.primary} strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </GlassPanel>
      </div>
    </div>
  )
}
