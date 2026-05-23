"use client"

import * as React from "react"
import { apiFetch } from "@/lib/api-client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { 
  Sliders, 
  Plus, 
  Trash2, 
  CloudSun, 
  Calendar, 
  Archive, 
  Clock, 
  HelpCircle,
  ToggleLeft,
  ToggleRight
} from "lucide-react"

interface PricingRule {
  id: string
  name: string
  rule_type: string
  conditions: Record<string, any>
  adjustment_type: string
  adjustment_value: number
  is_active: boolean
  created_at: string
}

export default function RulesPage() {
  const [rules, setRules] = React.useState<PricingRule[]>([])
  const [loading, setLoading] = React.useState(true)
  const [isDialogOpen, setIsDialogOpen] = React.useState(false)
  const [formError, setFormError] = React.useState<string | null>(null)

  // Form states
  const [name, setName] = React.useState("")
  const [ruleType, setRuleType] = React.useState("weather")
  const [adjType, setAdjType] = React.useState("percentage")
  const [adjVal, setAdjVal] = React.useState("")
  const [targetCategory, setTargetCategory] = React.useState("")
  
  // Dynamic rule-specific conditions states
  const [weatherCondition, setWeatherCondition] = React.useState("Rainy")
  const [tempBelow, setTempBelow] = React.useState("")
  const [tempAbove, setTempAbove] = React.useState("")
  
  const [minAttendance, setMinAttendance] = React.useState("")
  const [eventCategory, setEventCategory] = React.useState("concerts")
  const [eventRadius, setEventRadius] = React.useState("1.5")
  
  const [stockBelow, setStockBelow] = React.useState("")
  
  const [hourStart, setHourStart] = React.useState("")
  const [hourEnd, setHourEnd] = React.useState("")

  const fetchRules = React.useCallback(async () => {
    setLoading(true)
    try {
      const res = await apiFetch("/rules")
      if (res.ok) {
        setRules(await res.json())
      }
    } catch (err) {
      console.error("Failed to load rules:", err)
    }
    setLoading(false)
  }, [])

  React.useEffect(() => {
    fetchRules()
  }, [fetchRules])

  const openCreateDialog = () => {
    setName("")
    setRuleType("weather")
    setAdjType("percentage")
    setAdjVal("")
    setTargetCategory("")
    
    setWeatherCondition("Rainy")
    setTempBelow("")
    setTempAbove("")
    setMinAttendance("")
    setEventCategory("concerts")
    setEventRadius("1.5")
    setStockBelow("")
    setHourStart("")
    setHourEnd("")
    
    setFormError(null)
    setIsDialogOpen(true)
  }

  const handleToggleActive = async (id: string, currentStatus: boolean) => {
    try {
      const res = await apiFetch(`/rules/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !currentStatus })
      })
      if (res.ok) {
        fetchRules()
      }
    } catch (err) {
      console.error("Toggle active call failed:", err)
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete rules '${name}'?`)) return
    try {
      const res = await apiFetch(`/rules/${id}`, {
        method: "DELETE"
      })
      if (res.ok) {
        fetchRules()
      }
    } catch (err) {
      console.error("Delete rule call failed:", err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    const adjustment = parseFloat(adjVal)
    if (isNaN(adjustment)) {
      setFormError("Adjustment value must be a number.")
      return
    }

    // Assemble dynamic conditions
    const conditions: Record<string, any> = {}
    if (targetCategory) {
      conditions["category"] = targetCategory
    }

    if (ruleType === "weather") {
      conditions["weather"] = weatherCondition
      if (tempBelow) conditions["temp_below"] = parseFloat(tempBelow)
      if (tempAbove) conditions["temp_above"] = parseFloat(tempAbove)
    } else if (ruleType === "event") {
      if (minAttendance) conditions["attendance_above"] = parseInt(minAttendance)
      if (eventCategory) conditions["event_category"] = eventCategory
      if (eventRadius) conditions["radius_km"] = parseFloat(eventRadius)
    } else if (ruleType === "inventory") {
      if (stockBelow) conditions["stock_below"] = parseInt(stockBelow)
    } else if (ruleType === "time_of_day") {
      if (hourStart) conditions["hour_start"] = parseInt(hourStart)
      if (hourEnd) conditions["hour_end"] = parseInt(hourEnd)
      conditions["days_of_week"] = [0, 1, 2, 3, 4] // Default Mon-Fri
    }

    const payload = {
      name,
      rule_type: ruleType,
      conditions,
      adjustment_type: adjType,
      adjustment_value: adjustment,
      is_active: true
    }

    try {
      const res = await apiFetch("/rules", {
        method: "POST",
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        setIsDialogOpen(false)
        fetchRules()
      } else {
        const errorData = await res.json()
        setFormError(errorData.detail || "Transaction failed.")
      }
    } catch {
      setFormError("Failed to communicate with rules engine server.")
    }
  }

  const getRuleIcon = (type: string) => {
    switch (type) {
      case "weather": return <CloudSun className="h-5 w-5 text-emerald-400" />
      case "event": return <Calendar className="h-5 w-5 text-purple-400" />
      case "inventory": return <Archive className="h-5 w-5 text-amber-400" />
      case "time_of_day": return <Clock className="h-5 w-5 text-blue-400" />
      default: return <Sliders className="h-5 w-5 text-slate-400" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="flex justify-between items-center">
        <p className="text-sm text-slate-400">Configure trigger conditions and adjustments to automate menu adjustments.</p>
        <Button onClick={openCreateDialog} variant="glow" className="flex items-center gap-1.5 shrink-0">
          <Plus className="h-4 w-4" />
          <span>New Rule</span>
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-20 text-slate-400 text-xs">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent mx-auto mb-2"></div>
          Loading configured rules...
        </div>
      ) : rules.length === 0 ? (
        <Card className="border-slate-850 bg-slate-950/40 text-center p-12">
          <CardContent className="space-y-3">
            <Sliders className="h-10 w-10 text-slate-600 mx-auto" />
            <h3 className="text-lg font-bold text-white">No Rules Configured</h3>
            <p className="text-sm text-slate-500 max-w-sm mx-auto">
              Define logic triggers to automatically adjust product pricing when it rains, during concerts, or happy hours.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {rules.map((rule) => (
            <Card key={rule.id} className="border-slate-850 glass-card flex flex-col justify-between hover:border-slate-700 transition-all">
              <CardHeader className="pb-3 border-b border-slate-900/40">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="p-2 rounded bg-slate-900 border border-slate-850">
                      {getRuleIcon(rule.rule_type)}
                    </div>
                    <div>
                      <CardTitle className="text-sm font-bold text-white">{rule.name}</CardTitle>
                      <CardDescription className="text-[10px] capitalize font-medium text-slate-500">
                        {rule.rule_type.replace("_", " ")} Rule
                      </CardDescription>
                    </div>
                  </div>
                  
                  {/* Toggle Active Switch */}
                  <button 
                    onClick={() => handleToggleActive(rule.id, rule.is_active)}
                    className="text-slate-400 hover:text-white transition-colors cursor-pointer"
                  >
                    {rule.is_active ? (
                      <ToggleRight className="h-8 w-8 text-emerald-400" />
                    ) : (
                      <ToggleLeft className="h-8 w-8 text-slate-600" />
                    )}
                  </button>
                </div>
              </CardHeader>
              
              <CardContent className="pt-4 space-y-3 flex-1">
                {/* Rule Formula aggregate */}
                <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900/30 border border-slate-900">
                  <span className="text-xs text-slate-400 font-semibold">Adjustment Formula</span>
                  <span className={`text-sm font-bold px-2 py-0.5 rounded ${
                    rule.adjustment_value > 0
                      ? "bg-emerald-950/40 text-emerald-400 border border-emerald-500/20"
                      : "bg-red-950/40 text-red-400 border border-red-500/20"
                  }`}>
                    {rule.adjustment_value > 0 ? "+" : ""}
                    {rule.adjustment_value}
                    {rule.adjustment_type === "percentage" ? "%" : " USD"}
                  </span>
                </div>

                {/* Target scopes */}
                <div className="text-xs space-y-1 bg-slate-950/20 border border-slate-900/40 p-2.5 rounded">
                  <div className="flex justify-between text-slate-500">
                    <span>Target Category:</span>
                    <span className="text-slate-300 font-medium font-mono uppercase text-[10px]">
                      {rule.conditions.category || "GLOBAL (All catalog)"}
                    </span>
                  </div>
                  <hr className="border-slate-900 my-1.5" />
                  
                  {/* Parameter specs */}
                  <div className="space-y-1">
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Trigger specs</p>
                    {rule.rule_type === "weather" && (
                      <div className="text-[11px] text-slate-400 font-medium">
                        Condition: <span className="text-slate-200">{rule.conditions.weather || "Any"}</span>
                        {rule.conditions.temp_below && `, Temp < ${rule.conditions.temp_below}°C`}
                        {rule.conditions.temp_above && `, Temp > ${rule.conditions.temp_above}°C`}
                      </div>
                    )}
                    {rule.rule_type === "event" && (
                      <div className="text-[11px] text-slate-400 font-medium">
                        Distance: <span className="text-slate-200">&lt; {rule.conditions.radius_km || "1.5"}km</span>
                        {rule.conditions.attendance_above && `, Attendance > ${rule.conditions.attendance_above}`}
                        {rule.conditions.event_category && `, Category: ${rule.conditions.event_category}`}
                      </div>
                    )}
                    {rule.rule_type === "inventory" && (
                      <div className="text-[11px] text-slate-400 font-medium">
                        Trigger stock level: <span className="text-slate-200">&lt; {rule.conditions.stock_below} units</span>
                      </div>
                    )}
                    {rule.rule_type === "time_of_day" && (
                      <div className="text-[11px] text-slate-400 font-medium">
                        Hours: <span className="text-slate-200">{rule.conditions.hour_start}:00 - {rule.conditions.hour_end}:00</span>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>

              {/* Card Footer Delete Button */}
              <CardFooter className="pt-2 border-t border-slate-900 bg-slate-950/20 rounded-b-xl flex justify-end">
                <button
                  onClick={() => handleDelete(rule.id, rule.name)}
                  className="p-1.5 rounded hover:bg-slate-800 text-slate-500 hover:text-red-400 cursor-pointer inline-flex"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* Creator dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent onClose={() => setIsDialogOpen(false)} className="max-w-md">
          <DialogHeader>
            <DialogTitle>Configure Pricing Rule</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            {formError && (
              <div className="text-xs font-semibold p-3 rounded-lg bg-red-950/20 border border-red-900/40 text-red-400">
                {formError}
              </div>
            )}

            <div className="space-y-1">
              <label className="text-xs text-slate-400 font-medium">Rule Name</label>
              <Input placeholder="Rainy Day Coffee Booster" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">Trigger Type</label>
                <Select value={ruleType} onChange={(e) => setRuleType(e.target.value)}>
                  <option value="weather" className="bg-slate-900">Weather Scrape</option>
                  <option value="event" className="bg-slate-900">Nearby Events</option>
                  <option value="inventory" className="bg-slate-900">Stock Levels</option>
                  <option value="time_of_day" className="bg-slate-900">Time of Day</option>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">Target Category</label>
                <Input placeholder="Beverages (optional)" value={targetCategory} onChange={(e) => setTargetCategory(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 border-t border-slate-900 pt-3">
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">Adjustment Type</label>
                <Select value={adjType} onChange={(e) => setAdjType(e.target.value)}>
                  <option value="percentage" className="bg-slate-900">Percentage (%)</option>
                  <option value="fixed" className="bg-slate-900">Fixed Cash ($)</option>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-slate-400 font-medium">Value Change (+ / -)</label>
                <Input placeholder="15.0 or -0.50" value={adjVal} onChange={(e) => setAdjVal(e.target.value)} required />
              </div>
            </div>

            {/* Adapting form details depending on rule type */}
            <div className="border-t border-slate-900 pt-3 space-y-3">
              <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Trigger Conditions Details</p>
              
              {ruleType === "weather" && (
                <div className="space-y-2">
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Weather Condition</label>
                    <Select value={weatherCondition} onChange={(e) => setWeatherCondition(e.target.value)}>
                      <option value="Rainy" className="bg-slate-900">Rainy</option>
                      <option value="Sunny" className="bg-slate-900">Sunny / Warm</option>
                      <option value="Heatwave" className="bg-slate-900">Heatwave Alert</option>
                      <option value="Snowy" className="bg-slate-900">Snowy / Cold</option>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <label className="text-xs text-slate-400 font-medium">Temp below (°C)</label>
                      <Input placeholder="15 (optional)" value={tempBelow} onChange={(e) => setTempBelow(e.target.value)} />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-slate-400 font-medium">Temp above (°C)</label>
                      <Input placeholder="30 (optional)" value={tempAbove} onChange={(e) => setTempAbove(e.target.value)} />
                    </div>
                  </div>
                </div>
              )}

              {ruleType === "event" && (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <label className="text-xs text-slate-400 font-medium">Radius (km)</label>
                      <Input placeholder="1.5" value={eventRadius} onChange={(e) => setEventRadius(e.target.value)} />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-slate-400 font-medium">Event Category</label>
                      <Select value={eventCategory} onChange={(e) => setEventCategory(e.target.value)}>
                        <option value="concerts" className="bg-slate-900">Concerts</option>
                        <option value="sports" className="bg-slate-900">Sports Matches</option>
                        <option value="festivals" className="bg-slate-900">Festivals / Markets</option>
                      </Select>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Min Expected Attendance</label>
                    <Input placeholder="2000" value={minAttendance} onChange={(e) => setMinAttendance(e.target.value)} />
                  </div>
                </div>
              )}

              {ruleType === "inventory" && (
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Activate when stock falls below</label>
                  <Input placeholder="10 units" value={stockBelow} onChange={(e) => setStockBelow(e.target.value)} required />
                </div>
              )}

              {ruleType === "time_of_day" && (
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Hour Start (24h)</label>
                    <Input type="number" placeholder="14 (2 PM)" value={hourStart} onChange={(e) => setHourStart(e.target.value)} required />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Hour End (24h)</label>
                    <Input type="number" placeholder="17 (5 PM)" value={hourEnd} onChange={(e) => setHourEnd(e.target.value)} required />
                  </div>
                </div>
              )}
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="glow">
                Create Rule
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
