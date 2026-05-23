"use client"

import * as React from "react"
import { apiFetch } from "@/lib/api-client"
import { useAuth } from "@/lib/auth-context"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { 
  MapPin, 
  MessageSquare, 
  Check, 
  Loader2, 
  AlertCircle,
  Database,
} from "lucide-react"
import { PageHeader } from "@/components/dashboard/page-header"

export default function SettingsPage() {
  const { refreshUser } = useAuth()
  const [loading, setLoading] = React.useState(true)
  const [saving, setSaving] = React.useState(false)
  const [success, setSuccess] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  // Form states
  const [name, setName] = React.useState("")
  const [businessType, setBusinessType] = React.useState("cafe")
  const [lat, setLat] = React.useState("0")
  const [lng, setLng] = React.useState("0")
  const [timezone, setTimezone] = React.useState("UTC")
  const [phone, setPhone] = React.useState("")
  const [whatsappEnabled, setWhatsappEnabled] = React.useState(false)
  const [whatsappAutoApprove, setWhatsappAutoApprove] = React.useState(false)
  const [currency, setCurrency] = React.useState("USD")

  // Simulated POS states
  const [posSync, setPosSync] = React.useState(true)
  const [posType, setPosType] = React.useState("shopify")
  const [apiKey, setApiKey] = React.useState("••••••••••••••••••••••••")

  React.useEffect(() => {
    async function loadStoreSettings() {
      setLoading(true)
      try {
        const res = await apiFetch("/store")
        if (res.ok) {
          const store = await res.json()
          setName(store.name)
          setBusinessType(store.business_type)
          setLat(store.latitude.toString())
          setLng(store.longitude.toString())
          setTimezone(store.timezone)
          setPhone(store.whatsapp_phone || "")
          setWhatsappEnabled(store.whatsapp_enabled)
          setWhatsappAutoApprove(store.whatsapp_auto_approve ?? false)
          setCurrency(store.currency)
        }
      } catch (err) {
        console.error("Failed to load store settings:", err)
      }
      setLoading(false)
    }
    loadStoreSettings()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setSuccess(false)
    setError(null)

    const payload = {
      name,
      business_type: businessType,
      latitude: parseFloat(lat) || 0.0,
      longitude: parseFloat(lng) || 0.0,
      timezone,
      whatsapp_phone: phone || null,
      whatsapp_enabled: whatsappEnabled,
      whatsapp_auto_approve: whatsappAutoApprove,
      currency
    }

    try {
      const res = await apiFetch("/store", {
        method: "PATCH",
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        setSuccess(true)
        await refreshUser() // Update header name if changed
      } else {
        const errorData = await res.json()
        setError(errorData.detail || "Failed to update configurations.")
      }
    } catch {
      setError("Network connection failure.")
    }
    setSaving(false)
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title="Settings"
        description="Store location, notifications, and integrations."
        icon={MessageSquare}
      />

      {success && (
        <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-400 bg-emerald-950/20 border border-emerald-900/50 p-4 rounded-xl">
          <Check className="h-4 w-4" />
          <span>Store configuration updated successfully. Pricing telemetry is sync-calibrated.</span>
        </div>
      )}

      {error && (
        <div className="flex items-center space-x-2 text-xs font-semibold text-red-400 bg-red-950/20 border border-red-900/50 p-4 rounded-xl">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="text-center py-20 text-slate-400 text-xs">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-emerald-500" />
          Loading settings...
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            
            {/* Store parameters */}
            <Card className="border-slate-850 glass-card">
              <CardHeader>
                <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-emerald-400" />
                  <span>Geographic Configuration</span>
                </CardTitle>
                <CardDescription className="text-xs">Location metrics determines OpenWeatherMap & Event scrape signals.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Store Outlet Name</label>
                  <Input value={name} onChange={(e) => setName(e.target.value)} required />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Latitude</label>
                    <Input value={lat} onChange={(e) => setLat(e.target.value)} required />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Longitude</label>
                    <Input value={lng} onChange={(e) => setLng(e.target.value)} required />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Local Timezone</label>
                    <Input value={timezone} onChange={(e) => setTimezone(e.target.value)} required />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Currency Symbol</label>
                    <Select value={currency} onChange={(e) => setCurrency(e.target.value)}>
                      <option value="USD" className="bg-slate-900">USD ($)</option>
                      <option value="EUR" className="bg-slate-900">EUR (€)</option>
                      <option value="GBP" className="bg-slate-900">GBP (£)</option>
                      <option value="INR" className="bg-slate-900">INR (₹)</option>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Notification Integrations */}
            <Card className="border-slate-850 glass-card">
              <CardHeader>
                <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-emerald-400" />
                  <span>WhatsApp Notifications</span>
                </CardTitle>
                <CardDescription className="text-xs">Receive price adjustment alerts on signal shifts.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Merchant Phone Number</label>
                  <Input 
                    placeholder="+15550199" 
                    value={phone} 
                    onChange={(e) => setPhone(e.target.value)} 
                  />
                  <p className="text-[10px] text-slate-500 font-medium mt-0.5">Include international area prefix code.</p>
                </div>
                
                <div className="flex items-center space-x-3 p-3 rounded-lg bg-slate-900/30 border border-slate-900">
                  <input
                    type="checkbox"
                    id="whatsappEnabled"
                    checked={whatsappEnabled}
                    onChange={(e) => setWhatsappEnabled(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-800 bg-slate-950 text-emerald-500 focus:ring-emerald-500 cursor-pointer"
                  />
                  <div className="space-y-0.5 cursor-pointer" onClick={() => setWhatsappEnabled(!whatsappEnabled)}>
                    <label htmlFor="whatsappEnabled" className="text-xs font-semibold text-white block cursor-pointer">
                      Enable WhatsApp notifications
                    </label>
                    <span className="text-[10px] text-slate-500 font-medium block">
                      Receive pricing alerts and approval prompts via Twilio.
                    </span>
                  </div>
                </div>

                <div className="flex items-center space-x-3 p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/30">
                  <input
                    type="checkbox"
                    id="whatsappAutoApprove"
                    checked={whatsappAutoApprove}
                    onChange={(e) => setWhatsappAutoApprove(e.target.checked)}
                    disabled={!whatsappEnabled}
                    className="h-4 w-4 rounded border-slate-800 bg-slate-950 text-emerald-500 focus:ring-emerald-500 cursor-pointer disabled:opacity-40"
                  />
                  <div className="space-y-0.5">
                    <label htmlFor="whatsappAutoApprove" className="text-xs font-semibold text-white block">
                      Auto-approve mode
                    </label>
                    <span className="text-[10px] text-slate-500 font-medium block">
                      Apply recommendations automatically without manual approval.
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* POS Sync simulated card */}
          <Card className="border-slate-850 glass-card">
            <CardHeader className="pb-3 border-b border-slate-900/40">
              <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                <Database className="h-4 w-4 text-purple-400" />
                <span>POS & E-Commerce Integration (Shopify/Square)</span>
              </CardTitle>
              <CardDescription className="text-xs">Automatically publish approved recommendations back to registers.</CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-purple-950/10 border border-purple-900/20">
                <div className="space-y-0.5">
                  <p className="text-xs font-bold text-white">Simulate POS Price Synchronization</p>
                  <p className="text-[10px] text-slate-500">Automatically push approved price edits directly to Shopify catalog.</p>
                </div>
                <input
                  type="checkbox"
                  checked={posSync}
                  onChange={(e) => setPosSync(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-800 bg-slate-950 text-purple-500 focus:ring-purple-500 cursor-pointer"
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">POS Channel Integration Provider</label>
                  <Select value={posType} onChange={(e) => setPosType(e.target.value)} disabled={!posSync}>
                    <option value="shopify" className="bg-slate-900">Shopify API</option>
                    <option value="square" className="bg-slate-900">Square POS</option>
                    <option value="clover" className="bg-slate-900">Clover API</option>
                  </Select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">POS Private App Access Token</label>
                  <Input 
                    value={apiKey} 
                    onChange={(e) => setApiKey(e.target.value)} 
                    disabled={!posSync} 
                    type="password"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Submit action */}
          <div className="flex justify-end">
            <Button type="submit" variant="glow" disabled={saving} className="px-8">
              {saving ? "Saving Changes..." : "Save Settings"}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
