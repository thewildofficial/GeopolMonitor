"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export default function HomePage() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to dashboard after a short delay
    const timeout = setTimeout(() => {
      router.push("/dashboard")
    }, 2000)

    return () => clearTimeout(timeout)
  }, [router])

  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-intel-bg">
      <Card className="max-w-md intel-card intel-glow">
        <CardHeader className="text-center">
          <div className="text-6xl mb-4 intel-matrix-text">🛰️</div>
          <CardTitle className="text-4xl font-bold intel-matrix-text font-mono">
            GeopolMonitor
          </CardTitle>
          <CardDescription className="text-lg text-intel-text-secondary font-mono">
            CLASSIFIED INTELLIGENCE MONITORING PLATFORM
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-intel-accent border-t-transparent" />
            <p className="text-intel-text-secondary font-mono">INITIALIZING DASHBOARD...</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}