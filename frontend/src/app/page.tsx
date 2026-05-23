"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"

export default function Home() {
  const { token, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading) {
      if (token) {
        router.replace("/dashboard")
      } else {
        router.replace("/login")
      }
    }
  }, [token, loading, router])

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-slate-950 text-emerald-500">
      <div className="flex flex-col items-center space-y-4">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent"></div>
        <span className="text-sm font-semibold tracking-wider animate-pulse">REDIRECTING...</span>
      </div>
    </div>
  )
}
