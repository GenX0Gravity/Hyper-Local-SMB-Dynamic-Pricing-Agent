import "./globals.css"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { AuthProvider } from "@/lib/auth-context"
import LayoutShell from "@/components/layout-shell"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "PricePulse AI — Dynamic Pricing SaaS",
  description: "Modern SaaS dashboard for demand forecasting, weather & event intelligence, and AI pricing recommendations.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} antialiased`}>
        <AuthProvider>
          <LayoutShell>
            {children}
          </LayoutShell>
        </AuthProvider>
      </body>
    </html>
  )
}
