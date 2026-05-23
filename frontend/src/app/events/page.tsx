"use client"

import * as React from "react"
import { apiFetch } from "@/lib/api-client"
import { PageHeader } from "@/components/dashboard/page-header"
import { GlassPanel } from "@/components/dashboard/glass-panel"
import { StatCard } from "@/components/dashboard/stat-card"
import { LoadingState } from "@/components/dashboard/loading-state"
import { Button } from "@/components/ui/button"
import { CalendarDays, MapPin, Users, RefreshCw, Trophy } from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
} from "recharts"
import { chartTooltipStyle, chartLabelStyle, CHART_COLORS, barColors } from "@/lib/chart-theme"

interface ClassifiedEvent {
  name: string
  category: string
  category_label: string
  impact_score: number
  attendance_est: number
  distance_km: number
  hours_until_start: number | null
}

interface EventReport {
  aggregate_impact_score: number
  events: ClassifiedEvent[]
  category_summary: Array<{ category: string; event_count: number; max_impact_score: number }>
}

const CATEGORY_LABELS: Record<string, string> = {
  ipl_match: "IPL",
  football_match: "Football",
  durga_puja: "Durga Puja",
  college_festival: "College Fest",
  public_holiday: "Holiday",
  local_event: "Local",
}

export default function EventImpactPage() {
  const [report, setReport] = React.useState<EventReport | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [refreshing, setRefreshing] = React.useState(false)

  const load = React.useCallback(async () => {
    setLoading(true)
    const res = await apiFetch("/events/intelligence")
    if (res.ok) setReport(await res.json())
    setLoading(false)
  }, [])

  React.useEffect(() => {
    load()
  }, [load])

  const refresh = async () => {
    setRefreshing(true)
    await apiFetch("/events/intelligence/refresh", { method: "POST" })
    await load()
    setRefreshing(false)
  }

  const impactChart =
    report?.events.slice(0, 6).map((e) => ({
      name: e.name.slice(0, 18) + (e.name.length > 18 ? "…" : ""),
      impact: e.impact_score,
    })) ?? []

  const categoryRadar =
    report?.category_summary.map((s) => ({
      category: CATEGORY_LABELS[s.category] ?? s.category,
      score: s.max_impact_score,
      fullMark: 100,
    })) ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Event Impact"
        description="IPL, football, festivals, holidays, and local events affecting foot traffic."
        icon={CalendarDays}
        badge="Intelligence"
        actions={
          <Button variant="outline" onClick={refresh} disabled={refreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      />

      {loading ? (
        <LoadingState message="Scanning local events..." />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard
              title="Aggregate Impact"
              value={`${report?.aggregate_impact_score?.toFixed(0) ?? 0}/100`}
              subtitle="Composite event score"
              icon={Trophy}
              accent="purple"
            />
            <StatCard
              title="Active Events"
              value={String(report?.events.length ?? 0)}
              subtitle="Within search radius"
              icon={CalendarDays}
              accent="emerald"
            />
            <StatCard
              title="Categories"
              value={String(report?.category_summary.length ?? 0)}
              subtitle="Monitored types"
              icon={Users}
              accent="blue"
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <GlassPanel title="Event Impact Scores">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={impactChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    <XAxis dataKey="name" stroke={CHART_COLORS.axis} fontSize={9} angle={-20} textAnchor="end" height={60} />
                    <YAxis stroke={CHART_COLORS.axis} domain={[0, 100]} fontSize={10} />
                    <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                    <Bar dataKey="impact" fill={CHART_COLORS.secondary} radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </GlassPanel>

            <GlassPanel title="Impact by Category">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={categoryRadar}>
                    <PolarGrid stroke={CHART_COLORS.grid} />
                    <PolarAngleAxis dataKey="category" stroke={CHART_COLORS.axis} fontSize={10} />
                    <Radar dataKey="score" stroke={CHART_COLORS.secondary} fill={CHART_COLORS.secondary} fillOpacity={0.35} />
                    <Tooltip contentStyle={chartTooltipStyle} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </GlassPanel>
          </div>

          <GlassPanel title="Upcoming Events" description="Classified and scored" noPadding>
            <div className="divide-y divide-white/5">
              {(report?.events ?? []).map((ev, i) => (
                <div key={i} className="flex flex-col gap-2 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-white">{ev.name}</p>
                      <span
                        className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
                        style={{
                          backgroundColor: `${barColors[i % barColors.length]}20`,
                          color: barColors[i % barColors.length],
                        }}
                      >
                        {ev.category_label || CATEGORY_LABELS[ev.category] || ev.category}
                      </span>
                    </div>
                    <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                      <MapPin className="h-3 w-3" />
                      {ev.distance_km.toFixed(1)} km · ~{ev.attendance_est.toLocaleString()} attendees
                    </p>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    {ev.hours_until_start != null && (
                      <span className="text-xs text-slate-500">in {ev.hours_until_start.toFixed(0)}h</span>
                    )}
                    <div className="text-right">
                      <p className="text-lg font-bold text-purple-400">{ev.impact_score.toFixed(0)}</p>
                      <p className="text-[10px] text-slate-500">impact</p>
                    </div>
                  </div>
                </div>
              ))}
              {!report?.events.length && (
                <p className="py-12 text-center text-sm text-slate-500">No events detected nearby.</p>
              )}
            </div>
          </GlassPanel>
        </>
      )}
    </div>
  )
}
