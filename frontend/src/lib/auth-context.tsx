"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { apiFetch } from "./api-client"

interface User {
  id: string
  email: string
  full_name: string
  role: string
  tenant_id: string
  tenant_name: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<boolean>
  register: (
    storeName: string,
    businessType: string,
    latitude: number,
    longitude: number,
    email: string,
    password: string,
    fullName: string
  ) => Promise<boolean>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null)
  const [token, setToken] = React.useState<string | null>(null)
  const [loading, setLoading] = React.useState<boolean>(true)
  const router = useRouter()

  const refreshUser = React.useCallback(async () => {
    try {
      const response = await apiFetch("/auth/me")
      if (response.ok) {
        const profile = await response.json()
        setUser(profile)
        localStorage.setItem("pricepulse_user", JSON.stringify(profile))
      } else {
        logout()
      }
    } catch {
      logout()
    }
  }, [])

  // Sync token on boot
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const savedToken = localStorage.getItem("pricepulse_token")
      const savedUser = localStorage.getItem("pricepulse_user")
      
      if (savedToken) {
        setToken(savedToken)
        if (savedUser) {
          setUser(JSON.parse(savedUser))
        }
        // Validate and refresh profile details
        apiFetch("/auth/me").then(async (res) => {
          if (res.ok) {
            const profile = await res.json()
            setUser(profile)
            localStorage.setItem("pricepulse_user", JSON.stringify(profile))
          } else {
            logout()
          }
        }).catch(() => logout())
      }
      setLoading(false)
    }
  }, [])

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      const formData = new URLSearchParams()
      formData.append("username", email)
      formData.append("password", password)

      const response = await apiFetch("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData.toString(),
      })

      if (response.ok) {
        const data = await response.json()
        localStorage.setItem("pricepulse_token", data.access_token)
        setToken(data.access_token)
        
        // Fetch full profile info
        const profileRes = await apiFetch("/auth/me", {
          headers: {
            "Authorization": `Bearer ${data.access_token}`
          }
        })
        if (profileRes.ok) {
          const profile = await profileRes.json()
          setUser(profile)
          localStorage.setItem("pricepulse_user", JSON.stringify(profile))
        }
        
        router.push("/dashboard")
        return true
      }
      return false
    } catch {
      return false
    }
  }

  const register = async (
    storeName: string,
    businessType: string,
    latitude: number,
    longitude: number,
    email: string,
    password: string,
    fullName: string
  ): Promise<boolean> => {
    try {
      const payload = {
        tenant: {
          name: storeName,
          business_type: businessType,
          latitude,
          longitude,
        },
        user: {
          email,
          password,
          full_name: fullName,
        },
      }

      const response = await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      })

      if (response.ok) {
        const data = await response.json()
        localStorage.setItem("pricepulse_token", data.access_token)
        setToken(data.access_token)
        
        const profileRes = await apiFetch("/auth/me", {
          headers: {
            "Authorization": `Bearer ${data.access_token}`
          }
        })
        if (profileRes.ok) {
          const profile = await profileRes.json()
          setUser(profile)
          localStorage.setItem("pricepulse_user", JSON.stringify(profile))
        }

        router.push("/dashboard")
        return true
      }
      return false
    } catch {
      return false
    }
  }

  const logout = () => {
    localStorage.removeItem("pricepulse_token")
    localStorage.removeItem("pricepulse_user")
    setToken(null)
    setUser(null)
    router.push("/login")
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = React.useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
