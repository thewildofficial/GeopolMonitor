"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Activity, Users, AlertTriangle, Clock } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

interface FeedStatsProps {
  stats: {
    total_messages: number
    active_channels: number
    high_urgency_count: number
    last_update: string
  }
}

export function FeedStats({ stats }: FeedStatsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card className="intel-card intel-glow">
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-intel-info" />
            <div>
              <p className="text-sm text-intel-text-secondary font-mono">TOTAL MESSAGES</p>
              <p className="text-2xl font-bold text-intel-text-primary font-mono">{stats.total_messages}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="intel-card intel-glow">
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-intel-success" />
            <div>
              <p className="text-sm text-intel-text-secondary font-mono">ACTIVE CHANNELS</p>
              <p className="text-2xl font-bold text-intel-text-primary font-mono">{stats.active_channels}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="intel-card intel-glow">
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-intel-danger" />
            <div>
              <p className="text-sm text-intel-text-secondary font-mono">HIGH URGENCY</p>
              <p className="text-2xl font-bold text-intel-text-primary font-mono">{stats.high_urgency_count}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="intel-card intel-glow">
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-intel-warning" />
            <div>
              <p className="text-sm text-intel-text-secondary font-mono">LAST UPDATE</p>
              <p className="text-sm font-medium text-intel-text-primary font-mono">
                {formatDistanceToNow(new Date(stats.last_update), { addSuffix: true })}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
