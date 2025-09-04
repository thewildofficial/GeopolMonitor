import { Metadata } from "next"
import AnalyticsDashboard from "@/components/analytics-dashboard"

export const metadata: Metadata = {
  title: "Analytics Dashboard - GeopolMonitor",
  description: "Intelligence analytics and trend visualization",
}

export default function AnalyticsPage() {
  return (
    <div className="min-h-[calc(100vh-4rem)]">
      <AnalyticsDashboard />
    </div>
  )
}