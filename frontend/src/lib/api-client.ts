const DEFAULT_API_URL = "http://localhost:8000/api/v1"

export async function apiFetch(path: string, options: RequestInit = {}) {
  // Read target backend URL
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL
  const cleanPath = path.startsWith("/") ? path : `/${path}`
  
  const headers = new Headers(options.headers || {})
  
  // Read token from localStorage
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("pricepulse_token")
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`)
    }
  }

  // Enforce JSON headers if body is present and not form data
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(`${apiBaseUrl}${cleanPath}`, {
    ...options,
    headers,
  })

  // Handle unauthorized logouts
  if (response.status === 401 && typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
    localStorage.removeItem("pricepulse_token")
    localStorage.removeItem("pricepulse_user")
    window.location.href = "/login"
  }

  return response
}
