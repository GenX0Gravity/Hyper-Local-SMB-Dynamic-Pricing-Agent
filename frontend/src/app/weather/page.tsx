"use client"

import * as React from "react"
import { apiFetch } from "@/lib/api-client"
import { PageHeader } from "@/components/dashboard/page-header"
import { GlassPanel } from "@/components/dashboard/glass-panel"
import { StatCard } from "@/components/dashboard/stat-card"
import { LoadingState } from "@/components/dashboard/loading-state"
import { Button } from "@/components/ui/button"
import { CloudRain, Droplets, Wind, Thermometer, RefreshCw, Umbrella } from "lucide-react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts"
import { chartTooltipStyle, chartLabelStyle, CHART_COLORS } from "@/lib/chart-theme"

interface WeatherReport {
  current: {
    temperature_c: number
    humidity_pct: number
    wind_speed_ms: number
    condition_label: string
    rain_intensity: string
    is_heavy_rain: boolean
    is_raining: boolean
    precipitation_mm_1h: number
  }
  forecast?: {
    heavy_rain_within_hours: number | null
    windows: Array<{ starts_at: string; pop: number; rain_mm: number; temperature_c: number }>
  }
  demand_adjustments: Array<{ metric: string; delta_pct: number; reason: string }>
  offers: Array<{ title: string; adjustment_value: number }>
  alerts: Array<{ severity: string; message: string }>
}

export default function WeatherImpactPage() {
  const [report, setReport] = React.useState<WeatherReport | null>(null)
  const [monitor, setMonitor] = React.useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [refreshing, setRefreshing] = React.useState(false)

  const load = React.useCallback(async (refresh = false) => {
    setLoading(true)
    const path = refresh ? "/weather/intelligence?refresh=true" : "/weather/intelligence"
    const [intelRes, monRes] = await Promise.all([
      apiFetch(path),
      apiFetch("/weather/monitor"),
    ])
    if (intelRes.ok) setReport(await intelRes.json())
    if (monRes.ok) setMonitor(await monRes.json())
    setLoading(false)
  }, [])

  React.useEffect(() => {
    load()
  }, [load])

  const refresh = async () => {
    setRefreshing(true)
    await apiFetch("/weather/intelligence/refresh", { method: "POST" })
    await load(true)
    setRefreshing(false)
  }

  const forecastChart =
    report?.forecast?.windows.slice(0, 8).map((w) => ({
      time: new Date(w.starts_at).toLocaleTimeString([], { hour: "2-digit" }),
      pop: Math.round(w.pop * 100),
      rain: w.rain_mm,
      temp: w.temperature_c,
    })) ?? []

  const adjustmentChart =
    report?.demand_adjustments.map((a) => ({
      name: a.metric.replace(/_demand_score/g, "").slice(0, 12),
      boost: a.delta_pct,
    })) ?? []

  const c = report?.current

  return (
    <div className="space-y-6">
      <PageHeader
        title="Weather Impact"
        description="Rain, temperature, and forecast-driven demand adjustments for your menu."
        icon={CloudRain}
        badge="Live"
        actions={
          <Button variant="outline" onClick={refresh} disabled={refreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      />

      {loading ? (
        <LoadingState message="Fetching weather intelligence..." />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Temperature"
              value={c ? `${c.temperature_c.toFixed(0)}°C` : "—"}
              subtitle={c?.condition_label}
              icon={Thermometer}
              accent="amber"
            />
            <StatCard
              title="Rain Intensity"
              value={c?.rain_intensity ?? "—"}
              subtitle={c?.is_heavy_rain ? "Heavy rain playbook" : c?.is_raining ? "Raining" : "Dry"}
              icon={Droplets}
              accent={c?.is_heavy_rain ? "blue" : "default"}
            />
            <StatCard
              title="Humidity"
              value={c ? `${c.humidity_pct.toFixed(0)}%` : "—"}
              icon={Umbrella}
              accent="purple"
            />
            <StatCard
              title="Wind"
              value={c ? `${c.wind_speed_ms.toFixed(1)} m/s` : "—"}
              icon={Wind}
              accent="emerald"
            />
          </div>

          {report?.alerts && report.alerts.length > 0 && (
            <div className="space-y-2">
              {report.alerts.map((a, i) => (
                <div
                  key={i}
                  className={`rounded-xl border px-4 py-3 text-sm ${
                    a.severity === "critical"
                      ? "border-red-500/30 bg-red-500/10 text-red-200"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-200"
                  }`}
                >
                  {a.message}
                </div>
              ))}
            </div>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <GlassPanel title="Precipitation Forecast" description="Next 24h probability">
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={forecastChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    <XAxis dataKey="time" stroke={CHART_COLORS.axis} fontSize={10} />
                    <YAxis stroke={CHART_COLORS.axis} fontSize={10} />
                    <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                    <Area type="monotone" dataKey="pop" name="Rain %" stroke="#38bdf8" fill="#38bdf8" fillOpacity={0.2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </GlassPanel>

            <GlassPanel title="Demand Boost by Metric" description="Weather-driven adjustments">
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={adjustmentChart} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} horizontal={false} />
                    <XAxis type="number" stroke={CHART_COLORS.axis} fontSize={10} />
                    <YAxis dataKey="name" type="category" stroke={CHART_COLORS.axis} width={80} fontSize={10} />
                    <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                    <Bar dataKey="boost" fill={CHART_COLORS.primary} radius={[0, 4, 4, 0]} name="Boost %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </GlassPanel>
          </div>

          {report?.offers && report.offers.length > 0 && (
            <GlassPanel title="Weather Offers" description="Suggested promotions">
              <div className="grid gap-3 sm:grid-cols-2">
                {report.offers.map((o, i) => (
                  <div key={i} className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
                    <p className="font-semibold text-white">{o.title}</p>
                    <p className="mt-1 text-sm text-emerald-400">{o.adjustment_value}% adjustment</p>
                  </div>
                ))}
              </div>
            </GlassPanel>
          )}

          {monitor && (
            <p className="text-center text-[10px] text-slate-600">
              Cache: {String(monitor.cache_hit)} · Recorded {String(monitor.recorded_at ?? "")}
            </p>
          )}
        </>
      )}
    </div>
  )
}
