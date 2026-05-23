"use client"

import * as React from "react"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select } from "@/components/ui/select"
import { Zap, Sparkles, AlertCircle } from "lucide-react"

export default function LoginPage() {
  const { login, register } = useAuth()
  
  const [activeTab, setActiveTab] = React.useState<"login" | "register">("login")
  const [error, setError] = React.useState<string | null>(null)
  const [loading, setLoading] = React.useState(false)

  // Login states
  const [loginEmail, setLoginEmail] = React.useState("")
  const [loginPassword, setLoginPassword] = React.useState("")

  // Register states
  const [storeName, setStoreName] = React.useState("")
  const [businessType, setBusinessType] = React.useState("cafe")
  const [lat, setLat] = React.useState("40.7128")
  const [lng, setLng] = React.useState("-74.0060")
  const [ownerName, setOwnerName] = React.useState("")
  const [registerEmail, setRegisterEmail] = React.useState("")
  const [registerPassword, setRegisterPassword] = React.useState("")

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!loginEmail || !loginPassword) {
      setError("Please fill in all credentials.")
      setLoading(false)
      return
    }

    const success = await login(loginEmail, loginPassword)
    if (!success) {
      setError("Invalid username or password.")
    }
    setLoading(false)
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!storeName || !ownerName || !registerEmail || !registerPassword) {
      setError("All fields are required to register your store.")
      setLoading(false)
      return
    }

    const success = await register(
      storeName,
      businessType,
      parseFloat(lat) || 0.0,
      parseFloat(lng) || 0.0,
      registerEmail,
      registerPassword,
      ownerName
    )

    if (!success) {
      setError("Registration failed. Email might already be taken.")
    }
    setLoading(false)
  }

  const handleQuickDemo = async () => {
    setError(null)
    setLoading(true)
    const success = await login("demo@pricepulse.ai", "password123")
    if (!success) {
      setError("Demo account seeding failed or is offline. Please launch the backend.")
    }
    setLoading(false)
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-[#030712] px-4">
      {/* Dynamic ambient color gradients */}
      <div className="absolute top-1/4 left-1/4 -z-10 h-72 w-72 rounded-full bg-emerald-500/10 blur-[100px]" />
      <div className="absolute bottom-1/4 right-1/4 -z-10 h-72 w-72 rounded-full bg-purple-500/10 blur-[100px]" />

      <div className="w-full max-w-md">
        {/* Brand Logo Header */}
        <div className="flex flex-col items-center space-y-2 mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500 text-slate-950 shadow-[0_0_20px_rgba(16,185,129,0.3)]">
            <Zap className="h-6 w-6 fill-slate-950" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">PricePulse <span className="text-emerald-400">AI</span></h1>
          <p className="text-sm text-slate-400 text-center">Optimizing local retail pricing through demand intelligence</p>
        </div>

        {/* Auth form Card */}
        <Card className="glass-card shadow-2xl border-slate-800">
          <CardHeader className="pb-4">
            <div className="flex p-0.5 rounded-lg bg-slate-900/80 border border-slate-800 mb-4">
              <button
                onClick={() => { setActiveTab("login"); setError(null); }}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                  activeTab === "login"
                    ? "bg-emerald-500 text-slate-950 font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Sign In
              </button>
              <button
                onClick={() => { setActiveTab("register"); setError(null); }}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                  activeTab === "register"
                    ? "bg-emerald-500 text-slate-950 font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Register Store
              </button>
            </div>
            
            <CardTitle className="text-xl font-bold text-center">
              {activeTab === "login" ? "Welcome Back" : "Create Merchant Account"}
            </CardTitle>
            <CardDescription className="text-center">
              {activeTab === "login" 
                ? "Enter your credentials to access the pricing engine" 
                : "Register your store coordinates to configure demand telemetry"}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {error && (
              <div className="flex items-center space-x-2 text-xs font-medium text-red-400 bg-red-950/20 border border-red-900/50 p-3 rounded-lg">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {activeTab === "login" ? (
              <form onSubmit={handleLogin} className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Email address</label>
                  <Input
                    type="email"
                    placeholder="name@store.com"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Password</label>
                  <Input
                    type="password"
                    placeholder="••••••••"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required
                  />
                </div>
                <Button type="submit" variant="glow" className="w-full mt-2" disabled={loading}>
                  {loading ? "Signing In..." : "Access Engine"}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="space-y-3 max-h-[350px] overflow-y-auto pr-1">
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Store Name</label>
                  <Input
                    placeholder="The Daily Brew Cafe"
                    value={storeName}
                    onChange={(e) => setStoreName(e.target.value)}
                    required
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Business Type</label>
                    <Select
                      value={businessType}
                      onChange={(e) => setBusinessType(e.target.value)}
                    >
                      <option value="cafe" className="bg-slate-900">Cafe</option>
                      <option value="boutique" className="bg-slate-900">Boutique Store</option>
                      <option value="stationery" className="bg-slate-900">Stationery</option>
                      <option value="retail" className="bg-slate-900">Local Retail</option>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-slate-400 font-medium">Latitude</label>
                    <Input
                      placeholder="40.7128"
                      value={lat}
                      onChange={(e) => setLat(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Longitude</label>
                  <Input
                    placeholder="-74.0060"
                    value={lng}
                    onChange={(e) => setLng(e.target.value)}
                    required
                  />
                </div>

                <hr className="border-slate-800 my-2" />

                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Full Name (Owner)</label>
                  <Input
                    placeholder="Alex Mercer"
                    value={ownerName}
                    onChange={(e) => setOwnerName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Owner Email</label>
                  <Input
                    type="email"
                    placeholder="alex@store.com"
                    value={registerEmail}
                    onChange={(e) => setRegisterEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-slate-400 font-medium">Password</label>
                  <Input
                    type="password"
                    placeholder="Create security password"
                    value={registerPassword}
                    onChange={(e) => setRegisterPassword(e.target.value)}
                    required
                  />
                </div>

                <Button type="submit" variant="glow" className="w-full mt-3" disabled={loading}>
                  {loading ? "Registering Store..." : "Create Account"}
                </Button>
              </form>
            )}

            {/* Quick Demo Credentials login helper */}
            <div className="relative flex py-2 items-center">
              <div className="flex-grow border-t border-slate-850"></div>
              <span className="flex-shrink mx-4 text-[10px] text-slate-500 font-bold uppercase tracking-wider">Sandbox Sandbox</span>
              <div className="flex-grow border-t border-slate-850"></div>
            </div>

            <Button
              onClick={handleQuickDemo}
              variant="outline"
              type="button"
              className="w-full flex items-center justify-center space-x-2 border-emerald-500/30 text-emerald-400 hover:bg-emerald-950/20"
              disabled={loading}
            >
              <Sparkles className="h-4 w-4" />
              <span>Sign In with Demo Cafe Account</span>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
