"use client"

import * as React from "react"
import { apiFetch } from "@/lib/api-client"
import { PageHeader } from "@/components/dashboard/page-header"
import { GlassPanel } from "@/components/dashboard/glass-panel"
import { StatCard } from "@/components/dashboard/stat-card"
import { LoadingState } from "@/components/dashboard/loading-state"
import { Button } from "@/components/ui/button"
import {
  BarChart3,
  DollarSign,
  Percent,
  CheckCircle,
  XCircle,
  Target,
  CalendarDays,
  TrendingUp,
  Download,
} from "lucide-react"
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import { chartTooltipStyle, chartLabelStyle, CHART_COLORS } from "@/lib/chart-theme"

interface KPIMetrics {
  revenue_increase: number
  revenue_increase_pct: number
  conversion_rate: number
  accepted_recommendations: number
  rejected_recommendations: number
  pending_recommendations: number
  demand_accuracy: number
  event_impact_accuracy: number
  total_revenue: number
  total_units_sold: number
}

interface KPIDashboard {
  kpis: KPIMetrics
  trends: Array<{
    date: string
    revenue_increase: number
    conversion_rate: number
    accepted: number
    rejected: number
    demand_accuracy: number
    event_impact_accuracy: number
  }>
  highlights: string[]
}

interface PeriodReport {
  label: string
  summary: string
  kpis: KPIMetrics
}

interface ReportsBundle {
  reports: PeriodReport[]
  aggregate?: KPIMetrics
}

export default function RevenueAnalyticsPage() {
  const [dashboard, setDashboard] = React.useState<KPIDashboard | null>(null)
  const [weekly, setWeekly] = React.useState<ReportsBundle | null>(null)
  const [monthly, setMonthly] = React.useState<ReportsBundle | null>(null)
  const [tab, setTab] = React.useState<"kpi" | "weekly" | "monthly">("kpi")
  const [loading, setLoading] = React.useState(true)
  const [generating, setGenerating] = React.useState(false)

  const load = React.useCallback(async () => {
    setLoading(true)
    const [kpiRes, weekRes, monthRes] = await Promise.all([
      apiFetch("/analytics/kpi?lookback_days=30"),
      apiFetch("/analytics/reports/weekly?weeks=4"),
      apiFetch("/analytics/reports/monthly?months=6"),
    ])
    if (kpiRes.ok) setDashboard(await kpiRes.json())
    if (weekRes.ok) setWeekly(await weekRes.json())
    if (monthRes.ok) setMonthly(await monthRes.json())
    setLoading(false)
  }, [])

  React.useEffect(() => {
    load()
  }, [load])

  const generateReport = async (period: "weekly" | "monthly") => {
    setGenerating(true)
    await apiFetch(`/analytics/reports/generate?period_type=${period}`, { method: "POST" })
    await load()
    setGenerating(false)
    setTab(period)
  }

  const k = dashboard?.kpis

  const recChart = dashboard?.trends.map((t) => ({
    date: t.date.slice(5),
    accepted: t.accepted,
    rejected: t.rejected,
  })) ?? []

  const accuracyChart = dashboard?.trends.map((t) => ({
    date: t.date.slice(5),
    demand: t.demand_accuracy,
    event: t.event_impact_accuracy,
  })) ?? []

  const weeklyChart =
    weekly?.reports
      .slice()
      .reverse()
      .map((r) => ({
        label: r.label,
        revenue: r.kpis.revenue_increase,
        conversion: r.kpis.conversion_rate,
      })) ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Revenue Analytics"
        description="KPI dashboard, conversion tracking, forecast accuracy, and periodic reports."
        icon={BarChart3}
        badge="Analytics"
        actions={
          <Button
            variant="outline"
            size="sm"
            disabled={generating}
            onClick={() => generateReport("weekly")}
          >
            <Download className="mr-2 h-4 w-4" />
            Save Weekly Report
          </Button>
        }
      />

      <div className="flex flex-wrap gap-2">
        {(["kpi", "weekly", "monthly"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-xl px-4 py-2 text-xs font-semibold transition ${
              tab === t
                ? "bg-emerald-500 text-slate-950"
                : "glass-card text-slate-400 hover:text-white"
            }`}
          >
            {t === "kpi" ? "KPI Dashboard" : t === "weekly" ? "Weekly Reports" : "Monthly Reports"}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingState message="Loading analytics..." />
      ) : tab === "kpi" && k ? (
        <>
          {dashboard.highlights.length > 0 && (
            <div className="glass-card rounded-2xl p-4">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Insights
              </p>
              <ul className="space-y-1">
                {dashboard.highlights.map((h, i) => (
                  <li key={i} className="text-sm text-slate-300">
                    • {h}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard
              title="Revenue Increase"
              value={`+$${k.revenue_increase.toLocaleString()}`}
              subtitle={`${k.revenue_increase_pct.toFixed(1)}% vs baseline`}
              icon={DollarSign}
              accent="emerald"
              trend={{ value: `Total $${k.total_revenue.toLocaleString()}`, positive: true }}
            />
            <StatCard
              title="Conversion Rate"
              value={`${k.conversion_rate.toFixed(1)}%`}
              subtitle="Accepted / decided recommendations"
              icon={Percent}
              accent="purple"
            />
            <StatCard
              title="Accepted"
              value={String(k.accepted_recommendations)}
              subtitle={`${k.pending_recommendations} pending`}
              icon={CheckCircle}
              accent="emerald"
            />
            <StatCard
              title="Rejected"
              value={String(k.rejected_recommendations)}
              subtitle="Declined suggestions"
              icon={XCircle}
              accent="amber"
            />
            <StatCard
              title="Demand Accuracy"
              value={`${k.demand_accuracy.toFixed(0)}%`}
              subtitle="Forecast vs actual"
              icon={Target}
              accent="blue"
            />
            <StatCard
              title="Event Impact Accuracy"
              value={`${k.event_impact_accuracy.toFixed(0)}%`}
              subtitle="Event prediction quality"
              icon={CalendarDays}
              accent="purple"
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <GlassPanel title="Revenue Increase Trend" description="Daily incremental revenue">
              <div className="h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dashboard.trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    <XAxis dataKey="date" stroke={CHART_COLORS.axis} fontSize={10} tickFormatter={(v) => v.slice(5)} />
                    <YAxis stroke={CHART_COLORS.axis} fontSize={10} />
                    <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                    <Area type="monotone" dataKey="revenue_increase" stroke={CHART_COLORS.primary} fill={CHART_COLORS.primary} fillOpacity={0.2} name="Revenue ($)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </GlassPanel>

            <GlassPanel title="Recommendation Outcomes" description="Accepted vs rejected per day">
              <div className="h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={recChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    <XAxis dataKey="date" stroke={CHART_COLORS.axis} fontSize={10} />
                    <YAxis stroke={CHART_COLORS.axis} fontSize={10} />
                    <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                    <Legend />
                    <Bar dataKey="accepted" fill={CHART_COLORS.primary} name="Accepted" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="rejected" fill={CHART_COLORS.warning} name="Rejected" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </GlassPanel>

            <GlassPanel title="Accuracy Scores" description="Demand & event impact" className="lg:col-span-2">
              <div className="h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={accuracyChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    <XAxis dataKey="date" stroke={CHART_COLORS.axis} fontSize={10} />
                    <YAxis stroke={CHART_COLORS.axis} domain={[0, 100]} fontSize={10} />
                    <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                    <Legend />
                    <Line type="monotone" dataKey="demand" stroke={CHART_COLORS.primary} name="Demand %" dot={false} />
                    <Line type="monotone" dataKey="event" stroke={CHART_COLORS.secondary} name="Event %" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </GlassPanel>
          </div>
        </>
      ) : tab === "weekly" && weekly ? (
        <>
          <GlassPanel title="Weekly Performance" description="Last 4 weeks">
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklyChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                  <XAxis dataKey="label" stroke={CHART_COLORS.axis} fontSize={10} />
                  <YAxis stroke={CHART_COLORS.axis} fontSize={10} />
                  <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                  <Legend />
                  <Bar dataKey="revenue" fill={CHART_COLORS.primary} name="Revenue increase ($)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </GlassPanel>
          <div className="grid gap-4 md:grid-cols-2">
            {weekly.reports.map((r) => (
              <div key={r.label} className="glass-card rounded-2xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-bold text-white">{r.label}</span>
                  <TrendingUp className="h-4 w-4 text-emerald-400" />
                </div>
                <p className="text-xs text-slate-400 mb-4">{r.summary}</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-500">Revenue +</span>
                    <p className="font-bold text-emerald-400">${r.kpis.revenue_increase.toFixed(0)}</p>
                  </div>
                  <div>
                    <span className="text-slate-500">Conversion</span>
                    <p className="font-bold text-white">{r.kpis.conversion_rate.toFixed(0)}%</p>
                  </div>
                  <div>
                    <span className="text-slate-500">Accepted</span>
                    <p className="font-bold text-white">{r.kpis.accepted_recommendations}</p>
                  </div>
                  <div>
                    <span className="text-slate-500">Demand acc.</span>
                    <p className="font-bold text-white">{r.kpis.demand_accuracy.toFixed(0)}%</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : tab === "monthly" && monthly ? (
        <div className="space-y-4">
          {monthly.reports.map((r) => (
            <div key={r.label} className="glass-card rounded-2xl p-6">
              <h3 className="text-lg font-bold text-white mb-2">{r.label} Monthly Report</h3>
              <p className="text-sm text-slate-400 mb-4">{r.summary}</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Revenue +</p>
                  <p className="text-lg font-bold text-emerald-400">${r.kpis.revenue_increase.toFixed(0)}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Conversion</p>
                  <p className="text-lg font-bold text-white">{r.kpis.conversion_rate.toFixed(0)}%</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Accepted</p>
                  <p className="text-lg font-bold text-white">{r.kpis.accepted_recommendations}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Rejected</p>
                  <p className="text-lg font-bold text-amber-400">{r.kpis.rejected_recommendations}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Demand</p>
                  <p className="text-lg font-bold text-white">{r.kpis.demand_accuracy.toFixed(0)}%</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Events</p>
                  <p className="text-lg font-bold text-white">{r.kpis.event_impact_accuracy.toFixed(0)}%</p>
                </div>
              </div>
            </div>
          ))}
          <Button variant="outline" onClick={() => generateReport("monthly")} disabled={generating}>
            Persist Current Month Report
          </Button>
        </div>
      ) : null}
    </div>
  )
}
