"use client"

import * as React from "react"
import { apiFetch } from "@/lib/api-client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { TrendingUp, Sparkles, AlertCircle, Info, Thermometer } from "lucide-react"

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

export default function AnalyticsPage() {
  const [forecasts, setForecasts] = React.useState<CategoryForecast[]>([])
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    async function loadForecasts() {
      try {
        const res = await apiFetch("/analytics/demand-forecast")
        if (res.ok) {
          setForecasts(await res.json())
        }
      } catch (err) {
        console.error("Failed to load demand forecasts:", err)
      }
      setLoading(false)
    }
    loadForecasts()
  }, [])

  // Format forecast data for Recharts stacked/multi-bar rendering
  const getChartData = () => {
    if (forecasts.length === 0) return []
    
    const dates = forecasts[0].forecast.map(p => p.date)
    return dates.map((date, index) => {
      const dataPoint: Record<string, any> = { date }
      forecasts.forEach(cat => {
        dataPoint[cat.category] = cat.forecast[index]?.expected_sales_units || 0
      })
      return dataPoint
    })
  }

  const chartData = getChartData()
  const barColors = ["#10b981", "#8b5cf6", "#3b82f6", "#f59e0b"]

  return (
    <div className="space-y-6">
      {/* Subheader banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-purple-950/20 via-slate-900/40 to-slate-950/80 border border-slate-800 flex items-center space-x-3">
        <Sparkles className="h-6 w-6 text-purple-400 animate-pulse shrink-0" />
        <div>
          <h3 className="text-sm font-bold text-white">Machine Learning Demand Forecasting</h3>
          <p className="text-xs text-slate-400">7-Day predictive modeling integrating historical store transactions and local weather projections.</p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-20 text-slate-400 text-xs">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent mx-auto mb-2"></div>
          Calculating forecast indices...
        </div>
      ) : forecasts.length === 0 ? (
        <div className="text-center py-12 text-slate-500 text-sm">
          No forecast predictions compiled yet. Seeding product items is required.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Charts Grid */}
          <Card className="border-slate-850 glass-card">
            <CardHeader className="pb-4">
              <CardTitle className="text-base font-bold text-white">7-Day Projected Sales Units</CardTitle>
              <CardDescription className="text-xs">Stacked categories sales volume predictions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: "#0b0f19", border: "1px solid #1e293b", borderRadius: "8px" }}
                      labelStyle={{ color: "#ffffff", fontWeight: "bold" }}
                    />
                    <Legend verticalAlign="top" height={36} iconType="circle" />
                    {forecasts.map((cat, idx) => (
                      <Bar 
                        key={cat.category} 
                        dataKey={cat.category} 
                        stackId="a" 
                        fill={barColors[idx % barColors.length]} 
                        radius={[4, 4, 0, 0]}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Details list of forecast variables */}
          <div className="grid gap-6 md:grid-cols-2">
            {forecasts.map((cat) => (
              <Card key={cat.category} className="border-slate-850 glass-card">
                <CardHeader className="pb-3 border-b border-slate-900/40">
                  <CardTitle className="text-sm font-bold text-white flex items-center space-x-2">
                    <TrendingUp className="h-4 w-4 text-emerald-400" />
                    <span>Demand Shift: {cat.category}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 p-0">
                  <div className="divide-y divide-slate-900">
                    {cat.forecast.map((point, index) => (
                      <div key={index} className="flex items-center justify-between p-4 hover:bg-slate-900/10 transition-colors">
                        <div>
                          <p className="text-xs text-slate-400 font-semibold">{point.date}</p>
                          <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5 font-medium">
                            <Info className="h-3.5 w-3.5 text-slate-500" />
                            <span>{point.influencing_factor}</span>
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold text-white">{point.expected_sales_units} units</p>
                          <p className="text-[9px] text-slate-500 font-semibold font-mono">
                            Confidence: {(point.forecast_confidence * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
