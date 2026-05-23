"use client"

import * as React from "react"
import { apiFetch } from "@/lib/api-client"
import { PageHeader } from "@/components/dashboard/page-header"
import { GlassPanel } from "@/components/dashboard/glass-panel"
import { LoadingState } from "@/components/dashboard/loading-state"
import { EmptyState } from "@/components/dashboard/empty-state"
import { StatCard } from "@/components/dashboard/stat-card"
import { TrendingUp, Sparkles, Thermometer } from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts"
import { barColors, chartTooltipStyle, chartLabelStyle, CHART_COLORS } from "@/lib/chart-theme"

interface ForecastPoint {
  date: string
  expected_sales_units: number
  forecast_confidence: number
  influencing_factor: string
}

interface CategoryForecast {
  category: string
  forecast: ForecastPoint[]
}

export default function ForecastPage() {
  const [forecasts, setForecasts] = React.useState<CategoryForecast[]>([])
  const [batchScore, setBatchScore] = React.useState<number | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [fcRes, batchRes] = await Promise.all([
          apiFetch("/analytics/demand-forecast"),
          apiFetch("/forecast/predict/batch"),
        ])
        if (fcRes.ok) setForecasts(await fcRes.json())
        if (batchRes.ok) {
          const b = await batchRes.json()
          const scores = b.predictions?.map((p: { demand_score: number }) => p.demand_score) ?? []
          if (scores.length) {
            setBatchScore(scores.reduce((a: number, c: number) => a + c, 0) / scores.length)
          }
        }
      } catch (e) {
        console.error(e)
      }
      setLoading(false)
    }
    load()
  }, [])

  const chartData = React.useMemo(() => {
    if (!forecasts.length) return []
    const dates = forecasts[0].forecast.map((p) => p.date)
    return dates.map((date, i) => {
      const row: Record<string, string | number> = { date }
      forecasts.forEach((cat) => {
        row[cat.category] = cat.forecast[i]?.expected_sales_units ?? 0
      })
      return row
    })
  }, [forecasts])

  const trendData = forecasts[0]?.forecast.map((p) => ({
    date: p.date,
    units: p.expected_sales_units,
    confidence: Math.round(p.forecast_confidence * 100),
  })) ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Demand Forecast"
        description="7-day ML demand predictions with weather and event signal integration."
        icon={TrendingUp}
        badge="XGBoost"
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          title="Avg Demand Score"
          value={batchScore != null ? `${batchScore.toFixed(0)}/100` : "—"}
          subtitle="Live catalog prediction"
          icon={Sparkles}
          accent="purple"
        />
        <StatCard
          title="Categories"
          value={String(forecasts.length)}
          subtitle="Forecast segments"
          icon={TrendingUp}
          accent="emerald"
        />
        <StatCard
          title="Horizon"
          value="7 days"
          subtitle="Rolling forecast window"
          icon={Thermometer}
          accent="blue"
        />
      </div>

      {loading ? (
        <LoadingState message="Calculating demand indices..." />
      ) : forecasts.length === 0 ? (
        <EmptyState
          icon={TrendingUp}
          title="No forecast data"
          description="Train the model via API or seed sales history to generate predictions."
        />
      ) : (
        <>
          <GlassPanel title="7-Day Projected Sales by Category" description="Stacked unit volume">
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                  <XAxis dataKey="date" stroke={CHART_COLORS.axis} fontSize={11} tickLine={false} />
                  <YAxis stroke={CHART_COLORS.axis} fontSize={11} tickLine={false} />
                  <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                  <Legend />
                  {forecasts.map((cat, i) => (
                    <Bar key={cat.category} dataKey={cat.category} stackId="a" fill={barColors[i % barColors.length]} radius={[4, 4, 0, 0]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </GlassPanel>

          {trendData.length > 0 && (
            <GlassPanel title="Primary Category Trend" description={forecasts[0].category}>
              <div className="h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    <XAxis dataKey="date" stroke={CHART_COLORS.axis} fontSize={11} />
                    <YAxis stroke={CHART_COLORS.axis} fontSize={11} />
                    <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} />
                    <Line dataKey="units" stroke={CHART_COLORS.primary} strokeWidth={2} name="Units" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </GlassPanel>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {forecasts.map((cat) => (
              <GlassPanel key={cat.category} title={cat.category} noPadding>
                <div className="divide-y divide-white/5">
                  {cat.forecast.map((point, i) => (
                    <div key={i} className="flex items-center justify-between px-5 py-3 hover:bg-white/[0.02]">
                      <div>
                        <p className="text-xs font-semibold text-white">{point.date}</p>
                        <p className="mt-0.5 text-[11px] text-slate-500">{point.influencing_factor}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-emerald-400">{point.expected_sales_units} units</p>
                        <p className="text-[10px] text-slate-500">
                          {(point.forecast_confidence * 100).toFixed(0)}% confidence
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </GlassPanel>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
