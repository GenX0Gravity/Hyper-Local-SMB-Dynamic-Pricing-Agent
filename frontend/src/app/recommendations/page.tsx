"use client"

import * as React from "react"
import { apiFetch } from "@/lib/api-client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { 
  Zap, 
  ArrowUpRight, 
  ArrowDownRight, 
  Check, 
  X, 
  Sparkles,
  HelpCircle,
  Clock,
  CheckCircle2,
  TrendingDown
} from "lucide-react"

interface ProductSnippet {
  id: string
  name: string
  category: string | null
  sku: string | null
  base_price: number
  current_price: number
}

interface Recommendation {
  id: string
  tenant_id: string
  product_id: string
  product: ProductSnippet
  rule_id: string | null
  rule_name: string | null
  recommended_price: number
  previous_price: number
  reason: string
  status: string
  created_at: string
  expires_at: string
}

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = React.useState<Recommendation[]>([])
  const [activeTab, setActiveTab] = React.useState<"pending" | "history">("pending")
  const [loading, setLoading] = React.useState(true)
  const [message, setMessage] = React.useState<string | null>(null)

  const fetchRecommendations = React.useCallback(async () => {
    setLoading(true)
    try {
      const filter = activeTab === "pending" ? "pending" : "approved"
      const res = await apiFetch(`/recommendations?status_filter=${filter}`)
      if (res.ok) {
        setRecommendations(await res.json())
      }
    } catch (err) {
      console.error("Failed to load recommendations:", err)
    }
    setLoading(false)
  }, [activeTab])

  React.useEffect(() => {
    fetchRecommendations()
  }, [fetchRecommendations])

  const applyRecommendation = async (id: string, name: string, price: number) => {
    try {
      const res = await apiFetch(`/recommendations/${id}/apply`, {
        method: "POST"
      })
      if (res.ok) {
        setMessage(`Applied price change: ${name} updated to $${price.toFixed(2)}`)
        fetchRecommendations()
      } else {
        setMessage("Failed to apply recommendation.")
      }
    } catch {
      setMessage("Network connection error.")
    }
  }

  const rejectRecommendation = async (id: string, name: string) => {
    try {
      const res = await apiFetch(`/recommendations/${id}/reject`, {
        method: "POST"
      })
      if (res.ok) {
        setMessage(`Dismissed recommendation for ${name}`)
        fetchRecommendations()
      } else {
        setMessage("Failed to dismiss suggestion.")
      }
    } catch {
      setMessage("Network connection error.")
    }
  }

  return (
    <div className="space-y-6">
      {/* Subheader and Notification alerts */}
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <p className="text-sm text-slate-400">Review dynamic pricing adjustments suggested by the local demand monitor.</p>
        </div>
        
        {/* Toggle switch for queue vs history logs */}
        <div className="flex p-0.5 rounded-lg bg-slate-900 border border-slate-800 self-start">
          <button
            onClick={() => setActiveTab("pending")}
            className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
              activeTab === "pending"
                ? "bg-emerald-500 text-slate-950 font-bold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Pending Suggesions
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
              activeTab === "history"
                ? "bg-emerald-500 text-slate-950 font-bold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Approved History
          </button>
        </div>
      </div>

      {message && (
        <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-400 bg-emerald-950/20 border border-emerald-900/50 p-4 rounded-xl animate-fade-in">
          <Sparkles className="h-4 w-4 text-emerald-400 animate-pulse" />
          <span>{message}</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48 text-slate-400">
          <div className="flex flex-col items-center space-y-2">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent"></div>
            <span className="text-xs">Loading queue...</span>
          </div>
        </div>
      ) : recommendations.length === 0 ? (
        <Card className="border-slate-850 bg-slate-950/40 text-center p-12">
          <CardContent className="space-y-3">
            <HelpCircle className="h-10 w-10 text-slate-600 mx-auto" />
            <h3 className="text-lg font-bold text-white">
              {activeTab === "pending" ? "Queue is Empty" : "No price logs recorded"}
            </h3>
            <p className="text-sm text-slate-500 max-w-sm mx-auto">
              {activeTab === "pending"
                ? "Prices match the rule bounds. Scraped local signals have no matching conditions triggered."
                : "Dynamic price approvals will be recorded here once you accept recommendations."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {recommendations.map((rec) => {
            const priceDiff = rec.recommended_price - rec.previous_price
            const isMarkup = priceDiff > 0
            
            return (
              <Card 
                key={rec.id} 
                className={`border-slate-850 glass-card transition-all hover:border-slate-700/80 ${
                  activeTab === "pending" 
                    ? isMarkup ? "glow-pulse-green border-emerald-500/10" : "glow-pulse-orange border-amber-500/10"
                    : ""
                }`}
              >
                <CardHeader className="pb-3 border-b border-slate-900/40">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        {rec.product.category || "General"}
                      </span>
                      <CardTitle className="text-base font-bold text-white mt-1.5 truncate max-w-[220px]">
                        {rec.product.name}
                      </CardTitle>
                      <CardDescription className="text-xs">SKU: {rec.product.sku || "N/A"}</CardDescription>
                    </div>
                    
                    {/* Directional Badge */}
                    <div className={`flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-bold ${
                      isMarkup 
                        ? "bg-emerald-950/40 text-emerald-400 border border-emerald-500/20" 
                        : "bg-amber-950/40 text-amber-500 border border-amber-500/20"
                    }`}>
                      {isMarkup ? (
                        <>
                          <ArrowUpRight className="h-3.5 w-3.5 shrink-0" />
                          <span>+{((priceDiff / rec.previous_price) * 100).toFixed(0)}% Markup</span>
                        </>
                      ) : (
                        <>
                          <ArrowDownRight className="h-3.5 w-3.5 shrink-0" />
                          <span>{((priceDiff / rec.previous_price) * 100).toFixed(0)}% Discount</span>
                        </>
                      )}
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent className="pt-4 space-y-4">
                  {/* Prices comparison details */}
                  <div className="grid grid-cols-3 gap-2 bg-slate-900/40 p-3 rounded-lg border border-slate-900 text-center">
                    <div>
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Previous Price</p>
                      <p className="text-base font-semibold text-slate-400 mt-0.5">${rec.previous_price.toFixed(2)}</p>
                    </div>
                    <div className="flex items-center justify-center text-slate-600">→</div>
                    <div>
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Optimized Price</p>
                      <p className={`text-lg font-bold mt-0.5 ${isMarkup ? "text-emerald-400" : "text-amber-400"}`}>
                        ${rec.recommended_price.toFixed(2)}
                      </p>
                    </div>
                  </div>

                  {/* Triggering reason info */}
                  <div className="space-y-1">
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Trigging Logic</p>
                    <p className="text-xs text-slate-300 font-medium bg-slate-900/20 border border-slate-900/50 p-2.5 rounded">
                      {rec.reason}
                    </p>
                  </div>
                  
                  {/* Time stamps */}
                  <div className="flex items-center space-x-4 text-[10px] text-slate-500">
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      <span>Suggested: {new Date(rec.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    {activeTab === "pending" && (
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        <span>Expires: {new Date(rec.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    )}
                  </div>
                </CardContent>

                {/* Operations footer */}
                {activeTab === "pending" && (
                  <div className="flex border-t border-slate-900 bg-slate-950/60 p-3 rounded-b-xl gap-2">
                    <Button 
                      onClick={() => rejectRecommendation(rec.id, rec.product.name)}
                      variant="outline" 
                      className="flex-1 text-xs h-9 text-slate-400 hover:text-red-400 border-slate-800"
                    >
                      <X className="h-3.5 w-3.5 mr-1" />
                      Dismiss
                    </Button>
                    <Button 
                      onClick={() => applyRecommendation(rec.id, rec.product.name, rec.recommended_price)}
                      variant="glow" 
                      className="flex-1 text-xs h-9"
                    >
                      <Check className="h-3.5 w-3.5 mr-1" />
                      Approve & Apply
                    </Button>
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
