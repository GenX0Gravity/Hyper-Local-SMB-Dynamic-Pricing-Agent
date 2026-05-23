import "./globals.css"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { AuthProvider } from "@/lib/auth-context"
import LayoutShell from "@/components/layout-shell"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "PricePulse AI - SMB Dynamic Pricing Agent",
  description: "Optimize store prices in real-time based on local weather, foot traffic, and event demand signals.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <LayoutShell>
            {children}
          </LayoutShell>
        </AuthProvider>
      </body>
    </html>
  )
}
